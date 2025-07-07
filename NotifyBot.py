#!/usr/bin/env python3

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
from email.utils import parseaddr
from pathlib import Path
from typing import List, Tuple, Dict

from email_validator import validate_email, EmailNotValidError

LOG_FILENAME = "notifybot.log"


class MissingRequiredFilesError(Exception):
    """Exception raised when required input files are missing."""


def rotate_log_file() -> None:
    """Rotate the current log file by renaming it with a timestamp.

    If the log file exists, rename it to notifybot_YYYYMMDD_HHMMSS.log.
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
    """Configure logging to output messages to a file."""
    logging.basicConfig(
        filename=LOG_FILENAME,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s",
    )


def log_and_print(level: str, message: str) -> None:
    """Log a message at the given level and print it to the console with color.

    Args:
        level: The logging level as a string ('info', 'warning', 'error').
        message: The message to log and print.
    """
    level = level.lower()
    color_codes = {
        "info": "\033[94m",  # Blue
        "warning": "\033[93m",  # Yellow
        "error": "\033[91m",  # Red
    }
    color = color_codes.get(level, "\033[0m")

    if level == "info":
        logging.info(message)
    elif level == "warning":
        logging.warning(message)
    elif level == "error":
        logging.error(message)
    else:
        logging.info(message)

    print(f"{color}{message}\033[0m")


def is_valid_email(email: str) -> bool:
    """Check if the provided email address is valid.

    Args:
        email: The email address to validate.

    Returns:
        True if valid, False otherwise.
    """
    try:
        validate_email(email.strip())
        return True
    except EmailNotValidError:
        return False


def read_file(path: Path) -> str:
    """Read and return the content of a text file.

    Args:
        path: Path to the file.

    Returns:
        The file content as a string, or an empty string if an error occurs.
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as exc:
        log_and_print("error", f"Failed to read file {path}: {exc}")
        return ""


def extract_emails(raw: str, delimiters: str = ";") -> List[str]:
    """Extract a list of email addresses from a delimited string.

    Args:
        raw: Raw string containing emails.
        delimiters: Delimiters separating emails.

    Returns:
        List of extracted email strings.
    """
    if not raw:
        return []
    pattern = f"[{re.escape(delimiters)}]"
    return [e.strip() for e in re.split(pattern, raw) if e.strip()]


def read_recipients(path: Path, delimiters: str = ";") -> List[str]:
    """Read and validate email recipients from a text file.

    Args:
        path: Path to the recipients file.
        delimiters: Delimiters separating emails in each line.

    Returns:
        List of valid email addresses.
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
                        log_and_print(
                            "warning",
                            f"Skipping malformed email (empty addr): {email}",
                        )
                        continue
                    if is_valid_email(addr):
                        valid_emails.append(email)
                    else:
                        log_and_print("warning", f"Invalid email skipped: {email}")
    except Exception as exc:
        log_and_print("error", f"Failed to read emails from {path}: {exc}")
    return valid_emails


def write_to_txt(emails: List[str], path: Path) -> None:
    """Append a list of emails to a text file.

    Args:
        emails: List of email strings to write.
        path: File path to append to.
    """
    try:
        with path.open("a", encoding="utf-8") as f:
            for email in emails:
                f.write(email + "\n")
        log_and_print("info", f"Appended {len(emails)} emails to {path.name}")
    except Exception as exc:
        log_and_print("error", f"Failed to write to {path}: {exc}")


def deduplicate_file(path: Path) -> None:
    """Remove duplicate lines from a file, backing it up first.

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


def check_required_files(base: Path, required: List[str]) -> None:
    """Check for required files in a directory, raise error if missing.

    Args:
        base: Base directory path.
        required: List of required filenames.

    Raises:
        MissingRequiredFilesError: if any required file is missing.
    """
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        msg = f"Missing: {', '.join(missing)}"
        log_and_print("error", msg)
        raise MissingRequiredFilesError(msg)


