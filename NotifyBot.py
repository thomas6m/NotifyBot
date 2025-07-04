import os
import csv
import re
import time
import logging
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path
from typing import List, Tuple, Dict

# Logging configuration with function name and line number for better traceability
logging.basicConfig(
    filename='notifybot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s'
)


class MissingRequiredFilesError(Exception):
    """Custom exception for missing required files."""
    pass


def read_file(path: Path) -> str:
    """
    Read entire content from a file and return as a stripped string.

    Args:
        path (Path): Path to the file.

    Returns:
        str: Content of the file stripped of leading/trailing whitespace.
             Returns empty string on failure.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Failed to read file {path}: {e}")
        return ""


def read_recipients(path: Path) -> List[str]:
    """
    Read recipient emails from a text file, one email per line.

    Args:
        path (Path): Path to the recipients file.

    Returns:
        List[str]: List of email strings. Empty list if file missing or error occurs.
    """
    if not path.is_file():
        logging.warning(f"{path.name} does not exist. Continuing without it.")
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"Failed to read recipients from {path}: {e}")
        return []


def write_to_txt(emails: List[str], path: Path) -> None:
    """
    Append a list of emails to a text file, each on a new line.

    Args:
        emails (List[str]): List of email addresses to append.
        path (Path): Path to the file to append to.
    """
    try:
        with open(path, 'a', encoding='utf-8') as f:
            for email in emails:
                f.write(email + '\n')
        logging.info(f"Appended {len(emails)} new emails to {path.name}.")
    except Exception as e:
        logging.error(f"Failed to write to {path}: {e}")


def deduplicate_file(path: Path) -> None:
    """
    Remove duplicate and blank lines from a file, preserving original order.

    Args:
        path (Path): Path to the file to deduplicate.
    """
    try:
        if not path.is_file():
            return
        with open(path, 'r', encoding='utf-8') as f:
            seen = set()
            lines = []
            for line in f:
                stripped = line.strip()
                if stripped and stripped not in seen:
                    seen.add(stripped)
                    lines.append(stripped)
        with open(path, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(line + '\n')
        logging.info(f"Deduplicated entries in {path.name}.")
    except Exception as e:
        logging.error(f"Failed to deduplicate file {path}: {e}")


def check_required_files(base_path: Path, required_files: List[str]) -> None:
    """
    Check if all required files exist in the base directory.

    Raises:
        MissingRequiredFilesError: If any required file is missing.
    """
    missing = [f for f in required_files if not (base_path / f).is_file()]
    if missing:
        message = f"Missing required files: {', '.join(missing)}"
        logging.error(message)
        raise MissingRequiredFilesError(message)


def parse_filter_file(filter_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Parse filter.txt CSV-like file into keys and list of condition dicts.

    Args:
        filter_path (Path): Path to filter.txt file.

    Returns:
        Tuple[List[str], List[Dict[str, str]]]:
            - keys: List of column headers.
            - conditions: List of dicts with key-value filter conditions.
    """
    try:
        with open(filter_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            lines = list(reader)
        keys = lines[0]
        conditions = [dict(zip(keys, row)) for row in lines[1:]]
        return keys, conditions
    except Exception as e:
        logging.error(f"Failed to parse filter file {filter_path}: {e}")
        return [], []


def get_filtered_emailids(base_path: Path) -> List[str]:
    """
    Get a list of unique email IDs filtered based on filter.txt conditions,
    excluding those already present in to.txt.

    Args:
        base_path (Path): Base folder containing inventory.csv and filter.txt.

    Returns:
        List[str]: Sorted list of new filtered email IDs.
    """
    inventory_file = base_path / 'inventory.csv'
    filter_file = base_path / 'filter.txt'

    if not inventory_file.is_file() or not filter_file.is_file():
        logging.warning("inventory.csv or filter.txt missing.")
        return []

    keys, conditions = parse_filter_file(filter_file)
    email_set = set()

    try:
        with open(inventory_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                for cond in conditions:
                    if all(row.get(k, '').strip() == v.strip() for k, v in cond.items()):
                        for email in re.split(r'[;,]', row.get('emailids', '')):
                            email_clean = email.strip()
                            if email_clean:
                                email_set.add(email_clean)
    except Exception as e:
        logging.error(f"Error reading inventory file: {e}")

    existing_to = set(read_recipients(base_path / 'to.txt'))

    return sorted(email_set.difference(existing_to))


def send_email(
    from_email: str,
    subject: str,
    body_html: str,
    recipients: List[str],
    cc_emails: List[str],
    bcc_emails: List[str],
    log_sent: bool = False
) -> None:
    """
    Compose and send an HTML email message to multiple recipients.

    Args:
        from_email (str): Sender's email address.
        subject (str): Email subject line.
        body_html (str): Email HTML body content.
        recipients (List[str]): List of primary recipients.
        cc_emails (List[str]): List of CC recipients.
        bcc_emails (List[str]): List of BCC recipients.
        log_sent (bool, optional): Whether to log sent emails. Defaults to False.
    """
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ', '.join(recipients)
    if cc_emails:
        msg['Cc'] = ', '.join(cc_emails)
    msg.add_alternative(body_html, subtype='html')

    # Combine all recipients (To, CC, BCC) removing duplicates but preserving order
    all_recipients = list(dict.fromkeys(recipients + cc_emails + bcc_emails))

    try:
        with smtplib.SMTP('localhost') as server:
            server.send_message(msg, from_addr=from_email, to_addrs=all_recipients)
        print(f"Sent to {len(recipients)} recipient(s).")
        logging.info(f"Sent to {', '.join(recipients)}")
    except Exception as e:
        logging.error(f"Failed to send email to {', '.join(recipients)}: {e}")
        print(f"Failed to send to {', '.join(recipients)}")


def send_email_from_folder(base_folder: str) -> None:
    base_path = Path(base_folder)
    logging.info(f"--- Start sending emails from {base_folder} ---")

    required_files = ['from.txt', 'subject.txt', 'body.html', 'approver.txt']

    try:
        check_required_files(base_path, required_files)
    except MissingRequiredFilesError as e:
        print(str(e))
        sys.exit(1)  # Exit immediately with error status

    # Read subject and body early to check if empty
    subject = read_file(base_path / 'subject.txt')
    body_html = read_file(base_path / 'body.html')

    if not subject:
        print("Error: subject.txt is missing or empty. Exiting.")
        logging.error("subject.txt is missing or empty.")
        sys.exit(1)

    if not body_html:
        print("Error: body.html is missing or empty. Exiting.")
        logging.error("body.html is missing or empty.")
        sys.exit(1)

    from_email = read_file(base_path / 'from.txt')
    approvers = read_recipients(base_path / 'approver.txt')

    if not approvers:
        print("Approver list is empty.")
        logging.warning("Approver list is empty.")
        return

    # Draft email approval loop
    while True:
        print("Sending draft email to approvers...")
        send_email(from_email, "[DRAFT] " + subject, body_html, approvers, [], [], log_sent=False)

        approval = input("Has approval been received? (yes/no): ").strip().lower()
        if approval == 'yes':
            break
        elif approval == 'no':
            print("Waiting for updated body.html or subject.txt. Please make your edits.")

            # Re-read subject and body after edits
            subject = read_file(base_path / 'subject.txt')
            body_html = read_file(base_path / 'body.html')

            if not subject:
                print("Error: subject.txt is missing or empty after edits. Exiting.")
                logging.error("subject.txt missing or empty after edits during draft approval.")
                sys.exit(1)

            if not body_html:
                print("Error: body.html is missing or empty after edits. Exiting.")
                logging.error("body.html missing or empty after edits during draft approval.")
                sys.exit(1)

        else:
            print("Invalid input. Please enter 'yes' or 'no'.")

    # Append filtered new emails
    new_emails = get_filtered_emailids(base_path)
    if new_emails:
        write_to_txt(new_emails, base_path / 'to.txt')
        print(f"Added {len(new_emails)} new email(s) to to.txt")

    # Append additional_to.txt emails if present
    additional_to = read_recipients(base_path / 'additional_to.txt')
    if additional_to:
        write_to_txt(additional_to, base_path / 'to.txt')
        print(f"Appended {len(additional_to)} email(s) from additional_to.txt to to.txt")

    # Deduplicate to.txt after additions
    deduplicate_file(base_path / 'to.txt')

    # Read final recipients lists
    to_emails = read_recipients(base_path / 'to.txt')
    cc_emails = read_recipients(base_path / 'cc.txt')
    bcc_emails = read_recipients(base_path / 'bcc.txt')

    if not to_emails:
        print("No recipients found in to.txt.")
        logging.info("No recipients found in to.txt.")
        return

    total_sent = 0
    batch_size = 500

    for i in range(0, len(to_emails), batch_size):
        batch = to_emails[i:i + batch_size]
        send_email(from_email, subject, body_html, batch, cc_emails, bcc_emails, log_sent=False)
        total_sent += len(batch)
        if i + batch_size < len(to_emails):
            print("Waiting 5 seconds before sending next batch...")
            time.sleep(5)

    print("Emails sent successfully.")
    print(f"Summary:\n - Sent: {total_sent}")
    logging.info(f"Email Summary -> Sent: {total_sent}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python notifybot.py <base_folder>")
        sys.exit(1)

    send_email_from_folder(sys.argv[1])
