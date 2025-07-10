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
                          Optional files:
                            - to.txt            (recipient emails list)
                            - filter.txt        (filters for inventory.csv)
                            - inventory.csv     (contact inventory)
    --dry-run             Simulate sending emails without actual SMTP send.
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
    """
    Rotate the current log file by renaming it with a timestamp suffix.

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
    Configure logging to write INFO and above level logs to the log file.
    """
    logging.basicConfig(
        filename=LOG_FILENAME,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s",
    )


def log_and_print(level: str, message: str) -> None:
    """
    Log a message with the specified level and print it to the console with color.

    Args:
        level: Logging level as a string ('info', 'warning', 'error').
        message: The message to log and print.
    """
    level_lower = level.lower()
    colors = {"info": "\033[94m", "warning": "\033[93m", "error": "\033[91m"}
    color = colors.get(level_lower, "\033[0m")
    log_func = getattr(logging, level_lower, logging.info)
    log_func(message)
    print(f"{color}{message}\033[0m")


def is_valid_email(email: str) -> bool:
    """
    Validate an email address format using email_validator.

    Args:
        email: Email address string to validate.

    Returns:
        True if valid, False otherwise.
    """
    try:
        validate_email(email.strip())
        return True
    except EmailNotValidError:
        return False


def read_file(path: Path) -> str:
    """
    Read the content of a file as a UTF-8 string and strip whitespace.

    Args:
        path: Path to the file.

    Returns:
        The stripped content of the file, or empty string on failure.
    """
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        log_and_print("error", f"Failed to read file {path}: {exc}")
        return ""


def extract_emails(raw: str, delimiters: str = ";") -> List[str]:
    """
    Extract and split emails from a raw string by given delimiters.

    Args:
        raw: Raw string potentially containing emails separated by delimiters.
        delimiters: Delimiters to split the string (default: ';').

    Returns:
        List of trimmed email strings.
    """
    if not raw:
        return []
    return [e.strip() for e in re.split(f"[{re.escape(delimiters)}]", raw) if e.strip()]


def read_recipients(path: Path, delimiters: str = ";") -> List[str]:
    """
    Read and validate email addresses from a text file.

    Args:
        path: Path to the text file containing email addresses.
        delimiters: Delimiters used to separate emails in each line.

    Returns:
        List of valid email addresses.
    """
    if not path.is_file():
        log_and_print("warning", f"{path.name} missing, skipping.")
        return []

    valid_emails = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            for email in extract_emails(line.strip(), delimiters):
                if is_valid_email(email):
                    valid_emails.append(email)
                else:
                    log_and_print("warning", f"Invalid email skipped: {email}")
    return valid_emails


def deduplicate_file(path: Path) -> None:
    """
    Remove duplicate lines from a file, backing up the original first.

    Args:
        path: Path to the file to deduplicate.
    """
    if not path.is_file():
        return

    backup = path.with_name(f"{path.stem}_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}")
    shutil.copy2(path, backup)
    log_and_print("info", f"Backup created: {backup.name}")

    seen = set()
    unique_lines = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            cleaned = line.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                unique_lines.append(cleaned)

    with path.open("w", encoding="utf-8") as file:
        file.writelines(line + "\n" for line in unique_lines)
    log_and_print("info", f"Deduplicated {path.name}")


def check_required_files(base: Path, required: List[str]) -> None:
    """
    Verify presence of required files in a base directory.

    Args:
        base: Base directory path.
        required: List of required filenames.

    Raises:
        MissingRequiredFilesError: If any required files are missing.
    """
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        raise MissingRequiredFilesError(f"Missing required files: {', '.join(missing)}")


