#!/usr/bin/env python3
"""
NotifyBot: Automated email batch sender with filtering, logging, and dry-run support.

Usage:
    python notifybot.py --base-folder emails --dry-run
    python notifybot.py --base-folder emails --attachment-folder attachments
    python notifybot.py --base-folder emails --force

CLI Options:
    --base-folder         Base directory containing email input files [REQUIRED]. 
                          The directory should be inside /notifybot/basefolder.
                          Required files inside base folder:
                            - subject.txt       (email subject)
                            - body.html         (email body HTML)
                            - from.txt          (email From address)
                            - approver.txt      (approver emails for dry-run)
                          Recipient source (at least one required for real email mode):
                            - to.txt                    List of recipient emails
                            - filter.txt + inventory.csv   Filter-based recipient extraction
    --dry-run             Simulate sending emails without SMTP.
    --attachment-folder   Subfolder containing attachments (default: "attachment").
    --batch-size          Number of emails to send per batch (default: 500).
    --delay               Delay in seconds between batches (default: 5.0).
    --force               Skip confirmation prompt (for automation).
"""

import argparse
import csv
import logging
import mimetypes
import re
import shutil
import smtplib
import sys
import time
import traceback
import unicodedata
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import List, Tuple, Dict

from email_validator import validate_email, EmailNotValidError

# Path configurations
NOTIFYBOT_ROOT = Path("/notifybot")  # Root directory
LOG_FILENAME = NOTIFYBOT_ROOT / "logs" / "notifybot.log"  # Log file location

class MissingRequiredFilesError(Exception):
    """Exception raised when required input files are missing."""


def rotate_log_file() -> None:
    """Rotate current log file with a timestamp suffix."""
    log_path = LOG_FILENAME
    if log_path.is_file():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated = log_path.with_name(f"notifybot_{timestamp}.log")
        try:
            log_path.rename(rotated)
            print(f"Rotated log file to {rotated.name}")
        except Exception as exc:
            print(f"\033[91mFailed to rotate log file: {exc}\033[0m")


def setup_logging() -> None:
    """Configure logging to INFO+ level in LOG_FILENAME."""
    logging.basicConfig(
        filename=LOG_FILENAME,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s",
    )


def log_and_print(level: str, message: str) -> None:
    """Log and color-print a message at INFO/WARNING/ERROR levels."""
    level_lower = level.lower()
    colors = {"info": "\033[94m", "warning": "\033[93m", "error": "\033[91m"}
    color = colors.get(level_lower, "\033[0m")
    log_func = getattr(logging, level_lower, logging.info)
    log_func(message)
    print(f"{color}{message}\033[0m")


