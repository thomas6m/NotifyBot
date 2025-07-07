# NotifyBot Email Sender - Detailed Code Analysis

## File Header and Imports

```python
#!/usr/bin/env python3
"""
NotifyBot Email Sender Script
...
"""
```

**Purpose**: Shebang line makes the script executable on Unix systems, followed by a comprehensive docstring explaining recent updates.

### Import Analysis

```python
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
```

**Key Dependencies**:
- `csv`: Reading inventory and filter files
- `logging`: Comprehensive logging system
- `mimetypes`: Auto-detecting attachment file types
- `smtplib`: SMTP email sending
- `email.message.EmailMessage`: Modern email composition
- `pathlib.Path`: Modern file path handling
- `email_validator`: Third-party email validation (more robust than regex)

## Configuration and Custom Exceptions

```python
LOG_FILENAME = "notifybot.log"

class MissingRequiredFilesError(Exception):
    pass
```

**Design Pattern**: Custom exception for specific error handling, making error types more explicit.

## Log Management Functions

### Log Rotation Function

```python
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
```

**Key Features**:
- **Timestamp Format**: `YYYYMMDD_HHMMSS` ensures chronological sorting
- **Error Handling**: Gracefully handles rotation failures
- **ANSI Colors**: `\033[91m` = red text for errors, `\033[0m` = reset color
- **Path Operations**: Uses `pathlib` for modern file handling

### Logging Setup

```python
def setup_logging():
    logging.basicConfig(
        filename=LOG_FILENAME,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s",
    )
```

**Format Breakdown**:
- `%(asctime)s`: Timestamp of log entry
- `%(levelname)s`: Log level (INFO, WARNING, ERROR)
- `%(funcName)s`: Function name where log was called
- `[line %(lineno)d]`: Line number for debugging
- `%(message)s`: The actual log message

## Email Validation Functions

### Email Validation

```python
def is_valid_email(email: str) -> bool:
    try:
        validate_email(email.strip())
        return True
    except EmailNotValidError:
        return False
```

**Why This Approach**:
- Uses `email_validator` library instead of regex
- More robust than simple regex patterns
- Handles edge cases and international domains
- Strips whitespace automatically

### File Reading with Error Handling

```python
def read_file(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as exc:
        logging.error(f"Failed to read file {path}: {exc}")
        return ""
```

**Design Pattern**: Fail-safe function that returns empty string on error rather than crashing.

### Email List Processing

```python
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
```

**Key Features**:
- **parseaddr()**: Handles "Name <email@domain.com>" format
- **Validation**: Each email is validated before adding to list
- **User Feedback**: Yellow text (`\033[93m`) for warnings
- **Graceful Degradation**: Continues processing even with invalid emails

## File Writing and Deduplication

### Appending Emails

```python
def write_to_txt(emails: List[str], path: Path) -> None:
    try:
        with path.open("a", encoding="utf-8") as f:
            for email in emails:
                f.write(email + "\n")
        logging.info(f"Appended {len(emails)} emails to {path.name}")
    except Exception as exc:
        logging.error(f"Failed to write to {path}: {exc}")
```

**Design Choice**: Uses append mode (`"a"`) to add new emails without overwriting existing ones.

### Deduplication with Backup

```python
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
```

**Algorithm**:
1. **Backup First**: Creates timestamped backup before modifying
2. **Set for Tracking**: Uses set for O(1) duplicate detection
3. **List for Order**: Maintains original order of first occurrence
4. **Atomic Write**: Overwrites file only after successful processing

## Configuration and Filtering

### Filter File Parsing

```python
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
```

**CSV Processing**:
- **DictReader**: Converts CSV rows to dictionaries
- **Default Mode**: Sets "exact" as default matching mode
- **Error Handling**: Returns empty lists on failure

### Flexible Matching Function

```python
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
```

**Matching Modes**:
- **Exact**: Case-insensitive equality
- **Contains**: Substring matching
- **Regex**: Pattern matching with error handling
- **Fallback**: Defaults to exact matching for unknown modes

## Inventory Processing

### Email Filtering from Inventory

```python
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
```

**Advanced Logic**:
- **all()**: Requires ALL filter conditions to match
- **Set Operations**: `found - existing` removes duplicates efficiently
- **Email Parsing**: Splits multiple emails by semicolon or comma
- **Validation**: Final validation before returning results

## Email Sending Function

### Main Email Sending Logic

```python
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
```

**Function Parameters**:
- **Type Hints**: Uses modern Python typing for clarity
- **Optional Parameters**: Default values for flexibility
- **Size Limits**: Configurable attachment size limits

### Email Composition

```python
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(recipients)

    if cc:
        msg["Cc"] = ", ".join(cc)

    msg.set_content("This is a plain-text fallback version.")
    msg.add_alternative(body_html, subtype="html")
```

**Multi-part Email**:
- **Plain Text**: Fallback for clients that don't support HTML
- **HTML Alternative**: Rich formatting for modern clients
- **Header Management**: Proper email headers for delivery

### Attachment Processing

```python
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
```

