"""
NotifyBot Email Sender Script

Sends batch emails using content and recipients defined in flat files.
Supports filtering, dry-run mode, batching, attachments, and logging.

Author: Thomas Mathias (updated with attachments and colored error output)
Additional improvements by ChatGPT:
- Default attachments handling
- Email validation and filtering
- Enhanced exception logging with traceback
- Docstrings added to key functions
- Backup before deduplication to prevent data loss
"""

import os
import csv
import re
import time
import logging
import smtplib
import sys
import mimetypes
import shutil
from email.message import EmailMessage
from pathlib import Path
from typing import List, Tuple, Dict
from email.utils import parseaddr


# Configure logging
logging.basicConfig(
    filename='notifybot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s'
)


class MissingRequiredFilesError(Exception):
    """Custom exception raised when required input files are missing."""
    pass


def read_file(path: Path) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Failed to read file {path}: {e}")
        return ""


def read_recipients(path: Path) -> List[str]:
    """
    Reads recipient email addresses from a file, ignoring empty lines.
    """
    if not path.is_file():
        logging.warning(f"{path.name} does not exist. Continuing without it.")
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        # Validate emails and filter out invalid ones
        valid_emails = []
        for email in lines:
            realname, email_addr = parseaddr(email)
            if '@' in email_addr and '.' in email_addr:
                valid_emails.append(email)
            else:
                warning_msg = f"Invalid email address skipped: {email}"
                logging.warning(warning_msg)
                print(f"\033[93m{warning_msg}\033[0m")  # yellow warning
        return valid_emails
    except Exception as e:
        logging.error(f"Failed to read recipients from {path}: {e}")
        return []


def write_to_txt(emails: List[str], path: Path) -> None:
    try:
        with open(path, 'a', encoding='utf-8') as f:
            for email in emails:
                f.write(email + '\n')
        logging.info(f"Appended {len(emails)} new emails to {path.name}.")
    except Exception as e:
        logging.error(f"Failed to write to {path}: {e}")


def deduplicate_file(path: Path) -> None:
    """
    Deduplicates lines in a file by rewriting it with unique entries.
    Creates a backup copy before overwriting to avoid data loss.
    """
    try:
        if not path.is_file():
            return
        backup_path = path.with_suffix(path.suffix + '.bak')
        shutil.copy2(path, backup_path)
        logging.info(f"Backup of {path.name} created at {backup_path.name}")

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
    missing = [f for f in required_files if not (base_path / f).is_file()]
    if missing:
        message = f"Missing required files: {', '.join(missing)}"
        logging.error(message)
        raise MissingRequiredFilesError(message)


def parse_filter_file(filter_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
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
    Reads inventory.csv and filter.txt and returns filtered unique email IDs
    excluding those already in to.txt.
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
    # Validate filtered emails too
    valid_emails = []
    for email in sorted(email_set.difference(existing_to)):
        realname, email_addr = parseaddr(email)
        if '@' in email_addr and '.' in email_addr:
            valid_emails.append(email)
        else:
            warning_msg = f"Invalid filtered email skipped: {email}"
            logging.warning(warning_msg)
            print(f"\033[93m{warning_msg}\033[0m")  # yellow warning

    return valid_emails


def send_email(
    from_email: str,
    subject: str,
    body_html: str,
    recipients: List[str],
    cc_emails: List[str],
    bcc_emails: List[str],
    attachments: List[Path] = None,
    log_sent: bool = False
) -> None:
    """
    Composes and sends an email with optional attachments.

    Args:
        from_email (str): Sender email address.
        subject (str): Email subject line.
        body_html (str): HTML content of the email body.
        recipients (List[str]): List of "To" recipient emails.
        cc_emails (List[str]): List of "Cc" recipient emails.
        bcc_emails (List[str]): List of "Bcc" recipient emails.
        attachments (List[Path], optional): List of file paths to attach.
        log_sent (bool): Whether to log successful sends.
    """
    attachments = attachments or []

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ', '.join(recipients)
    if cc_emails:
        msg['Cc'] = ', '.join(cc_emails)
    msg.add_alternative(body_html, subtype='html')

    # Attach files if any
    for file_path in attachments:
        try:
            ctype, encoding = mimetypes.guess_type(str(file_path))
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)

            with open(file_path, 'rb') as f:
                file_data = f.read()

            msg.add_attachment(file_data,
                               maintype=maintype,
                               subtype=subtype,
                               filename=file_path.name)
            logging.info(f"Attached file: {file_path.name}")
        except Exception as e:
            logging.error(f"Failed to attach file {file_path}: {e}")

    all_recipients = list(dict.fromkeys(recipients + cc_emails + bcc_emails))

    try:
        with smtplib.SMTP('localhost') as server:
            server.send_message(msg, from_addr=from_email, to_addrs=all_recipients)
        print(f"Sent to {len(recipients)} recipient(s).")
        if log_sent:
            logging.info(f"Sent to {', '.join(recipients)}")
    except Exception as e:
        err_msg = f"Failed to send email to {', '.join(recipients)}: {e}"
        logging.error(err_msg)
        logging.exception(e)  # full traceback
        print(f"\033[91m{err_msg}\033[0m")  # red color for error