def is_valid_email(email: str) -> bool:
    """Check email syntax using email_validator."""
    try:
        validate_email(email.strip(), check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def read_file(path: Path) -> str:
    """Read text file content and strip, or log an error."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        log_and_print("error", f"Failed to read {path}: {exc}")
        return ""


def extract_emails(raw: str, delimiters: str = ";") -> List[str]:
    """Split and trim emails from a raw string by delimiters."""
    if not raw:
        return []
    return [e.strip() for e in re.split(f"[{re.escape(delimiters)}]", raw) if e.strip()]


def read_recipients(path: Path, delimiters: str = ";") -> List[str]:
    """Read and validate emails from a file (semicolon-separated)."""
    if not path.is_file():
        log_and_print("warning", f"{path.name} missing, skipping.")
        return []
    valid = []
    for line in path.read_text(encoding="utf-8").splitlines():
        for email in extract_emails(line.strip(), delimiters):
            if is_valid_email(email):
                valid.append(email)
            else:
                log_and_print("warning", f"Invalid email skipped: {email}")
    return valid


def deduplicate_file(path: Path) -> None:
    """Back up and deduplicate a file's lines."""
    if not path.is_file():
        return
    backup = path.with_name(f"{path.stem}_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}")
    shutil.copy2(path, backup)
    log_and_print("info", f"Backup created: {backup.name}")
    unique, seen = [], set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and line not in seen:
            seen.add(line)
            unique.append(line)
    path.write_text("\n".join(unique) + "\n", encoding="utf-8")
    log_and_print("info", f"Deduplicated {path.name}")


def check_required_files(base: Path, required: List[str], dry_run: bool = True) -> None:
    """Ensure required files exist. In real mode, ensure valid recipient source."""
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        raise MissingRequiredFilesError(f"Missing required files: {', '.join(missing)}")
    if not dry_run:
        has_to = (base / "to.txt").is_file()
        has_filters = (base / "filter.txt").is_file() and (base / "inventory.csv").is_file()
        if not (has_to or has_filters):
            raise MissingRequiredFilesError(
                "Missing recipient source: Provide either 'to.txt' or both 'filter.txt' and 'inventory.csv'."
            )


def send_email(recipients: List[str], subject: str, body_html: str, attachments: List[Path], from_address: str, dry_run: bool = False) -> None:
    """Compose and send email via localhost SMTP or simulate if dry_run."""
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, from_address, ", ".join(recipients)
    msg.add_alternative(body_html, subtype="html")
    max_size = 15 * 1024 * 1024
    for path in attachments:
        if not path.is_file():
            continue
        try:
            if path.stat().st_size > max_size:
                log_and_print("warning", f"Skipping large attachment: {path.name}")
                continue
            data = path.read_bytes()
            ctype, _ = mimetypes.guess_type(path.name)
            maint, sub = (ctype or "application/octet-stream").split("/", 1)
            msg.add_attachment(data, maintype=maint, subtype=sub, filename=sanitize_filename(path.name))
            log_and_print("info", f"Attached: {path.name}")
        except Exception as exc:
            log_and_print("error", f"Attachment error: {exc}")
    if dry_run:
        log_and_print("info", f"[DRY RUN] Would send to: {msg['To']}")
        return
    try:
        with smtplib.SMTP("localhost") as server:
            server.send_message(msg)
        log_and_print("info", f"Email sent to {msg['To']}")
    except Exception as exc:
        log_and_print("error", f"SMTP error: {exc}")


def send_email_from_folder(base: Path, attachment_subfolder: str, dry_run: bool, batch_size: int = 500, delay: float = 5.0, force: bool = False) -> None:
    """Main logic: load files, decide mode, gather recipients, and dispatch."""
    required_files = ["body.html", "subject.txt", "from.txt", "approver.txt"]
    check_required_files(base, required_files, dry_run=dry_run)

    from_address = read_file(base / "from.txt")
    if not from_address or not is_valid_email(from_address):
        raise MissingRequiredFilesError("Invalid or missing From address in from.txt")

    subject = read_file(base / "subject.txt")
    body_html = read_file(base / "body.html")
    approvers = read_recipients(base / "approver.txt")
    recipients = read_recipients(base / "to.txt")
    if not dry_run:
        if not recipients:
            recipients = read_recipients(base / "filter.txt")  # Default filter-based recipient
    attachments = list(Path(base / attachment_subfolder).glob("*"))

    if not dry_run and not recipients:
        raise MissingRequiredFilesError("No valid recipients found in to.txt or filters.")

    log_and_print("info", f"Processing batch: {len(recipients)} recipients")
    
    # Batch sending logic
    for i in range(0, len(recipients), batch_size):
        batch_recipients = recipients[i:i+batch_size]
        send_email(batch_recipients, subject, body_html, attachments, from_address, dry_run)
        if not dry_run:
            log_and_print("info", f"Waiting {delay} seconds before sending next batch")
            time.sleep(delay)


def validate_base_folder(base_folder: str) -> Path:
    """Ensure the base folder is within /notifybot/basefolder/."""
    notifybot_basefolder = Path("/notifybot/basefolder")
    base_path = notifybot_basefolder / base_folder
    
    # Check if the resolved absolute path starts with /notifybot/basefolder/
    if not base_path.resolve().is_relative_to(notifybot_basefolder.resolve()):
        raise ValueError(f"Base folder must be inside {notifybot_basefolder}.")
    
    if not base_path.is_dir():
        raise ValueError(f"The folder '{base_folder}' does not exist inside {notifybot_basefolder}.")
    
    return base_path


def main():
    parser = argparse.ArgumentParser(description="NotifyBot Email Batch Sender")
    parser.add_argument("--base-folder", required=True, help="Base folder name inside /notifybot/basefolder/")
    parser.add_argument("--dry-run", action="store_true", help="Simulate email sending.")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of emails per batch.")
    parser.add_argument("--delay", type=float, default=5.0, help="Delay in seconds between batches.")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompts.")
    parser.add_argument("--attachment-folder", default="attachment", help="Subfolder for attachments.")
    
    args = parser.parse_args()

    # Validate base-folder path
    try:
        base_path = validate_base_folder(args.base_folder)
    except ValueError as e:
        log_and_print("error", str(e))
        sys.exit(1)

    setup_logging()
    rotate_log_file()

    try:
        send_email_from_folder(base_path, args.attachment_folder, args.dry_run, args.batch_size, args.delay, args.force)
    except Exception as e:
        log_and_print("error", f"Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
