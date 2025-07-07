#!/usr/bin/env python3

import csv
import logging
import mimetypes
import shutil
import smtplib
import sys
import time
import re
import unicodedata
from datetime import datetime
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from email_validator import validate_email, EmailNotValidError
import string

LOG_FILENAME = "notifybot.log"


class MissingRequiredFilesError(Exception):
    """Exception raised when required input files are missing."""
    pass


def rotate_log_file():
    """
    Rotate the current log file by renaming it with a timestamp suffix.
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


def setup_logging():
    """
    Setup logging configuration to log INFO level messages with timestamps and line info.
    """
    logging.basicConfig(
        filename=LOG_FILENAME,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s",
    )


def log_and_print(level: str, message: str):
    """
    Helper to log a message and print it with colored terminal output.

    Args:
        level: Logging level as string ('info', 'warning', 'error')
        message: The message to log and print
    """
    level = level.lower()
    color_codes = {
        'info': "\033[94m",    # Blue
        'warning': "\033[93m", # Yellow
        'error': "\033[91m",   # Red
    }
    color = color_codes.get(level, "\033[0m")

    # Log
    if level == 'info':
        logging.info(message)
    elif level == 'warning':
        logging.warning(message)
    elif level == 'error':
        logging.error(message)
    else:
        logging.info(message)

    # Print colored
    print(f"{color}{message}\033[0m")


def is_valid_email(email: str) -> bool:
    """
    Validate the given email address using email_validator package.

    Args:
        email: The email address string to validate.

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
    Read the content of a file and return it as a stripped string.

    Args:
        path: Path object to the file.

    Returns:
        File content as a string, or empty string on error.
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as exc:
        log_and_print("error", f"Failed to read file {path}: {exc}")
        return ""


def extract_emails(raw: str, delimiters: str = ";") -> List[str]:
    """
    Split a string by multiple delimiters and return a list of non-empty trimmed strings.

    Args:
        raw: Raw string containing emails separated by delimiters.
        delimiters: String of delimiter characters (e.g. ";,").

    Returns:
        List of email strings.
    """
    if not raw:
        return []
    pattern = f"[{re.escape(delimiters)}]"
    return [e.strip() for e in re.split(pattern, raw) if e.strip()]


def read_recipients(path: Path, delimiters: str = ";") -> List[str]:
    """
    Read recipient emails from a file, validate them, and return a list.

    Args:
        path: Path to the recipient file.
        delimiters: Delimiters used to separate emails.

    Returns:
        List of valid email strings.
    """
    if not path.is_file():
        log_and_print("warning", f"{path.name} missing, skipping.")
        return []

    valid_emails = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                for email in extract_emails(line.strip(), delimiters):
                    _, addr = parseaddr(email)
                    if not addr:
                        log_and_print("warning", f"Skipping malformed email (empty addr): {email}")
                        continue
                    if is_valid_email(addr):
                        valid_emails.append(email)
                    else:
                        log_and_print("warning", f"Invalid email skipped: {email}")
    except Exception as exc:
        log_and_print("error", f"Failed to read emails from {path}: {exc}")
    return valid_emails


def write_to_txt(emails: List[str], path: Path):
    """
    Append a list of emails to a file.

    Args:
        emails: List of email strings.
        path: Path to the file to append to.
    """
    try:
        with path.open("a", encoding="utf-8") as f:
            for email in emails:
                f.write(email + "\n")
        log_and_print("info", f"Appended {len(emails)} emails to {path.name}")
    except Exception as exc:
        log_and_print("error", f"Failed to write to {path}: {exc}")


def deduplicate_file(path: Path):
    """
    Remove duplicate lines from a file, creating a timestamped backup first.

    Args:
        path: Path to the file to deduplicate.
    """
    if not path.is_file():
        return

    backup = path.with_name(f"{path.stem}_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}")
    shutil.copy2(path, backup)
    log_and_print("info", f"Backup created: {backup.name}")

    seen = set()
    uniq = []

    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                cleaned = line.strip()
                if cleaned and cleaned not in seen:
                    seen.add(cleaned)
                    uniq.append(cleaned)

        with path.open("w", encoding="utf-8") as f:
            for line in uniq:
                f.write(line + "\n")
        log_and_print("info", f"Deduplicated {path.name}")
    except Exception as exc:
        log_and_print("error", f"Error deduplicating {path}: {exc}")