def prepare_to_txt(base_path: Path) -> None:
    """
    Adds filtered and additional emails to to.txt and deduplicates it.
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


def send_email_from_folder(
    base_folder: str,
    dry_run: bool = False,
    batch_size: int = 500,
    delay: int = 5
) -> None:
    """
    Main entry point to send emails from a given folder.

    Args:
        base_folder (str): Directory path with all email files.
        dry_run (bool): If True, only sends draft to approvers.
        batch_size (int): Number of emails to send per batch.
        delay (int): Delay in seconds between batches.
    """
    base_path = Path(base_folder)
    attachments_folder = base_path / "attachments"

    logging.info(f"--- Start sending emails from {base_folder} ---")

    required_files = ['from.txt', 'subject.txt', 'body.html', 'approver.txt']

    try:
        check_required_files(base_path, required_files)
    except MissingRequiredFilesError as e:
        print(f"\033[91m{str(e)}\033[0m")  # Red color error
        sys.exit(1)

    subject = read_file(base_path / 'subject.txt')
    body_html = read_file(base_path / 'body.html')
    from_email = read_file(base_path / 'from.txt')
    approvers = read_recipients(base_path / 'approver.txt')

    if not subject or not body_html:
        print("\033[91mMissing subject or body. Exiting.\033[0m")
        logging.error("Subject or body is missing.")
        sys.exit(1)

    if not approvers:
        print("\033[93mApprover list is empty.\033[0m")  # Yellow warning
        logging.warning("Approver list is empty.")
        return

    prepare_to_txt(base_path)

    if dry_run:
        print("Dry-run mode: Draft email sent to approvers only.")
        send_email(from_email, "[DRAFT] " + subject, body_html, approvers, [], [], attachments=None, log_sent=False)
        logging.info("Dry-run complete. No actual recipients emailed.")
        return

    to_emails = read_recipients(base_path / 'to.txt')
    cc_emails = read_recipients(base_path / 'cc.txt')
    bcc_emails = read_recipients(base_path / 'bcc.txt')

    # Collect attachments if folder exists
    attachments = []
    if attachments_folder.is_dir():
        attachments = [f for f in attachments_folder.iterdir() if f.is_file()]
        print(f"Found {len(attachments)} attachment(s) to include.")

    if not to_emails:
        print("\033[91mNo recipients found in to.txt.\033[0m")
        logging.info("No recipients found in to.txt.")
        return

    total_sent = 0

    for i in range(0, len(to_emails), batch_size):
        batch = to_emails[i:i + batch_size]
        send_email(from_email, subject, body_html, batch, cc_emails, bcc_emails, attachments=attachments)
        total_sent += len(batch)
        if i + batch_size < len(to_emails):
            print(f"Waiting {delay} seconds before sending next batch...")
            time.sleep(delay)

    print("Emails sent successfully.")
    print(f"Summary:\n - Sent: {total_sent}")
    logging.info(f"Email Summary -> Sent: {total_sent}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="NotifyBot Email Sender")
    parser.add_argument("base_folder", help="Base folder containing email files")
    parser.add_argument("--dry-run", action="store_true", help="Only send draft to approver, skip actual email send")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of emails per batch (default: 500)")
    parser.add_argument("--delay", type=int, default=5, help="Delay in seconds between batches (default: 5)")

    args = parser.parse_args()

    send_email_from_folder(
        base_folder=args.base_folder,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        delay=args.delay
    )
