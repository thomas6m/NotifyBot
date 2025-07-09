#!/usr/bin/env python3
"""
NotifyBot: Automated email batch sender with filtering, logging, and dry-run support.

Usage:
    python notifybot.py --base-folder ./emails --dry-run
    python notifybot.py --base-folder ./emails --attachment-folder attachments

CLI Options:
    --base-folder         Base directory containing email input files [REQUIRED].
    --dry-run             Simulate sending emails without actual SMTP send.
    --attachment-folder   Subfolder containing attachments (default: "attachment").
    --batch-size          Number of emails to send per batch (default: 30).
    --delay               Delay in seconds between batches (default: 1.0).
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
    log_path = Path(LOG_FILENAME)
    if log_path.is_file():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_name = log_path.with_name(f"notifybot_{timestamp}.log")
        try:
            log_path.rename(rotated_name)
            print(f"Rotated log file to {rotated_name.name}")
        except Exception as exc:
            print(f"\033[91mFailed to rotate log file: {exc}\033[0m")


def setup_logging() -> None:
    logging.basicConfig(
        filename=LOG_FILENAME,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s",
    )


def log_and_print(level: str, message: str) -> None:
    level = level.lower()
    colors = {"info": "\033[94m", "warning": "\033[93m", "error": "\033[91m"}
    color = colors.get(level, "\033[0m")
    getattr(logging, level, logging.info)(message)
    print(f"{color}{message}\033[0m")


def is_valid_email(email: str) -> bool:
    try:
        validate_email(email.strip())
        return True
    except EmailNotValidError:
        return False


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        log_and_print("error", f"Failed to read file {path}: {exc}")
        return ""


def extract_emails(raw: str, delimiters: str = ";") -> List[str]:
    if not raw:
        return []
    return [e.strip() for e in re.split(f"[{re.escape(delimiters)}]", raw) if e.strip()]


def read_recipients(path: Path, delimiters: str = ";") -> List[str]:
    if not path.is_file():
        log_and_print("warning", f"{path.name} missing, skipping.")
        return []

    valid_emails = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            for email in extract_emails(line.strip(), delimiters):
                if is_valid_email(email):
                    valid_emails.append(email)
                else:
                    log_and_print("warning", f"Invalid email skipped: {email}")
    return valid_emails


def deduplicate_file(path: Path) -> None:
    if not path.is_file():
        return

    backup = path.with_name(f"{path.stem}_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}")
    shutil.copy2(path, backup)
    log_and_print("info", f"Backup created: {backup.name}")

    seen = set()
    uniq = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            cleaned = line.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                uniq.append(cleaned)

    with path.open("w", encoding="utf-8") as f:
        f.writelines(line + "\n" for line in uniq)
    log_and_print("info", f"Deduplicated {path.name}")


def check_required_files(base: Path, required: List[str]) -> None:
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        raise MissingRequiredFilesError(f"Missing: {', '.join(missing)}")


def parse_filter_file(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            for row in rows:
                row.setdefault("mode", "exact")
                row.setdefault("regex_flags", "")
            return reader.fieldnames or [], rows
    except Exception as exc:
        log_and_print("error", f"Failed to parse filter file: {exc}")
        return [], []


def match_condition(actual: str, expected: str, mode: str, regex_flags: str = "") -> bool:
    actual = actual.strip()
    expected = expected.strip()
    if mode == "exact":
        return actual.lower() == expected.lower()
    if mode == "contains":
        return expected.lower() in actual.lower()
    if mode == "regex":
        flags = 0
        for flag in regex_flags.upper().split("|"):
            flags |= getattr(re, flag, 0)
        try:
            return re.search(expected, actual, flags=flags) is not None
        except re.error as e:
            log_and_print("warning", f"Regex error: {e}")
            return False
    return actual.lower() == expected.lower()


def get_filtered_emailids(base: Path, delimiters: str = ";") -> List[str]:
    inv = base / "inventory.csv"
    flt = base / "filter.txt"
    if not inv.is_file() or not flt.is_file():
        return []

    _, filters = parse_filter_file(flt)
    found = set()

    with inv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if all(
                match_condition(
                    row.get(f["field"], ""),
                    f["value"],
                    f["mode"],
                    f.get("regex_flags", ""),
                )
                for f in filters
            ):
                for e in extract_emails(row.get("emailids", ""), delimiters):
                    if e.strip():
                        found.add(e.strip())

    existing = set(read_recipients(base / "to.txt", delimiters))
    return [e for e in sorted(found - existing) if is_valid_email(e)]


def sanitize_filename(filename: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", filename)
        .encode("ASCII", "ignore")
        .decode("ASCII")
    )
    return re.sub(r"[^\w\.-]", "_", normalized) or "attachment"


def send_email(
    recipients: List[str],
    subject: str,
    body_html: str,
    attachments: List[Path],
    dry_run: bool = False,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "notifybot@example.com"
    msg["To"] = ", ".join(recipients)
    msg.add_alternative(body_html, subtype="html")

    max_size = 15 * 1024 * 1024
    for path in attachments:
        if not path.is_file():
            continue
        try:
            if path.stat().st_size > max_size:
                log_and_print("warning", f"Skipping large attachment: {path.name}")
                continue
            with path.open("rb") as f:
                data = f.read()
            ctype, _ = mimetypes.guess_type(path.name)
            maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
            msg.add_attachment(
                data,
                maintype=maintype,
                subtype=subtype,
                filename=sanitize_filename(path.name),
            )
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


def send_email_from_folder(
    base: Path,
    attachment_subfolder: str,
    dry_run: bool,
    batch_size: int = 30,
    delay: float = 1.0,
) -> None:
    check_required_files(base, ["body.html", "subject.txt", "from.txt", "approver.txt"])

    to_txt_path = base / "to.txt"
    filter_path = base / "filter.txt"
    inventory_path = base / "inventory.csv"

    emails = set()

    if to_txt_path.is_file():
        emails.update(read_recipients(to_txt_path))
        deduplicate_file(to_txt_path)

    if filter_path.is_file() and inventory_path.is_file():
        filtered_emails = get_filtered_emailids(base)
        emails.update(filtered_emails)

        if filtered_emails:
            with to_txt_path.open("a", encoding="utf-8") as f:
                for email in filtered_emails:
                    f.write(email + "\n")
            deduplicate_file(to_txt_path)
            log_and_print("info", f"to.txt updated with {len(filtered_emails)} filtered emails.")

        if dry_run:
            return

    emails = sorted(emails)
    if not dry_run:
        confirm = input(f"Send emails to {len(emails)} users? (yes/no): ").strip().lower()
        if confirm != "yes":
            log_and_print("info", "Operation aborted by user.")
            return

    if not emails:
        raise Exception("No recipients to send email to.")

    subject = read_file(base / "subject.txt")
    body_html = read_file(base / "body.html")
    attachments = list((base / attachment_subfolder).glob("*")) if (base / attachment_subfolder).is_dir() else []

    for i in range(0, len(emails), batch_size):
        batch = emails[i : i + batch_size]
        log_and_print("info", f"Sending batch {i // batch_size + 1} with {len(batch)} recipients...")
        send_email(batch, subject, body_html, attachments, dry_run=dry_run)
        time.sleep(delay)


def main() -> int:
    rotate_log_file()
    setup_logging()

    parser = argparse.ArgumentParser(description="NotifyBot - Email Batch Sender")
    parser.add_argument("--base-folder", type=str, required=True, help="Base directory containing email input files.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate sending emails without SMTP.")
    parser.add_argument("--attachment-folder", type=str, default="attachment", help="Folder name for attachments.")
    parser.add_argument("--batch-size", type=int, default=30, help="Number of emails to send per batch.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay in seconds between batches.")
    args = parser.parse_args()

    base_folder = Path(args.base_folder)
    if not base_folder.is_dir():
        log_and_print("error", f"Invalid base folder: {args.base_folder}")
        return 1

    try:
        send_email_from_folder(
            base_folder,
            args.attachment_folder,
            args.dry_run,
            batch_size=args.batch_size,
            delay=args.delay,
        )
        return 0
    except MissingRequiredFilesError as exc:
        log_and_print("error", str(exc))
        return 1
    except Exception as e:
        log_and_print("error", f"Unhandled error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