def check_required_files(base: Path, required: List[str]):
    """
    Verify that all required files exist in the base folder.

    Args:
        base: Path to base folder.
        required: List of required filenames.

    Raises:
        MissingRequiredFilesError: If any required files are missing.
    """
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        msg = f"Missing: {', '.join(missing)}"
        log_and_print("error", msg)
        raise MissingRequiredFilesError(msg)


def parse_filter_file(filter_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Parse the filter.txt CSV file.

    Args:
        filter_path: Path to filter.txt.

    Returns:
        Tuple of (headers list, list of rows as dictionaries).
    """
    try:
        with filter_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            headers = reader.fieldnames or []

        for row in rows:
            # Default mode to exact if not present
            row.setdefault("mode", "exact")
            # Default regex_flags for regex mode, empty or 'IGNORECASE'
            row.setdefault("regex_flags", "")

        return headers, rows
    except Exception as exc:
        log_and_print("error", f"Failed to parse filter {filter_path}: {exc}")
        return [], []


def match_condition(actual: str, expected: str, mode: str = "exact", regex_flags: str = "") -> bool:
    """
    Compare actual and expected strings based on matching mode.

    Args:
        actual: The actual string value.
        expected: The expected string value.
        mode: Matching mode ("exact", "contains", "regex").
        regex_flags: Flags for regex, e.g. "IGNORECASE", "MULTILINE".

    Returns:
        True if matched, False otherwise.
    """
    actual = actual.strip()
    expected = expected.strip()
    mode = mode.strip().lower()

    if mode == "exact":
        return actual.lower() == expected.lower()
    if mode == "contains":
        return expected.lower() in actual.lower()
    if mode == "regex":
        flags = 0
        # Support multiple flags separated by |
        for flag_part in regex_flags.upper().split("|"):
            if flag_part == "IGNORECASE":
                flags |= re.IGNORECASE
            elif flag_part == "MULTILINE":
                flags |= re.MULTILINE
            elif flag_part == "DOTALL":
                flags |= re.DOTALL
            # Add more flags here if needed

        try:
            return re.search(expected, actual, flags=flags) is not None
        except re.error as e:
            log_and_print("warning", f"Invalid regex '{expected}': {e}")
            return False

    log_and_print("warning", f"Unknown match mode '{mode}', defaulting to exact.")
    return actual.lower() == expected.lower()


def get_filtered_emailids(base: Path, delimiters: str = ";") -> List[str]:
    """
    Retrieve filtered email IDs based on inventory.csv and filter.txt.

    Args:
        base: Path to base folder.
        delimiters: Delimiters used in email fields.

    Returns:
        List of filtered valid email addresses.
    """
    inv = base / "inventory.csv"
    flt = base / "filter.txt"

    if not inv.is_file() or not flt.is_file():
        log_and_print("warning", "inventory.csv or filter.txt missing.")
        return []

    _, conds = parse_filter_file(flt)
    found = set()

    try:
        with inv.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                match = all(
                    match_condition(
                        actual=row.get(cond.get("field", ""), ""),
                        expected=cond.get("value", ""),
                        mode=cond.get("mode", "exact"),
                        regex_flags=cond.get("regex_flags", ""),
                    )
                    for cond in conds
                )
                if match:
                    emails = row.get("emailids", "")
                    for e in extract_emails(emails, delimiters):
                        if e.strip():
                            found.add(e.strip())
    except Exception as exc:
        log_and_print("error", f"Error reading {inv}: {exc}")

    existing = set(read_recipients(base / "to.txt", delimiters))
    valid = []

    for raw in sorted(found - existing):
        _, addr = parseaddr(raw)
        if addr and is_valid_email(addr):
            valid.append(raw)
        else:
            log_and_print("warning", f"Filtered invalid email skipped: {raw}")

    return valid


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to ASCII only, replacing non-ASCII and unsafe chars with '_'.

    Args:
        filename: The original filename.

    Returns:
        Sanitized ASCII-only filename.
    """
    # Normalize to NFKD form and encode ASCII ignoring errors
    nfkd_form = unicodedata.normalize('NFKD', filename)
    ascii_bytes = nfkd_form.encode('ASCII', 'ignore')
    ascii_str = ascii_bytes.decode('ASCII')

    # Replace any remaining unsafe characters with underscore
    sanitized = re.sub(r'[^\w\.-]', '_', ascii_str)

    # Ensure it’s not empty after sanitization
    return sanitized or "attachment"


def send_email(
    recipients: List[str],
    subject: str,
    body: str,
    attachments: List[Path],
    smtp_server: str = "localhost",
    dry_run: bool = False,
):
    """
    Send an email with optional attachments.

    Args:
        recipients: List of recipient email addresses.
        subject: Email subject line.
        body: Email body content.
        attachments: List of file Paths to attach.
        smtp_server: SMTP server address.
        dry_run: If True, don't actually send emails.
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "notifybot@example.com"
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    max_attachment_size = 15 * 1024 * 1024  # 15 MB

    for path in attachments:
        if not path.is_file():
            log_and_print("warning", f"Attachment missing, skipping: {path.name}")
            continue

        try:
            filesize = path.stat().st_size
            if filesize > max_attachment_size:
                log_and_print(
                    "warning",
                    f"Skipping large attachment >15MB: {path.name} ({filesize} bytes)",
                )
                continue

            with path.open("rb") as f:
                data = f.read()

            ctype, encoding = mimetypes.guess_type(path.name)
            if ctype is None or encoding is not None:
                ctype = "application/octet-stream"

            maintype, subtype = ctype.split("/", 1)
            sanitized_name = sanitize_filename(path.name)

            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=sanitized_name)
            log_and_print("info", f"Attached: {sanitized_name}")
        except Exception as exc:
            log_and_print("error", f"Error attaching {path.name}: {exc}")

    if dry_run:
        log_and_print("info", f"[DRY RUN] Would send email to {msg['To']}")
        return

    try:
        with smtplib.SMTP(smtp_server) as server:
            server.send_message(msg)
            log_and_print("info", f"Email sent to {msg['To']}")
    except Exception as exc:
        log_and_print("error", f"Failed to send email: {exc}")


def send_email_from_folder(
    base_folder: str,
    dry_run: bool = False,
    batch_size: int = 10,
    retries: int = 3,
    delay: int = 3,
):
    """
    Main routine to read inputs from base folder and send emails in batches.

    Args:
        base_folder: Folder containing input files.
        dry_run: If True, don't actually send emails.
        batch_size: Number of recipients per email batch.
        retries: Number of retries on failure.
        delay: Delay in seconds between retries.
    """
    base = Path(base_folder)

    # Rotate logs before setting up logging
    rotate_log_file()
    setup_logging()

    try:
        check_required_files(base, ["body.txt", "subject.txt"])
    except MissingRequiredFilesError as e:
        print(f"\033[91m{e}\033[0m")
        sys.exit(1)

    subject = read_file(base / "subject.txt")
    body_template_raw = read_file(base / "body.txt")

    to_emails = read_recipients(base / "to.txt")
    if not to_emails:
        log_and_print("warning", "No valid recipients found in to.txt")

    filtered_emails = get_filtered_emailids(base)
    if filtered_emails:
        write_to_txt(filtered_emails, base / "to.txt")
        deduplicate_file(base / "to.txt")
        to_emails.extend(filtered_emails)
        to_emails = list(dict.fromkeys(to_emails))  # Deduplicate in memory

    attachments = []
    for path in base.glob("attachments/*"):
        if path.is_file():
            attachments.append(path)

    total = len(to_emails)
    if total == 0:
        log_and_print("warning", "No recipients to send emails to.")
        return

    # Batch sending
    for i in range(0, total, batch_size):
        batch = to_emails[i : i + batch_size]
        log_and_print("info", f"Sending batch {i // batch_size + 1} to {len(batch)} recipients.")

        # Personalization: substitute ${email} with all batch emails joined
        try:
            body_template = string.Template(body_template_raw)
            body = body_template.safe_substitute(email=", ".join(batch))
        except Exception as exc:
            log_and_print("error", f"Failed to substitute template: {exc}")
            body = body_template_raw

        attempts = 0
        while attempts < retries:
            try:
                send_email(batch, subject, body, attachments, dry_run=dry_run)
                break
            except Exception as exc:
                attempts += 1
                log_and_print("error", f"Send attempt {attempts} failed: {exc}")
                if attempts == retries:
                    log_and_print("error", "Max retries reached, aborting batch.")
                    raise
                time.sleep(delay)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Bulk Email Sender")
    parser.add_argument("folder", help="Folder containing email inputs")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode, do not send emails")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of emails per batch")
    parser.add_argument("--retries", type=int, default=3, help="Retry count for sending emails")
    parser.add_argument("--delay", type=int, default=3, help="Delay between retries in seconds")

    args = parser.parse_args()

    try:
        send_email_from_folder(
            base_folder=args.folder,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            retries=args.retries,
            delay=args.delay,
        )
    except Exception as exc:
        log_and_print("error", f"Fatal error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