**Attachment Features**:
- **Size Validation**: Prevents oversized attachments
- **MIME Detection**: Automatic content type detection
- **Fallback Type**: Uses generic binary type if detection fails
- **Error Handling**: Fails gracefully on attachment errors

### SMTP Delivery

```python
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
```

**SMTP Logic**:
- **Deduplication**: `dict.fromkeys()` removes duplicate recipients
- **Context Manager**: `with` statement ensures connection cleanup
- **All Recipients**: Includes To, Cc, and Bcc in SMTP envelope
- **Conditional Logging**: Only logs recipients if requested

## Workflow Management

### Recipient Preparation

```python
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
```

**Smart Logic**:
- **Conditional Filtering**: Only processes inventory if to.txt doesn't exist
- **Always Add Additional**: Respects additional_to.txt regardless
- **Final Deduplication**: Ensures no duplicates in final list

## Main Execution Function

### Core Processing Logic

```python
def send_email_from_folder(
    base_folder: str,
    dry_run: bool = False,
    batch_size: int = 500,
    delay: int = 5,
    attachments_folder: Optional[str] = None,
    max_attachment_size_mb: int = 10,
) -> None:
```

**Default Values**:
- **Batch Size**: 500 recipients per batch (reasonable for most SMTP servers)
- **Delay**: 5 seconds between batches (prevents server overload)
- **Max Attachment**: 10MB limit (email server friendly)

### Initialization Sequence

```python
    base = Path(base_folder)

    # Rotate log file before configuring logging
    rotate_log_file()

    # Setup fresh logging after rotation
    setup_logging()

    attach_path = Path(attachments_folder) if attachments_folder else base / "attachments"
    logging.info(f"Start sending from {base_folder}")
    start = datetime.now()
```

**Execution Order**:
1. **Log Rotation**: Preserves previous logs
2. **Fresh Logging**: Creates new log configuration
3. **Path Setup**: Determines attachment folder
4. **Timing**: Records start time for performance metrics

### File Validation

```python
    required = ["from.txt", "subject.txt", "body.html", "approver.txt"]
    try:
        check_required_files(base, required)
    except MissingRequiredFilesError as exc:
        print(f"\033[91m{exc}\033[0m")
        sys.exit(1)
```

**Error Handling Pattern**:
- **Custom Exception**: Specific error type for missing files
- **Early Exit**: Prevents execution with incomplete setup
- **User Feedback**: Clear error message with color coding

### Dry Run Mode

```python
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
```

**Dry Run Features**:
- **Subject Prefix**: Adds "[DRAFT]" to distinguish test emails
- **Approvers Only**: Sends only to designated approvers
- **No Attachments**: Skips attachment processing for faster testing
- **Early Return**: Exits after test email

### Batch Processing Loop

```python
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
```

**Batch Processing Features**:
- **Slice Processing**: `to_list[i:i + batch_size]` creates batches
- **Error Isolation**: Batch failures don't stop entire process
- **Progress Tracking**: Counts sent emails and errors
- **Delay Management**: Waits between batches (but not after last batch)

### Final Reporting

```python
    duration = (datetime.now() - start).total_seconds()
    summary = f"Summary — Sent: {sent}, Errors: {errors}, Time: {duration:.2f}s"
    print(summary)
    logging.info(summary)
```

**Performance Metrics**:
- **Duration Calculation**: Total execution time
- **Comprehensive Stats**: Sent count, error count, timing
- **Dual Output**: Both console and log file

## Command Line Interface

### Argument Parser Setup

```python
def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="NotifyBot Email Sender CLI")
    parser.add_argument("base_folder", help="Directory with email source files")
    parser.add_argument("--dry-run", action="store_true", help="Send to approvers only")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of recipients per batch")
    parser.add_argument("--delay", type=int, default=5, help="Seconds delay between batches")
    parser.add_argument("--attachments-folder", type=str, help="Alternate folder for attachments")
    parser.add_argument("--max-attachment-size", type=int, default=10, help="Max MB per attachment")
```

**CLI Design**:
- **Positional Argument**: Required base folder
- **Optional Flags**: All configuration options have defaults
- **Type Conversion**: Automatic int conversion for numeric arguments
- **Help Text**: Descriptive help for each option

## Code Quality Features

### Type Hints Throughout

```python
def read_recipients(path: Path) -> List[str]:
def parse_filter_file(filter_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
def match_condition(actual: str, expected: str, mode: str = "exact") -> bool:
```

**Benefits**:
- **IDE Support**: Better autocomplete and error detection
- **Documentation**: Types serve as inline documentation
- **Debugging**: Easier to trace type-related issues

### Consistent Error Handling

```python
try:
    # operation
except Exception as exc:
    logging.error(f"Error description: {exc}")
    # appropriate fallback
```

**Pattern**:
- **Specific Error Context**: Each error message includes context
- **Logging**: All errors are logged for debugging
- **Graceful Degradation**: Functions continue or fail safely

### Modern Python Features

- **f-strings**: Modern string formatting
- **pathlib**: Modern path handling
- **Context managers**: Proper resource management
- **List comprehensions**: Concise data processing
- **Set operations**: Efficient deduplication

This code demonstrates professional Python development practices with robust error handling, comprehensive logging, and user-friendly interfaces.
