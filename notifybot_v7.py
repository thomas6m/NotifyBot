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
                            - body.html         (email body)
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
import os
import json
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import List, Tuple, Dict

from email_validator import validate_email, EmailNotValidError

# Path configurations
NOTIFYBOT_ROOT = Path("/notifybot")  # Root directory
LOG_FILENAME = NOTIFYBOT_ROOT / "logs" / "notifybot.log"  # Log file location
INVENTORY_PATH = NOTIFYBOT_ROOT / "inventory" / "inventory.csv"  # New location of inventory.csv

class MissingRequiredFilesError(Exception):
    """Exception raised when required input files are missing."""


def csv_log_entry(message: str) -> str:
    """Generate log entry in CSV format."""
    timestamp_epoch = int(time.time())  # Epoch timestamp
    username = os.getlogin()  # Get the username of the executor
    return f"{timestamp_epoch},{username},{message}"

def setup_logging() -> None:
    """Configure logging to INFO+ level in LOG_FILENAME with structured CSV format."""
    def log_and_print(level: str, message: str) -> None:
        """Log and color-print a message at INFO/WARNING/ERROR levels in CSV format."""
        # Define emojis for different log levels and events
        emoji_map = {
            "info": "ℹ️",          # Information
            "warning": "⚠️",       # Warning
            "error": "❌",          # Error
            "success": "✅",        # Success
            "processing": "⏳",     # Processing
            "backup": "💾",         # File backup
            "file": "📂",           # File handling
            "confirmation": "✋"    # User confirmation
        }

        # Generate the log entry in CSV format
        csv_log = csv_log_entry(message)
        
        # Log the entry to the file in plain format
        log_func = getattr(logging, level.lower(), logging.info)
        log_func(csv_log)
        
        # Print the log to the console with an emoji (only for console output, not in the log file)
        emoji = emoji_map.get(level.lower(), "ℹ️")  # Default to "ℹ️" if level is unknown
        print(f"{emoji} {csv_log}")  # Print with emoji in console

    globals()['log_and_print'] = log_and_print

def rotate_log_file() -> None:
    """Rotate current log file with a timestamp suffix."""
    log_path = LOG_FILENAME
    if log_path.is_file():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated = log_path.with_name(f"notifybot_{timestamp}.log")
        try:
            log_path.rename(rotated)
            log_and_print("info", f"Rotated log file to {rotated.name}")
        except Exception as exc:
            log_and_print("error", f"Failed to rotate log file: {exc}")

def is_valid_email(email: str) -> bool:
    """Check email syntax using email_validator."""
    try:
        validate_email(email.strip(), check_deliverability=False)
        return True
    except EmailNotValidError as exc:
        log_and_print("error", f"Invalid email format: {email}. Error: {exc}")
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
    valid = []
    if not path.is_file():
        log_and_print("warning", f"{path.name} missing, skipping.")
        return valid
    
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            for email in extract_emails(line.strip(), delimiters):
                if is_valid_email(email):
                    valid.append(email)
                else:
                    log_and_print("warning", f"Invalid email skipped: {email}")
    except Exception as exc:
        log_and_print("error", f"Error processing recipients in {path}: {exc}")
    return valid

def deduplicate_file(path: Path) -> None:
    """Back up and deduplicate a file's lines."""
    if not path.is_file():
        return
    try:
        backup = path.with_name(f"{path.stem}_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}")
        shutil.copy2(path, backup)
        log_and_print("backup", f"Backup created: {backup.name}")
        
        unique, seen = [], set()
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and line not in seen:
                seen.add(line)
                unique.append(line)
        
        path.write_text("\n".join(unique) + "\n", encoding="utf-8")
        log_and_print("info", f"Deduplicated {path.name}")
    except Exception as exc:
        log_and_print("error", f"Error during file deduplication for {path}: {exc}")

def check_required_files(base: Path, required: List[str], dry_run: bool = True) -> None:
    """Ensure required files exist. In real mode, ensure valid recipient source."""
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        raise MissingRequiredFilesError(f"Missing required files: {', '.join(missing)}")
    
    if not dry_run:
        has_to = (base / "to.txt").is_file()
        has_filters = (base / "filter.txt").is_file() and INVENTORY_PATH.is_file()
        if not (has_to or has_filters):
            raise MissingRequiredFilesError(
                "Missing recipient source: Provide either 'to.txt' or both 'filter.txt' and 'inventory.csv'."
            )

def send_email(recipients: List[str], subject: str, body_html: str, attachments: List[Path], from_address: str, dry_run: bool = False) -> None:
    """Compose and send email via localhost SMTP or simulate if dry_run."""
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, from_address, ", ".join(recipients)
    msg.add_alternative(body_html, subtype="html")
    
    max_size = 15 * 1024 * 1024  # 15MB max attachment size
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
            log_and_print("file", f"Attached: {path.name}")
        except Exception as exc:
            log_and_print("error", f"Error attaching file {path.name}: {exc}")
    
    if dry_run:
        log_and_print("info", f"[DRY RUN] Would send to: {msg['To']}")
        return
    
    try:
        with smtplib.SMTP("localhost") as server:
            server.send_message(msg)
        log_and_print("success", f"Email sent to {msg['To']}")
    except Exception as exc:
        log_and_print("error", f"SMTP error while sending email: {exc}")

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
        raise MissingRequiredFilesError("No recipients found! Please check input files.")
    
    if not force:
        log_and_print("confirmation", "Ready to send emails. Press Enter to confirm or Ctrl+C to abort...")
        input()

    # Split into batches to prevent spamming
    batches = [recipients[i:i + batch_size] for i in range(0, len(recipients), batch_size)]
    for batch in batches:
        send_email(batch, subject, body_html, attachments, from_address, dry_run=dry_run)
        log_and_print("info", f"Batch of {len(batch)} emails sent. Sleeping for {delay} seconds...")
        time.sleep(delay)

# Command-line arguments parsing
def main():
    parser = argparse.ArgumentParser(description="NotifyBot Email Sender")
    parser.add_argument("--base-folder", required=True, type=str, help="Base folder containing email resources (e.g., 'emails').")
    parser.add_argument("--attachment-folder", default="attachment", type=str, help="Folder for attachments.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate email sending without sending actual emails.")
    parser.add_argument("--batch-size", default=500, type=int, help="Number of emails per batch.")
    parser.add_argument("--delay", default=5.0, type=float, help="Delay in seconds between batches.")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt.")
    args = parser.parse_args()

    setup_logging()  # Set up logging with CSV format

    # Construct the full path inside /notifybot/basefolder/
    base_folder = NOTIFYBOT_ROOT / "basefolder" / args.base_folder
    
    # Ensure the provided folder is inside /notifybot/basefolder
    if not base_folder.exists() or not base_folder.is_dir():
        log_and_print("error", f"Invalid base folder: {base_folder}. Folder does not exist or is not a directory.")
        sys.exit(1)

    attachment_folder = args.attachment_folder
    dry_run = args.dry_run
    batch_size = args.batch_size
    delay = args.delay
    force = args.force

    try:
        send_email_from_folder(base_folder, attachment_folder, dry_run, batch_size, delay, force)
    except MissingRequiredFilesError as e:
        log_and_print("error", str(e))
        sys.exit(1)
    except Exception as e:
        log_and_print("error", f"Unexpected error: {e}\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
