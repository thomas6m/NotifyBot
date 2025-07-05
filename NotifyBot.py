import os
import csv
import re
import time
import logging
import smtplib
import sys
import mimetypes
from email.message import EmailMessage
from pathlib import Path
from typing import List, Tuple, Dict

# ANSI color codes for terminal coloring
LOG_COLORS = {
    'DEBUG': '\033[36m',   # Cyan
    'INFO': '\033[32m',    # Green
    'WARNING': '\033[33m', # Yellow
    'ERROR': '\033[31m',   # Red
    'RESET': '\033[0m'     # Reset to default
}

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname
        msg = super().format(record)
        color = LOG_COLORS.get(levelname, LOG_COLORS['RESET'])
        reset = LOG_COLORS['RESET']
        return f"{color}{msg}{reset}"


class MissingRequiredFilesError(Exception):
    """Custom exception for missing required files."""
    pass


def is_valid_email(email: str) -> bool:
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None


def read_file(path: Path) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Failed to read file {path}: {e}")
        return ""


def read_recipients(path: Path) -> List[str]:
    if not path.is_file():
        logging.warning(f"{path.name} does not exist. Continuing without it.")
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and is_valid_email(line.strip())]
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
    try:
        if not path.is_file():
            return
        with open(path, 'r', encoding='utf-8') as f:
            seen = set()
            lines = []
            for line in f:
                stripped = line.strip()
                if stripped and is_valid_email(stripped) and stripped not in seen:
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
                            if email_clean and is_valid_email(email_clean):
                                email_set.add(email_clean)
    except Exception as e:
        logging.error(f"Error reading inventory file: {e}")

    existing_to = set(read_recipients(base_path / 'to.txt'))
    return sorted(email_set.difference(existing_to))


def get_attachments(base_path: Path) -> List[Tuple[str, bytes, str]]:
    attachments = []
    attach_dir = base_path / 'attachment'
    if not attach_dir.is_dir():
        return attachments

    for file_path in attach_dir.iterdir():
        if file_path.is_file():
            mime_type, _ = mimetypes.guess_type(file_path.name)
            if not mime_type:
                mime_type = 'application/octet-stream'
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                attachments.append((file_path.name, data, mime_type))
            except Exception as e:
                logging.error(f"Failed to read attachment {file_path.name}: {e}")
    return attachments


def send_email(
    from_email: str,
    subject: str,
    body_html: str,
    recipients: List[str],
    cc_emails: List[str],
    bcc_emails: List[str],
    attachments: List[Tuple[str, bytes, str]] = None,
    log_sent: bool = False
) -> None:
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ', '.join(recipients)
    if cc_emails:
        msg['Cc'] = ', '.join(cc_emails)
    msg.add_alternative(body_html, subtype='html')

    if attachments:
        for filename, data, mime_type in attachments:
            maintype, subtype = mime_type.split('/', 1)
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

    all_recipients = list(dict.fromkeys(recipients + cc_emails + bcc_emails))

    try:
        with smtplib.SMTP('localhost') as server:
            server.send_message(msg, from_addr=from_email, to_addrs=all_recipients)
        print(f"Sent to {len(recipients)} recipient(s).")
        logging.info(f"Sent to {', '.join(recipients)}")
    except Exception as e:
        logging.error(f"Failed to send email to: {recipients}. Error: {e}", exc_info=True)
        print(f"Failed to send to {', '.join(recipients)}")


def prepare_to_txt(base_path: Path) -> None:
    new_emails = get_filtered_emailids(base_path)
    if new_emails:
        write_to_txt(new_emails, base_path / 'to.txt')
        print(f"Added {len(new_emails)} new email(s) to to.txt")
        logging.debug(f"New emails appended: {new_emails}")

    additional_to = read_recipients(base_path / 'additional_to.txt')
    if additional_to:
        write_to_txt(additional_to, base_path / 'to.txt')
        print(f"Appended {len(additional_to)} email(s) from additional_to.txt to to.txt")
        logging.debug(f"Additional emails appended: {additional_to}")

    deduplicate_file(base_path / 'to.txt')


def send_email_from_folder(base_folder: str, dry_run: bool = False, batch_size: int = 500, delay: int = 5) -> None:
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

    if not subject:
        print("Error: subject.txt is missing or empty. Exiting.")
        logging.error("subject.txt is missing or empty.")
        sys.exit(1)

    if not body_html:
        print("Error: body.html is missing or empty. Exiting.")
        logging.error("body.html is missing or empty.")
        sys.exit(1)

    if not approvers:
        print("Approver list is empty.")
        logging.warning("Approver list is empty.")
        return

    prepare_to_txt(base_path)
    attachments = get_attachments(base_path)

    if dry_run:
        print("Dry-run mode: Draft email sent to approvers only.")
        send_email(from_email, "[DRAFT] " + subject, body_html, approvers, [], [], attachments=attachments)
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

    for i in range(0, len(to_emails), batch_size):
        batch = to_emails[i:i + batch_size]
        logging.debug(f"Sending batch {i // batch_size + 1}: {batch}")
        send_email(from_email, subject, body_html, batch, cc_emails, bcc_emails, attachments=attachments)
        total_sent += len(batch)
        if i + batch_size < len(to_emails):
            print(f"Waiting {delay} seconds before sending next batch...")
            logging.info(f"Waiting {delay} seconds before sending next batch...")
            time.sleep(delay)

    print("Emails sent successfully.")
    print(f"Summary:\n - Sent: {total_sent}")
    logging.info(f"Email Summary -> Sent: {total_sent}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="NotifyBot Email Sender")
    parser.add_argument("base_folder", help="Base folder containing email files")
    parser.add_argument("--dry-run", action="store_true", help="Only send draft to approver, skip actual email send")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of emails to send per batch (default: 500)")
    parser.add_argument("--delay", type=int, default=5, help="Seconds to wait between batches (default: 5)")
    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help="Set logging level (default: INFO)"
    )

    args = parser.parse_args()

    # Configure logging only when the script runs directly
    # File handler (no colors)
    file_handler = logging.FileHandler('notifybot.log', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s'
    ))

    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s'
    ))

    logger = logging.getLogger()
    logger.handlers = []  # Clear existing handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    numeric_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    send_email_from_folder(args.base_folder, dry_run=args.dry_run, batch_size=args.batch_size, delay=args.delay)