def parse_filter_file(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Parse a CSV filter file with optional 'mode' and 'regex_flags' columns.

    Args:
        path: Path to the CSV filter file.

    Returns:
        Tuple containing:
            - List of fieldnames in the CSV.
            - List of filter dictionaries with keys 'field', 'value', 'mode', and 'regex_flags'.
    """
    try:
        with path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            for row in rows:
                row.setdefault("mode", "exact")
                row.setdefault("regex_flags", "")
            return reader.fieldnames or [], rows
    except Exception as exc:
        log_and_print("error", f"Failed to parse filter file: {exc}")
        return [], []


def match_condition(
    actual: str, expected: str, mode: str, regex_flags: str = ""
) -> bool:
    """
    Evaluate if a value matches a filter condition.

    Args:
        actual: Actual string value to test.
        expected: Expected value or pattern.
        mode: Match mode ('exact', 'contains', 'regex').
        regex_flags: Flags for regex compilation separated by '|'.

    Returns:
        True if the condition matches, False otherwise.
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
    Retrieve email IDs from inventory.csv filtered by filter.txt conditions.

    Args:
        base: Base directory containing 'inventory.csv' and 'filter.txt'.
        delimiters: Delimiters to split email IDs in the inventory.

    Returns:
        List of unique filtered email addresses, excluding those in to.txt.
    """
    inv_path = base / "inventory.csv"
    filter_path = base / "filter.txt"
    if not inv_path.is_file() or not filter_path.is_file():
        return []

    _, filters = parse_filter_file(filter_path)
    found = set()

    with inv_path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
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
                for email in extract_emails(row.get("emailids", ""), delimiters):
                    if email.strip():
                        found.add(email.strip())

    existing = set(read_recipients(base / "to.txt", delimiters))
    return [e for e in sorted(found - existing) if is_valid_email(e)]


def sanitize_filename(filename: str) -> str:
    """
    Normalize and sanitize a filename for safe attachment use.

    Args:
        filename: Original filename.

    Returns:
        Sanitized filename containing only ASCII letters, digits, dots, underscores, or hyphens.
        Returns 'attachment' if the result is empty.
    """
    normalized = (
        unicodedata.normalize("NFKD", filename)
        .encode("ASCII", "ignore")
        .decode("ASCII")
    )
    sanitized = re.sub(r"[^\w\.-]", "_", normalized)
    return sanitized or "attachment"


def send_email(
    recipients: List[str],
    subject: str,
    body_html: str,
    attachments: List[Path],
    from_address: str,
    dry_run: bool = False,
) -> None:
    """
    Compose and send an email with optional attachments.

    Args:
        recipients: List of recipient email addresses.
        subject: Email subject line.
        body_html: HTML content of the email body.
        attachments: List of file paths to attach.
        from_address: Sender's email address.
        dry_run: If True, simulate sending without actually sending.
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = ", ".join(recipients)
    msg.add_alternative(body_html, subtype="html")

    max_size = 15 * 1024 * 1024  # 15 MB max attachment size

    for path in attachments:
        if not path.is_file():
            continue
        try:
            if path.stat().st_size > max_size:
                log_and_print("warning", f"Skipping large attachment: {path.name}")
                continue
            with path.open("rb") as file:
                data = file.read()
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
    batch_size: int = 500,
    delay: float = 5.0,
    force: bool = False,
) -> None:
    """
    Send emails based on files in a base folder, supporting dry-run, batching, filtering, and confirmation.

    Args:
        base: Base directory containing email input files.
        attachment_subfolder: Name of subfolder inside base with attachments.
        dry_run: If True, send test email only to approvers without real sending.
        batch_size: Number of emails to send in each batch.
        delay: Delay in seconds between batches.
        force: If True, skip confirmation prompt.
    """
    required_files = ["body.html", "subject.txt", "from.txt", "approver.txt"]
    check_required_files(base, required_files)

    from_address = read_file(base / "from.txt")
    if not from_address or not is_valid_email(from_address):
        raise MissingRequiredFilesError("Invalid or missing From address in from.txt")

    if dry_run:
        approver_emails = read_recipients(base / "approver.txt")
        if not approver_emails:
            log_and_print("warning", "No approvers found for dry-run mode.")
            return

        subject = read_file(base / "subject.txt")
        body_html = read_file(base / "body.html")
        attachments = (
            list((base / attachment_subfolder).glob("*"))
            if (base / attachment_subfolder).is_dir()
            else []
        )

        log_and_print(
            "info",
            f"[DRY RUN] Sending test email to approvers: {', '.join(approver_emails)}",
        )
        send_email(
            approver_emails, subject, body_html, attachments, from_address, dry_run=True
        )
        return

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
            with to_txt_path.open("a", encoding="utf-8") as file:
                for email in filtered_emails:
                    file.write(email + "\n")
            deduplicate_file(to_txt_path)
            log_and_print(
                "info", f"to.txt updated with {len(filtered_emails)} filtered emails."
            )

    emails = sorted(emails)
    if not emails:
        raise Exception("No recipients to send email to.")

    if not force:
        confirm = input(f"Send emails to {len(emails)} users? (yes/no): ").strip().lower()
        if confirm != "yes":
            log_and_print("info", "Operation aborted by user.")
            return

    subject = read_file(base / "subject.txt")
    body_html = read_file(base / "body.html")
    attachments = (
        list((base / attachment_subfolder).glob("*"))
        if (base / attachment_subfolder).is_dir()
        else []
    )

    for i in range(0, len(emails), batch_size):
        batch = emails[i : i + batch_size]
        log_and_print(
            "info", f"Sending batch {i // batch_size + 1} with {len(batch)} recipients..."
        )
        send_email(batch, subject, body_html, attachments, from_address, dry_run=False)
        time.sleep(delay)


def main() -> int:
    """
    Main entry point: parse CLI arguments, setup logging, and trigger email sending.

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
    rotate_log_file()
    setup_logging()

    parser = argparse.ArgumentParser(description="NotifyBot - Email Batch Sender")
    parser.add_argument(
        "--base-folder", type=str, required=True, help="Base directory containing email input files."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate sending emails without SMTP."
    )
    parser.add_argument(
        "--attachment-folder", type=str, default="attachment", help="Folder name for attachments."
    )
    parser.add_argument(
        "--batch-size", type=int, default=500, help="Number of emails to send per batch."
    )
    parser.add_argument(
        "--delay", type=float, default=5.0, help="Delay in seconds between batches."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt (useful for automation).",
    )
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
            force=args.force,
        )
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
