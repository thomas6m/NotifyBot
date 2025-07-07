#!/usr/bin/env python3
"""
NotifyBot Email Sender Script

Updated:
- filter.txt supports field,value,mode (exact/contains/regex)
- match_condition() enables flexible matching
- Added log rotation: rename notifybot.log with timestamp suffix on each run
- prepare_to_txt updated to skip inventory filter if to.txt exists
"""

import csv
import logging
import mimetypes
import shutil
import smtplib
import sys
import time
import re
from datetime import datetime
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from email_validator import validate_email, EmailNotValidError

LOG_FILENAME = "notifybot.log"

class MissingRequiredFilesError(Exception):
    pass

def rotate_log_file():
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
    logging.basicConfig(
        filename=LOG_FILENAME,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s",
    )

def is_valid_email(email: str) -> bool:
    try:
        validate_email(email.strip())
        return True
    except EmailNotValidError:
        return False

def read_file(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as exc:
        logging.error(f"Failed to read file {path}: {exc}")
        return ""

def read_recipients(path: Path) -> List[str]:
    if not path.is_file():
        logging.warning(f"{path.name} missing, skipping.")
        return []

    valid_emails: List[str] = []

    try:
        with path.open("r", encoding="utf-8") as f:
            for raw in f:
                email = raw.strip()
                if not email:
                    continue
                _, addr = parseaddr(email)
                if is_valid_email(addr):
                    valid_emails.append(email)
                else:
                    warning = f"Invalid email skipped: {email}"
                    logging.warning(warning)
                    print(f"\033[93m{warning}\033[0m")
    except Exception as exc:
        logging.error(f"Failed to read emails from {path}: {exc}")

    return valid_emails

def write_to_txt(emails: List[str], path: Path) -> None:
    try:
        with path.open("a", encoding="utf-8") as f:
            for email in emails:
                f.write(email + "\n")
        logging.info(f"Appended {len(emails)} emails to {path.name}")
    except Exception as exc:
        logging.error(f"Failed to write to {path}: {exc}")

def deduplicate_file(path: Path) -> None:
    if not path.is_file():
        return

    backup = path.with_name(
        f"{path.stem}_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}"
    )
    shutil.copy2(path, backup)
    logging.info(f"Backup created: {backup.name}")

    seen: set = set()
    uniq: List[str] = []

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
        logging.info(f"Deduplicated {path.name}")
    except Exception as exc:
        logging.error(f"Error deduplicating {path}: {exc}")

def check_required_files(base: Path, required: List[str]) -> None:
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        msg = f"Missing: {', '.join(missing)}"
        logging.error(msg)
        raise MissingRequiredFilesError(msg)

def parse_filter_file(filter_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    try:
        with filter_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            headers = reader.fieldnames or []

        for row in rows:
            row.setdefault("mode", "exact")

        return headers, rows
    except Exception as exc:
        logging.error(f"Failed to parse filter {filter_path}: {exc}")
        return [], []

def match_condition(actual: str, expected: str, mode: str = "exact") -> bool:
    actual = actual.strip()
    expected = expected.strip()
    mode = mode.strip().lower()

    if mode == "exact":
        return actual.lower() == expected.lower()
    elif mode == "contains":
        return expected.lower() in actual.lower()
    elif mode == "regex":
        try:
            return re.search(expected, actual) is not None
        except re.error as e:
            logging.warning(f"Invalid regex '{expected}': {e}")
            return False
    else:
        logging.warning(f"Unknown match mode '{mode}', defaulting to exact.")
        return actual.lower() == expected.lower()

def get_filtered_emailids(base: Path) -> List[str]:
    inv = base / "inventory.csv"
    flt = base / "filter.txt"

    if not inv.is_file() or not flt.is_file():
        logging.warning("inventory.csv or filter.txt missing.")
        return []

    _, conds = parse_filter_file(flt)
    found: set = set()

    try:
        with inv.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                match = all(
                    match_condition(
                        actual=row.get(cond.get("field", ""), ""),
                        expected=cond.get("value", ""),
                        mode=cond.get("mode", "exact")
                    )
                    for cond in conds
                )
                if match:
                    emails = row.get("emailids", "")
                    for e in re.split(r"[;,]", emails):
                        if e.strip():
                            found.add(e.strip())
    except Exception as exc:
        logging.error(f"Error reading {inv}: {exc}")

    existing = set(read_recipients(base / "to.txt"))
    valid: List[str] = []

    for raw in sorted(found - existing):
        _, addr = parseaddr(raw)
        if is_valid_email(addr):
            valid.append(raw)
        else:
            warning = f"Invalid filtered email: {raw}"
            logging.warning(warning)
            print(f"\033[93m{warning}\033[0m")

    return valid

def send_email(
    from_email: str,
    subject: str,
    body_html: str,
    recipients: List[str],
    cc: List[str],
    bcc: List[str],
    attachments: Optional[List[Path]] = None,
    max_attachment_size_mb: int = 10,
    log_sent: bool = False,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(recipients)

    if cc:
        msg["Cc"] = ", ".join(cc)

    msg.set_content("This is a plain-text fallback version.")
    msg.add_alternative(body_html, subtype="html")

    for path in attachments or []:
        size_mb = path.stat().st_size / (1024**2)
        if size_mb > max_attachment_size_mb:
            logging.warning(f"Skipping {path.name}: {size_mb:.1f}MB > limit")
            continue

        ctype, encoding = mimetypes.guess_type(path.name)
        ctype = ctype or "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)

        try:
            with path.open("rb") as fp:
                msg.add_attachment(
                    fp.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=path.name
                )
            logging.info(f"Attached: {path.name}")
        except Exception as exc:
            logging.error(f"Error attaching {path.name}: {exc}")
            print(f"\033[91mAttachment failed: {path.name}\033[0m")
            return

    all_recipients = list(dict.fromkeys(recipients + cc + bcc))

    try:
        with smtplib.SMTP("localhost") as server:
            server.send_message(msg, from_addr=from_email, to_addrs=all_recipients)
        print(f"Sent to {len(recipients)} recipients.")
        if log_sent:
            logging.info(f"Sent to: {', '.join(recipients)}")
    except Exception as exc:
        error = f"Failed to send to {recipients}: {exc}"
        logging.error(error)
        print(f"\033[91m{error}\033[0m")

def prepare_to_txt(base: Path) -> None:
    to_path = base / "to.txt"

    # If to.txt exists, skip filtering from inventory.csv + filter.txt
    if not to_path.is_file():
        new_ids = get_filtered_emailids(base)
        if new_ids:
            write_to_txt(new_ids, to_path)
            print(f"Added {len(new_ids)} filtered addresses.")

    # Always add additional_to.txt content
    addl = read_recipients(base / "additional_to.txt")
    if addl:
        write_to_txt(addl, to_path)
        print(f"Added {len(addl)} additional addresses.")

    deduplicate_file(to_path)

def send_email_from_folder(
    base_folder: str,
    dry_run: bool = False,
    batch_size: int = 500,
    delay: int = 5,
    attachments_folder: Optional[str] = None,
    max_attachment_size_mb: int = 10,
) -> None:
    base = Path(base_folder)

    # Rotate log file before configuring logging
    rotate_log_file()

    # Setup fresh logging after rotation
    setup_logging()

    attach_path = Path(attachments_folder) if attachments_folder else base / "attachments"
    logging.info(f"Start sending from {base_folder}")
    start = datetime.now()

    required = ["from.txt", "subject.txt", "body.html", "approver.txt"]
    try:
        check_required_files(base, required)
    except MissingRequiredFilesError as exc:
        print(f"\033[91m{exc}\033[0m")
        sys.exit(1)

    from_email = read_file(base / "from.txt")
    subject = read_file(base / "subject.txt")
    body_html = read_file(base / "body.html")
    approvers = read_recipients(base / "approver.txt")

    if not all([from_email, subject, body_html]):
        logging.error("Missing subject/body/from.")
        print("\033[91mMissing core files. Exiting.\033[0m")
        sys.exit(1)

    if not approvers:
        logging.warning("No approvers listed.")
        print("\033[93mNo approvers defined.\033[0m")
        return

    prepare_to_txt(base)

    if dry_run:
        print("DRY-RUN: sending draft to approvers only.")
        send_email(
            from_email,
            "[DRAFT] " + subject,
            body_html,
            approvers,
            [],
            [],
            attachments=[],
            log_sent=False,
            max_attachment_size_mb=max_attachment_size_mb,
        )
        logging.info("Dry-run complete.")
        return

    to_list = read_recipients(base / "to.txt")
    cc_list = read_recipients(base / "cc.txt")
    bcc_list = read_recipients(base / "bcc.txt")

    attachments = []
    if attach_path.is_dir():
        attachments = [p for p in attach_path.iterdir() if p.is_file()]
        print(f"Found {len(attachments)} attachments.")

    if not to_list:
        logging.info("to.txt empty.")
        print("\033[91mNo recipients.\033[0m")
        return

    deduplicate_file(base / "to.txt")
    to_list = read_recipients(base / "to.txt")

    sent, errors = 0, 0
    for i in range(0, len(to_list), batch_size):
        batch = to_list[i:i + batch_size]
        try:
            send_email(
                from_email,
                subject,
                body_html,
                batch,
                cc_list,
                bcc_list,
                attachments=attachments,
                max_attachment_size_mb=max_attachment_size_mb,
                log_sent=True,
            )
            sent += len(batch)
        except Exception as exc:
            errors += 1
            logging.error(f"Batch error {i}: {exc}")

        if i + batch_size < len(to_list):
            print(f"Waiting {delay} seconds...")
            time.sleep(delay)

    duration = (datetime.now() - start).total_seconds()
    summary = f"Summary — Sent: {sent}, Errors: {errors}, Time: {duration:.2f}s"
    print(summary)
    logging.info(summary)

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="NotifyBot Email Sender CLI")
    parser.add_argument("base_folder", help="Directory with email source files")
    parser.add_argument("--dry-run", action="store_true", help="Send to approvers only")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of recipients per batch")
    parser.add_argument("--delay", type=int, default=5, help="Seconds delay between batches")
    parser.add_argument("--attachments-folder", type=str, help="Alternate folder for attachments")
    parser.add_argument("--max-attachment-size", type=int, default=10, help="Max MB per attachment")

    args = parser.parse_args()

    send_email_from_folder(
        base_folder=args.base_folder,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        delay=args.delay,
        attachments_folder=args.attachments_folder,
        max_attachment_size_mb=args.max_attachment_size,
    )

if __name__ == "__main__":
    main()
