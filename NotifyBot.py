"""
NotifyBot Email Sender Script

Sends batch emails using content and recipients defined in flat files.
Supports filtering, dry-run mode, batching, and logging.

Author: Thomas Mathias
"""

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

# Configure logging
logging.basicConfig(
    filename='notifybot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s'
)


class MissingRequiredFilesError(Exception):
    """
    Custom exception raised when required input files are missing.
    """
    pass


def read_file(path: Path) -> str:
    """
    Reads the entire content of a text file.

    Args:
        path (Path): Path to the file.

    Returns:
        str: File content, stripped of leading/trailing whitespace.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Failed to read file {path}: {e}")
        return ""


def read_recipients(path: Path) -> List[str]:
    """
    Reads a list of recipients (email addresses) from a file.

    Args:
        path (Path): Path to recipient list file.

    Returns:
        List[str]: List of email addresses.
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
    Appends emails to a text file.

    Args:
        emails (List[str]): List of email addresses to write.
        path (Path): Destination file path.
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
    Removes duplicate lines from a text file in-place.

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
    Ensures that all required files are present in the base directory.

    Args:
        base_path (Path): Base directory path.
        required_files (List[str]): List of required filenames.

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
    Parses the filter file to extract column headers and condition rows.

    Args:
        filter_path (Path): Path to the filter.txt file.

    Returns:
        Tuple[List[str], List[Dict[str, str]]]: Tuple of header keys and conditions.
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
    Filters email IDs from inventory.csv based on filter.txt conditions.

    Args:
        base_path (Path): Base directory containing files.

    Returns:
        List[str]: Filtered email addresses.
    """
    inventory_file = base_path / 'inventory.csv'
    filter_file = base_path / 'filter.txt'

    if not inventory_file.is_file() or not filter_file.is_file():
        logging.warning("inventory.csv or filter.txt missing.")
        return []

    _, conditions = parse_filter_file(filter_file)
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
    Sends an email with optional CC/BCC.

    Args:
        from_email (str): Sender email address.
        subject (str): Email subject.
        body_html (str): Email body (HTML).
        recipients (List[str]): Primary recipients.
        cc_emails (List[str]): CC recipients.
        bcc_emails (List[str]): BCC recipients.
        log_sent (bool): Whether to log successful sends.
    """
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ', '.join(recipients)
    if cc_emails:
        msg['Cc'] = ', '.join(cc_emails)
    msg.add_alternative(body_html, subtype='html')

    all_recipients = list(dict.fromkeys(recipients + cc_emails + bcc_emails))

    try:
        with smtplib.SMTP('localhost') as server:
            server.send_message(msg, from_addr=from_email, to_addrs=all_recipients)
        print(f"Sent to {len(recipients)} recipient(s).")
        if log_sent:
            logging.info(f"Sent to {', '.join(recipients)}")
    except Exception as e:
        logging.error(f"Failed to send email to {', '.join(recipients)}: {e}")
        print(f"Failed to send to {', '.join(recipients)}")


def prepare_to_txt(base_path: Path) -> None:
    """
    Updates `to.txt` by adding filtered and additional recipients,
    then deduplicates the list.
    """
    new_emails = get_filtered_emailids(base_path)
    if new_emails:
        write_to_txt(new_emails, base_path / 'to.txt')
        print(f"Added {len(new_emails)} new email(s) to to.txt")

    additional_to = read_recipients(base_path / 'additional_to.txt')
    if additional_to:
        write_to_txt(additional_to, base_path / 'to.txt')
        print(f"Appended {len(additional_to)} email(s) from additional_to.txt to to.txt")

    deduplicate_file(base_path / 'to.txt')


def send_email_from_folder(base_folder: str, dry_run: bool = False) -> None:
    """
    Main entry point to send emails from a given folder.

    Args:
        base_folder (str): Directory path with all email files.
        dry_run (bool): If True, only sends draft to approvers.
    """
    base_path = Path(base_folder)
    logging.info(f"--- Start sending emails from {base_folder} ---")

    required_files = ['from.txt', 'subject.txt', 'body.html', 'approver.txt']

    try:
        check_required_files(base_path, required_files)
    except MissingRequiredFilesError as e:
        print(str(e))
        sys.exit(1)

    subject = read_file(base_path / 'subject.txt')
    body_html = read_file(base_path / 'body.html')
    from_email = read_file(base_path / 'from.txt')
    approvers = read_recipients(base_path / 'approver.txt')

    if not subject or not body_html:
        print("Missing subject or body. Exiting.")
        logging.error("Subject or body is missing.")
        sys.exit(1)

    if not approvers:
        print("Approver list is empty.")
        logging.warning("Approver list is empty.")
        return

    prepare_to_txt(base_path)

    if dry_run:
        print("Dry-run mode: Draft email sent to approvers only.")
        send_email(from_email, "[DRAFT] " + subject, body_html, approvers, [], [], log_sent=False)
        logging.info("Dry-run complete. No actual recipients emailed.")
        return

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
        send_email(from_email, subject, body_html, batch, cc_emails, bcc_emails)
        total_sent += len(batch)
        if i + batch_size < len(to_emails):
            print("Waiting 5 seconds before sending next batch...")
            time.sleep(5)

    print("Emails sent successfully.")
    print(f"Summary:\n - Sent: {total_sent}")
    logging.info(f"Email Summary -> Sent: {total_sent}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="NotifyBot Email Sender")
    parser.add_argument("base_folder", help="Base folder containing email files")
    parser.add_argument("--dry-run", action="store_true", help="Only send draft to approver, skip actual email send")
    args = parser.parse_args()

    send_email_from_folder(args.base_folder, dry_run=args.dry_run)
