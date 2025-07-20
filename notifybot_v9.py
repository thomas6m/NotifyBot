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
import sys
import time
import traceback
import os
import json
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import List, Tuple, Dict
import subprocess
from email_validator import validate_email, EmailNotValidError

# Path configurations
NOTIFYBOT_ROOT = Path("/notifybot")  # Root directory
BASEFOLDER_PATH = NOTIFYBOT_ROOT / "basefolder"  # Enforced base folder location
LOG_FILENAME = NOTIFYBOT_ROOT / "logs" / "notifybot.log"  # Log file location
INVENTORY_PATH = NOTIFYBOT_ROOT / "inventory" / "inventory.csv"  # New location of inventory.csv

class MissingRequiredFilesError(Exception):
    """Exception raised when required input files are missing."""

def validate_base_folder(base_folder: str) -> Path:
    """Ensure that the base folder is a valid relative path inside /notifybot/basefolder"""
    base_folder_path = BASEFOLDER_PATH / base_folder
    
    # Ensure the base folder is inside /notifybot/basefolder
    if not base_folder_path.is_dir():
        raise ValueError(f"Invalid base folder: {base_folder}. It must be a directory inside '/notifybot/basefolder'.")

    # Return the validated path
    return base_folder_path

def csv_log_entry(message: str) -> str:
    """Generate log entry in CSV format."""
    timestamp_epoch = int(time.time())  # Epoch timestamp
    username = os.getlogin()  # Get the username of the executor
    return f"{timestamp_epoch},{username},{message}"

def setup_logging() -> None:
    """Configure logging to INFO+ level in LOG_FILENAME with structured CSV format."""
    def log_and_print(level: str, message: str) -> None:
        """Log and color-print a message at INFO/WARNING/ERROR levels in CSV format."""
        # Emoji mappings for log levels
        emoji_mapping = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
            "processing": "⏳",
            "backup": "💾",
            "file": "📂",
            "confirmation": "✋"
        }

        # Get emoji for level
        emoji = emoji_mapping.get(level.lower(), "")
        csv_log = csv_log_entry(f"{emoji} {message}")
        log_func = getattr(logging, level.lower(), logging.info)
        log_func(csv_log)
        print(f"{csv_log}")  # Print to the console as well

    globals()['log_and_print'] = log_and_print

def rotate_log_file() -> None:
    """Rotate current log file with a timestamp suffix."""
    log_path = LOG_FILENAME
    if log_path.is_file():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated = log_path.with_name(f"notifybot_{timestamp}.log")
        try:
            log_path.rename(rotated)
            log_and_print("info", f"Log file rotated: {rotated.name}")
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
        log_and_print("backup", f"💾 Backup created: {backup.name}")
        
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

def sanitize_filename(filename: str) -> str:
    """Sanitize the filename to prevent issues with special characters."""
    return re.sub(r"[^\w\s.-]", "", filename)

def send_email(recipients: List[str], subject: str, body_html: str, attachments: List[Path], from_address: str, dry_run: bool = False) -> None:
    """Compose and send email via sendmail or simulate if dry_run."""
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, from_address, ", ".join(recipients)
    msg.add_alternative(body_html, subtype="html")
    
    # Add attachments (same logic as before)
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
    
    # Convert the message to a string
    email_message = msg.as_string()
    
    try:
        # Prepare the sendmail subprocess
        p = subprocess.Popen(
            ["/usr/sbin/sendmail", "-t", "-oi"], 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        # Send the email by writing the message to the sendmail process
        stdout, stderr = p.communicate(email_message.encode('utf-8'))
        
        # Check for any errors
        if p.returncode != 0:
            log_and_print("error", f"Failed to send email: {stderr.decode('utf-8')}")
        else:
            log_and_print("success", f"✅ Email sent to {msg['To']} via sendmail")
    
    except Exception as exc:
        log_and_print("error", f"Failed to send email using sendmail: {exc}")

def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Automated email batch sender with filtering, logging, and dry-run support.")
    parser.add_argument("--base-folder", required=True, help="Base directory containing email input files (must be inside /notifybot/basefolder)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate sending emails without SMTP")
    parser.add_argument("--attachment-folder", help="Subfolder containing attachments (default: 'attachment')")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of emails per batch (default: 500)")
    parser.add_argument("--delay", type=float, default=5.0, help="Delay in seconds between batches (default: 5.0)")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt (for automation)")
    args = parser.parse_args()

    setup_logging()
    rotate_log_file()

    # Validate the base folder path to ensure it's inside /notifybot/basefolder
    try:
        base_folder = validate_base_folder(args.base_folder)
        print(f"Base folder is validated: {base_folder}")
        
        # Define base folder and required files
        required_files = ["subject.txt", "body.html", "from.txt", "to.txt", "filter.txt"]
        
        # Check for required files
        check_required_files(base_folder, required_files, args.dry_run)
        # Perform further tasks based on the dry run or real mode...
    except ValueError as e:
        print(f"Error: {e}")
        return  # Exit if the base folder is invalid
    except MissingRequiredFilesError as e:
        log_and_print("error", str(e))

if __name__ == "__main__":
    main()
