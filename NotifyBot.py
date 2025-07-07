#!/usr/bin/env python3

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
    pass


def rotate_log_file() -> None:
    """
    Rotate the current log file by renaming it with a timestamp suffix.

    If the log file exists, rename it to 'notifybot_YYYYMMDD_HHMMSS.log'.
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
    Configure logging to output INFO level messages with timestamp, function name, and line info.
    """
    logging.basicConfig(
        filename=LOG_FILENAME,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s",
    )


def log_and_print(level: str, message: str) -> None:
    """
    Log a message and print it with colored terminal output.

    Args:
        level: Logging level as string ('info', 'warning', 'error').
        message: The message to log and print.
    """
    level = level.lower()
    color_codes = {
        "info": "\033[94m",    # Blue
        "warning": "\033[93m", # Yellow
        "error": "\033[91m",   # Red
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
    Read and return the content of a file, stripping whitespace.

    Args:
        path: Path object to the file.

    Returns:
        File content as a stripped string, or empty string on error.
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
    Read recipient emails from a file, validate them, and return a list of valid emails.

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
    """
    Append a list of emails to a text file.

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


def deduplicate_file(path: Path) -> None:
    """
    Remove duplicate lines from a file, creating a timestamped backup first.

    Args:
        path: Path to the file to deduplicate.
    """
    if not path.is_file():
        return

    backup = path.with_name(
        f"{path.stem}_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}"
    )
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
    Parse the filter.txt CSV file to extract headers and rows with defaults.

    Args:
        filter_path: Path to filter.txt.

    Returns:
        Tuple containing list of headers and list of row dictionaries.
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
    """
    Retrieve filtered email IDs based on inventory.csv and filter.txt files.

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
    """
    Send an email with HTML body only (no plain text fallback).

    Args:
        recipients: List of recipient email addresses.
        subject: Email subject line.
        body_html: HTML body content.
        attachments: List of file Paths to attach.
        smtp_server: SMTP server address.
        dry_run: If True, do not actually send emails.
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "notifybot@example.com"
    msg["To"] = ", ".join(recipients)

    # Only HTML version
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
    dry_run: bool = False,
    batch_size: int = 30,
) -> None:
    """
    Compose and send emails from files in the base folder.

    Args:
        base: Path to base folder with input files.
        dry_run: If True, only simulate sending.
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

    # Collect attachments in base folder excluding the body and subject files and known text files
    attachments = [
        p
        for p in base.iterdir()
        if p.is_file() and p.name not in required + ["to.txt", "filter.txt"]
    ]

    # Batch recipients and send emails
    for i in range(0, len(emails), batch_size):
        batch = emails[i : i + batch_size]
        log_and_print("info", f"Sending batch {i // batch_size + 1} with {len(batch)} recipients...")
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

    base_folder = Path(__file__).parent / "base"

    # Command line options: add "--dry-run" to test without sending emails
    dry_run = "--dry-run" in sys.argv

    try:
        send_email_from_folder(base_folder, dry_run=dry_run)
    except MissingRequiredFilesError as exc:
        log_and_print("error", str(exc))


if __name__ == "__main__":
    main()
