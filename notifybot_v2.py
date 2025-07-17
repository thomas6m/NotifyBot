#!/usr/bin/env python3
"""
NotifyBot: Automated email batch sender with filtering, logging, and dry-run support.

Usage:
    python notifybot.py --base-folder ./emails --dry-run
    python notifybot.py --base-folder ./emails --attachment-folder attachments
    python notifybot.py --base-folder ./emails --force

CLI Options:
    --base-folder         Base directory containing email input files [REQUIRED].
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

LOG_FILENAME = "notifybot.log"

class MissingRequiredFilesError(Exception):
    """Exception raised when required input files are missing."""

def rotate_log_file() -> None:
    """Rotate current log file with a timestamp suffix."""
    log_path = Path(LOG_FILENAME)
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

def parse_filter_file(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """Parse filter.csv into rows with default modes and regex_flags."""
    try:
        reader = csv.DictReader(path.open("r", newline="", encoding="utf-8"))
        rows = list(reader)
        for r in rows:
            r.setdefault("mode", "exact")
            r.setdefault("regex_flags", "")
        return reader.fieldnames or [], rows
    except Exception as exc:
        log_and_print("error", f"Failed to parse filter file: {exc}")
        return [], []

def match_condition(actual: str, expected: str, mode: str, regex_flags: str = "") -> bool:
    """Match a value by exact, contains, or regex."""
    actual, expected = actual.strip(), expected.strip()
    if mode == "exact":
        return actual.lower() == expected.lower()
    if mode == "contains":
        return expected.lower() in actual.lower()
    if mode == "regex":
        flags = 0
        for flag in regex_flags.upper().split("|"):
            flags |= getattr(re, flag, 0)
        try:
            return bool(re.search(expected, actual, flags))
        except re.error as exc:
            log_and_print("warning", f"Regex error: {exc}")
            return False
    return actual.lower() == expected.lower()

def get_filtered_emailids(base: Path, delimiters: str = ";") -> List[str]:
    """Return unique filtered emails from inventory minus any already in to.txt."""
    inv, filt = base / "inventory.csv", base / "filter.txt"
    if not inv.is_file() or not filt.is_file():
        return []
    _, filters = parse_filter_file(filt)
    found = set()
    with inv.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if all(match_condition(row.get(f["field"], ""), f["value"], f["mode"], f.get("regex_flags", "")) for f in filters):
                for email in extract_emails(row.get("emailids", ""), delimiters):
                    if email.strip():
                        found.add(email.strip())
    existing = set(read_recipients(base / "to.txt", delimiters))
    return sorted(e for e in found - existing if is_valid_email(e))

def sanitize_filename(filename: str) -> str:
    """Normalize filenames to ASCII, safe characters only."""
    name = unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore").decode("ASCII")
    sanitized = re.sub(r"[^\w\.-]", "_", name)
    return sanitized or "attachment"

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

    subject, body_html = read_file(base / "subject.txt"), read_file(base / "body.html")
    attachments = list((base / attachment_subfolder).glob("*")) if (base / attachment_subfolder).is_dir() else []

    if dry_run:
        approvers = read_recipients(base / "approver.txt")
        if not approvers:
            log_and_print("warning", "No approvers found for dry-run mode.")
            return
        log_and_print("info", f"[DRY RUN] Sending test email to: {', '.join(approvers)}")
        send_email(approvers, subject, body_html, attachments, from_address, dry_run=True)
        return

    to_path, filt_path, inv_path = base / "to.txt", base / "filter.txt", base / "inventory.csv"
    has_to, has_filters = to_path.is_file(), (filt_path.is_file() and inv_path.is_file())
    emails = set()

    if has_to:
        emails.update(read_recipients(to_path))
        deduplicate_file(to_path)
    if has_filters:
        new = get_filtered_emailids(base)
        if new:
            emails.update(new)
            with to_path.open("a", encoding="utf-8") as f:
                f.write("\n".join(new) + "\n")
            deduplicate_file(to_path)
            log_and_print("info", f"to.txt updated with {len(new)} filtered emails.")

    emails = sorted(emails)
    if not emails:
        raise MissingRequiredFilesError("No recipients to send email to.")

    if not force:
        confirm = input(f"Send emails to {len(emails)} users? (yes/no): ").strip().lower()
        if confirm != "yes":
            log_and_print("info", "Operation aborted by user.")
            return

    for i in range(0, len(emails), batch_size):
        batch = emails[i:i+batch_size]
        log_and_print("info", f"Sending batch {i//batch_size+1} with {len(batch)} recipients...")
        send_email(batch, subject, body_html, attachments, from_address, dry_run=False)
        time.sleep(delay)

def main() -> int:
    """CLI parsing and invocation."""
    rotate_log_file()
    setup_logging()
    parser = argparse.ArgumentParser(description="NotifyBot - Email Batch Sender")
    parser.add_argument("--base-folder", type=str, required=True, help="Base dir with email input files.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate sending emails.")
    parser.add_argument("--attachment-folder", type=str, default="attachment", help="Subfolder with attachments.")
    parser.add_argument("--batch-size", type=int, default=500, help="Emails per batch.")
    parser.add_argument("--delay", type=float, default=5.0, help="Delay seconds between batches.")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt.")
    args = parser.parse_args()

    base = Path(args.base_folder)
    if not base.is_dir():
        log_and_print("error", f"Invalid base folder: {args.base_folder}")
        return 1

    try:
        send_email_from_folder(base, args.attachment_folder, args.dry_run, args.batch_size, args.delay, args.force)
        return 0
    except MissingRequiredFilesError as exc:
        log_and_print("error", str(exc))
        return 1
    except Exception as e:
        log_and_print("error", f"Unhandled error: {e}")
        log_and_print("error", traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
