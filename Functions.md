# NotifyBot: Complete Code Explanation

## Overview
NotifyBot is an automated email batch sender with advanced features like filtering, logging, dry-run support, and attachment handling. It's designed to send emails to multiple recipients efficiently while providing safety mechanisms.

## Key Features
- **Batch Processing**: Sends emails in configurable batches with delays
- **Filtering System**: Uses CSV inventory with filter conditions
- **Dry Run Mode**: Test without actually sending emails
- **Attachment Support**: Handles multiple file attachments with size limits
- **Email Validation**: Validates email addresses before sending
- **Logging**: Comprehensive logging with rotation
- **Deduplication**: Removes duplicate email addresses

## Directory Structure
```
base/
├── body.html          # Email body content (HTML format)
├── subject.txt        # Email subject line
├── to.txt            # Recipient email addresses
├── inventory.csv     # Optional: Database of contacts with metadata
├── filter.txt        # Optional: Filter conditions in CSV format
└── attachment/       # Folder containing files to attach
```

## Step-by-Step Code Explanation

### 1. Imports and Setup
```python
import argparse, csv, logging, mimetypes, re, shutil, smtplib, sys, time, unicodedata
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import List, Tuple, Dict
from email_validator import validate_email, EmailNotValidError
```

**Purpose**: Imports all necessary libraries for email handling, file operations, logging, and validation.

### 2. Custom Exception Class
```python
class MissingRequiredFilesError(Exception):
    """Exception raised when required input files are missing."""
```

**Purpose**: Custom exception for handling missing required files scenario.

### 3. Log File Management

#### `rotate_log_file()`
```python
def rotate_log_file() -> None:
    log_path = Path(LOG_FILENAME)
    if log_path.is_file():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_name = log_path.with_name(f"notifybot_{timestamp}.log")
        log_path.rename(rotated_name)
```

**Steps**:
1. Checks if existing log file exists
2. Creates timestamp-based filename
3. Renames old log file to prevent overwriting
4. Allows fresh logging for each run

#### `setup_logging()`
```python
def setup_logging() -> None:
    logging.basicConfig(
        filename=LOG_FILENAME,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s",
    )
```

**Steps**:
1. Configures Python's logging system
2. Sets log level to INFO and above
3. Creates detailed format with timestamp, level, function name, and line number
4. Outputs to file for persistent logging

#### `log_and_print()`
```python
def log_and_print(level: str, message: str) -> None:
    level = level.lower()
    colors = {"info": "\033[94m", "warning": "\033[93m", "error": "\033[91m"}
    color = colors.get(level, "\033[0m")
    getattr(logging, level, logging.info)(message)
    print(f"{color}{message}\033[0m")
```

**Steps**:
1. Accepts log level and message
2. Defines color codes for different log levels
3. Logs message to file using appropriate logging level
4. Prints colored message to console for immediate feedback

### 4. Email Validation

#### `is_valid_email()`
```python
def is_valid_email(email: str) -> bool:
    try:
        validate_email(email.strip())
        return True
    except EmailNotValidError:
        return False
```

**Steps**:
1. Strips whitespace from email
2. Uses `email_validator` library for RFC-compliant validation
3. Returns True for valid emails, False for invalid ones
4. Handles validation errors gracefully

### 5. File Operations

#### `read_file()`
```python
def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        log_and_print("error", f"Failed to read file {path}: {exc}")
        return ""
```

**Steps**:
1. Attempts to read file with UTF-8 encoding
2. Strips whitespace from content
3. Handles file reading errors gracefully
4. Returns empty string on failure

#### `extract_emails()`
```python
def extract_emails(raw: str, delimiters: str = ";") -> List[str]:
    if not raw:
        return []
    return [e.strip() for e in re.split(f"[{re.escape(delimiters)}]", raw) if e.strip()]
```

**Steps**:
1. Checks if input string is empty
2. Uses regex to split on specified delimiters (default: semicolon)
3. Strips whitespace from each email
4. Filters out empty strings
5. Returns list of clean email addresses

#### `read_recipients()`
```python
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
```

**Steps**:
1. Checks if file exists
2. Opens file and reads line by line
3. Extracts emails from each line using delimiters
4. Validates each email address
5. Collects only valid emails
6. Logs warnings for invalid emails

### 6. Deduplication

#### `deduplicate_file()`
```python
def deduplicate_file(path: Path) -> None:
    if not path.is_file():
        return
    
    backup = path.with_name(f"{path.stem}_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}")
    shutil.copy2(path, backup)
    
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
```

**Steps**:
1. Checks if file exists
2. Creates timestamped backup of original file
3. Reads all lines and tracks seen lines in a set
4. Keeps only unique, non-empty lines
5. Overwrites original file with deduplicated content
6. Preserves original file order

### 7. File Validation

#### `check_required_files()`
```python
def check_required_files(base: Path, required: List[str]) -> None:
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        raise MissingRequiredFilesError(f"Missing: {', '.join(missing)}")
```

**Steps**:
1. Checks each required file in the base directory
2. Creates list of missing files
3. Raises custom exception if any files are missing
4. Provides clear error message listing missing files

### 8. Filtering System

#### `parse_filter_file()`
```python
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
```

**Steps**:
1. Opens filter file as CSV
2. Reads all rows into dictionary format
3. Sets default values for optional fields (mode, regex_flags)
4. Returns column headers and row data
5. Handles parsing errors gracefully

#### `match_condition()`
```python
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
```

**Steps**:
1. Strips whitespace from both strings
2. **Exact mode**: Case-insensitive exact match
3. **Contains mode**: Case-insensitive substring search
4. **Regex mode**: 
   - Parses regex flags (e.g., "IGNORECASE|MULTILINE")
   - Applies flags to regex search
   - Handles regex syntax errors
5. Falls back to exact match for unknown modes

#### `get_filtered_emailids()`
```python
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
```

**Steps**:
1. Checks if both inventory.csv and filter.txt exist
2. Parses filter conditions from filter.txt
3. Reads inventory.csv row by row
4. For each row, tests ALL filter conditions (AND logic)
5. If all conditions match, extracts emails from that row
6. Collects unique emails in a set
7. Reads existing recipients from to.txt
8. Returns only new emails (not already in to.txt)
9. Validates and sorts final email list

### 9. Attachment Handling

#### `sanitize_filename()`
```python
def sanitize_filename(filename: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", filename)
        .encode("ASCII", "ignore")
        .decode