def parse_filter_file(filter_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """Parse a CSV filter file into headers and list of row dicts.

    Args:
        filter_path: Path to filter.txt CSV file.

    Returns:
        Tuple containing list of headers and list of rows as dictionaries.
    """
    try:
        with filter_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            headers = reader.fieldnames or []

        for row in rows:
            row.setdefault("mode", "exact")
            row.setdefault("regex_flags", "")

        return headers, rows
    except Exception as exc:
        log_and_print("error", f"Failed to parse filter {filter_path}: {exc}")
        return [], []


def match_condition(
    actual: str,
    expected: str,
    mode: str = "exact",
    regex_flags: str = "",
) -> bool:
    """Check if a string matches a condition based on mode and regex flags.

    Args:
        actual: The string to test.
        expected: The expected string or regex pattern.
        mode: Match mode: 'exact', 'contains', or 'regex'.
        regex_flags: Flags for regex (e.g. IGNORECASE|MULTILINE).

    Returns:
        True if condition matches, False otherwise.
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
        for flag_part in regex_flags.upper().split("|"):
            if flag_part == "IGNORECASE":
                flags |= re.IGNORECASE
            elif flag_part == "MULTILINE":
                flags |= re.MULTILINE
            elif flag_part == "DOTALL":
                flags |= re.DOTALL

        try:
            return re.search(expected, actual, flags=flags) is not None
        except re.error as e:
            log_and_print("warning", f"Invalid regex '{expected}': {e}")
            return False

    log_and_print("warning", f"Unknown match mode '{mode}', defaulting to exact.")
    return actual.lower() == expected.lower()


def get_filtered_emailids(base: Path, delimiters: str = ";") -> List[str]:
    """Filter email IDs from inventory.csv based on filter.txt conditions.

    Args:
        base: Base directory containing 'inventory.csv' and 'filter.txt'.
        delimiters: Delimiters used for email separation.

    Returns:
        List of filtered and validated email addresses.
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
    """Sanitize a filename by removing/ replacing unsafe characters.

    Args:
        filename: Original filename.

    Returns:
        Sanitized filename safe for file systems.
    """
    nfkd_form = unicodedata.normalize("NFKD", filename)
    ascii_bytes = nfkd_form.encode("ASCII", "ignore")
    ascii_str = ascii_bytes.decode("ASCII")

    sanitized = re.sub(r"[^\w\.-]", "_", ascii_str)

    return sanitized or "attachment"


def send_email(
    recipients: List[str],
    subject: str,
    body_html: str,
    attachments: List[Path],
    smtp_server: str = "localhost",
    dry_run: bool = False,
) -> None:
    """Send an email with optional attachments to recipients.

    Args:
        recipients: List of recipient email addresses.
        subject: Email subject.
        body_html: HTML content of the email body.
        attachments: List of file paths to attach.
        smtp_server: SMTP server address.
        dry_run: If True, do not actually send email, just simulate.
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "notifybot@example.com"
    msg["To"] = ", ".join(recipients)

    msg.add_alternative(body_html, subtype="html")

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

            msg.add_attachment(
                data, maintype=maintype, subtype=subtype, filename=sanitized_name
            )
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
    base: Path,
    attachment_subfolder: str = "attachment",
    dry_run: bool = False,
    batch_size: int = 30,
) -> None:
    """Send emails using data and files from a specified folder.

    Args:
        base: Base directory path containing required files.
        attachment_subfolder: Name of subfolder for attachments inside base.
        dry_run: If True, simulate sending without actual email sending.
        batch_size: Number of recipients per email batch.
    """
    required = ["body.html", "subject.txt"]
    check_required_files(base, required)

    to_txt = base / "to.txt"
    filter_txt = base / "filter.txt"

    emails = read_recipients(to_txt)
    if filter_txt.is_file():
        emails += get_filtered_emailids(base)

    if not emails:
        log_and_print("error", "No valid recipients found.")
        return

    deduplicate_file(to_txt)

    subject = read_file(base / "subject.txt")
    body_html = read_file(base / "body.html")

    # Attachments in base folder except known files
    attachments = [
        p
        for p in base.iterdir()
        if p.is_file() and p.name not in required + ["to.txt", "filter.txt"]
    ]

    # Add attachments from the specified attachment folder inside base
    attachment_folder = base / attachment_subfolder
    if attachment_folder.is_dir():
        attachments.extend(p for p in attachment_folder.iterdir() if p.is_file())

    # Batch recipients and send emails
    for i in range(0, len(emails), batch_size):
        batch = emails[i : i + batch_size]
        log_and_print(
            "info", f"Sending batch {i // batch_size + 1} with {len(batch)} recipients..."
        )
        send_email(
            recipients=batch,
            subject=subject,
            body_html=body_html,
            attachments=attachments,
            dry_run=dry_run,
        )
        time.sleep(1)


def main() -> None:
    """Main entry point for the notifybot script."""
    rotate_log_file()
    setup_logging()

    parser = argparse.ArgumentParser(description="Notifybot email sender")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate sending emails without actually sending",
    )
    parser.add_argument(
        "--attachment-folder",
        type=str,
        default="attachment",
        help="Subfolder name inside base folder to load attachments from (default: 'attachment')",
    )
    args = parser.parse_args()

    base_folder = Path(__file__).parent / "base"

    try:
        send_email_from_folder(
            base_folder,
            attachment_subfolder=args.attachment_folder,
            dry_run=args.dry_run,
        )
    except MissingRequiredFilesError as exc:
        log_and_print("error", str(exc))


if __name__ == "__main__":
    main()
