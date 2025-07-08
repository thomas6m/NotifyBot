#!/usr/bin/env python3
"""
NotifyBot: Automated email batch sender with filtering, logging, and dry-run support.

Usage:
    python notifybot.py --dry-run
    python notifybot.py --attachment-folder attachments

CLI Options:
    --dry-run             Simulate sending emails without actual SMTP send.
    --attachment-folder   Subfolder containing attachments (default: "attachment").
    --batch-size          Number of emails to send per batch (default: 30).
    --delay               Delay in seconds between batches (default: 1.0).

Expected Structure:
    base/
    ├── body.html
    ├── subject.txt
    ├── to.txt
    ├── inventory.csv      # Optional, used with filter.txt
    ├── filter.txt         # Optional, CSV format filter conditions
    └── attachment/        # Folder with files to attach
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
    """
    Rotate the log file by renaming the current log with a timestamp suffix.

    If the log file does not exist, this function does nothing.
    """
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
    """
    Configure logging to output INFO and above to a log file with a detailed format.
    """
    logging.basicConfig(
        filename=LOG_FILENAME,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s",
    )


def log_and_print(level: str, message: str) -> None:
    """
    Log a message at the specified level and print it with color coding to the console.

    Args:
        level (str): Logging level as string ('info', 'warning', 'error').
        message (str): The message to log and print.
    """
    level = level.lower()
    colors = {"info": "\033[94m", "warning": "\033[93m", "error": "\033[91m"}
    color = colors.get(level, "\033[0m")
    getattr(logging, level, logging.info)(message)
    print(f"{color}{message}\033[0m")


def is_valid_email(email: str) -> bool:
    """
    Validate the email address using the email_validator library.

    Args:
        email (str): The email address to validate.

    Returns:
        bool: True if email is valid, False otherwise.
    """
    try:
        validate_email(email.strip())
        return True
    except EmailNotValidError:
        return False


def read_file(path: Path) -> str:
    """
    Read the content of a file as a UTF-8 string, stripped of whitespace.

    Args:
        path (Path): Path to the file.

    Returns:
        str: File content or empty string if reading fails.
    """
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        log_and_print("error", f"Failed to read file {path}: {exc}")
        return ""


def extract_emails(raw: str, delimiters: str = ";") -> List[str]:
    """
    Extract and split emails from a raw string using delimiters.

    Args:
        raw (str): Raw string containing email addresses.
        delimiters (str): Delimiters to split on (default ';').

    Returns:
        List[str]: List of extracted email addresses.
    """
    if not raw:
        return []
    return [e.strip() for e in re.split(f"[{re.escape(delimiters)}]", raw) if e.strip()]


def read_recipients(path: Path, delimiters: str = ";") -> List[str]:
    """
    Read recipient email addresses from a text file, validating each.

    Args:
        path (Path): Path to the recipient file.
        delimiters (str): Delimiters for separating emails on a line.

    Returns:
        List[str]: List of valid email addresses.
    """
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
    """
    Deduplicate lines in a file, backing up the original before rewriting.

    Args:
        path (Path): Path to the file to deduplicate.
    """
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
    """
    Check that all required files exist in the base directory.

    Args:
        base (Path): Base directory path.
        required (List[str]): List of required filenames.

    Raises:
        MissingRequiredFilesError: If any required files are missing.
    """
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        raise MissingRequiredFilesError(f"Missing: {', '.join(missing)}")


def parse_filter_file(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Parse the filter CSV file to extract filter conditions.

    Args:
        path (Path): Path to filter file.

    Returns:
        Tuple[List[str], List[Dict[str, str]]]: Tuple of header fieldnames and list of filter dicts.
    """
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
    """
    Check if a string matches an expected value using different matching modes.

    Args:
        actual (str): Actual string to test.
        expected (str): Expected string or pattern.
        mode (str): Matching mode: 'exact', 'contains', or 'regex'.
        regex_flags (str): Optional regex flags separated by '|'.

    Returns:
        bool: True if the condition matches, else False.
    """
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
    """
    Retrieve email IDs filtered according to conditions defined in filter.txt and inventory.csv.

    Args:
        base (Path): Base directory path containing filter and inventory files.
        delimiters (str): Delimiters used in email lists.

    Returns:
        List[str]: List of filtered, validated email addresses excluding those already in to.txt.
    """
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
    """
    Sanitize a filename by removing non-ASCII characters and replacing invalid chars.

    Args:
        filename (str): Original filename.

    Returns:
        str: Sanitized filename safe for email attachment.
    """
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
    """
    Compose and send an email message with optional attachments.

    Args:
        recipients (List[str]): List of recipient email addresses.
        subject (str): Email subject.
        body_html (str): Email body in HTML format.
        attachments (List[Path]): List of paths to attach files.
        dry_run (bool): If True, simulate sending without SMTP.
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "notifybot@example.com"
    msg["To"] = ", ".join(recipients)
    msg.add_alternative(body_html, subtype="html")

    max_size = 15 * 1024 * 1024  # 15 MB
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
    """
    Send emails in batches using data and files located in a base folder.

    Args:
        base (Path): Base directory containing required files.
        attachment_subfolder (str): Subfolder name for attachments.
        dry_run (bool): If True, simulate sending emails without actual SMTP send.
        batch_size (int): Number of emails to send per batch.
        delay (float): Delay in seconds between batches.

    Raises:
        MissingRequiredFilesError: If required files are missing.
        Exception: If no recipients are found.
    """
    check_required_files(base, ["body.html", "subject.txt"])
    to_txt_path = base / "to.txt"
    filter_path = base / "filter.txt"
    inventory_path = base / "inventory.csv"

    emails = set()

    # Read existing to.txt emails if present
    if to_txt_path.is_file():
        emails.update(read_recipients(to_txt_path))
        deduplicate_file(to_txt_path)

    # If filter and inventory files exist, get filtered emails
    if filter_path.is_file() and inventory_path.is_file():
        filtered_emails = get_filtered_emailids(base)
        emails.update(filtered_emails)

        # Always update to.txt with filtered emails regardless of dry-run
        if filtered_emails:
            with to_txt_path.open("a", encoding="utf-8") as f:
                for email in filtered_emails:
                    f.write(email + "\n")
            deduplicate_file(to_txt_path)
            log_and_print(
                "info",
                f"to.txt generated/updated with {len(filtered_emails)} filtered emails.",
            )

        if dry_run:
            # Skip actual sending in dry-run mode after updating to.txt
            return

    if not emails:
        raise Exception("No recipients to send email to.")

    emails = sorted(emails)
    subject = read_file(base / "subject.txt")
    body_html = read_file(base / "body.html")
    attachments = (
        list((base / attachment_subfolder).glob("*"))
        if (base / attachment_subfolder).is_dir()
        else []
    )

    for i in range(0, len(emails), batch_size):
        batch = emails[i : i + batch_size]
        log_and_print("info", f"Sending batch {i // batch_size + 1} with {len(batch)} recipients...")
        send_email(batch, subject, body_html, attachments, dry_run=dry_run)
        time.sleep(delay)


def main() -> int:
    """
    Main entry point: parses CLI arguments and sends emails accordingly.

    Returns:
        int: Exit code, 0 on success, 1 on error.
    """
    rotate_log_file()
    setup_logging()

    parser = argparse.ArgumentParser(description="NotifyBot - Email Batch Sender")
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate sending emails without SMTP."
    )
    parser.add_argument(
        "--attachment-folder",
        type=str,
        default="attachment",
        help="Folder name for attachments.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=30,
        help="Number of emails to send per batch.",
    )
    parser.add_argument(
        "--delay", type=float, default=1.0, help="Delay in seconds between batches."
    )
    args = parser.parse_args()

    base_folder = Path(__file__).parent / "base"
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
