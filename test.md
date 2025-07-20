# NotifyBot: Step-by-Step Code Explanation

## Overview
NotifyBot is a Python script designed for automated batch email sending with advanced features like filtering, logging, attachment support, and dry-run capabilities. It uses the system's `sendmail` command for email delivery.

## 1. Script Structure and Imports

### Core Dependencies
```python
import argparse, csv, logging, mimetypes, re, shutil, sys, time, traceback, os, json
from datetime import datetime
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Tuple, Dict, Set
import subprocess
from email_validator import validate_email, EmailNotValidError
```

**Purpose**: The script uses standard library modules for file handling, email composition, subprocess management, and third-party `email_validator` for email validation.

## 2. Configuration and Path Setup

### Directory Structure
```python
NOTIFYBOT_ROOT = Path("/notifybot")
BASEFOLDER_PATH = NOTIFYBOT_ROOT / "basefolder"
LOG_FILENAME = NOTIFYBOT_ROOT / "logs" / "notifybot.log"
INVENTORY_PATH = NOTIFYBOT_ROOT / "inventory" / "inventory.csv"
```

**Purpose**: Establishes a fixed directory structure:
- `/notifybot/` - Root directory
- `/notifybot/basefolder/` - Contains email campaign folders
- `/notifybot/logs/` - Log files
- `/notifybot/inventory/` - Master inventory CSV for filtering

## 3. Core Helper Functions

### A. Path Validation (`validate_base_folder`)
```python
def validate_base_folder(base_folder: str) -> Path:
    base_folder_path = BASEFOLDER_PATH / base_folder
    if not base_folder_path.is_dir():
        raise ValueError(f"Invalid base folder: {base_folder}")
    return base_folder_path
```

**Purpose**: Ensures the specified campaign folder exists within the enforced directory structure.

### B. Logging System (`csv_log_entry`, `setup_logging`)
```python
def csv_log_entry(message: str) -> str:
    timestamp_epoch = int(time.time())
    username = os.getlogin() or os.getenv('USER', 'unknown')
    return f"{timestamp_epoch},{username},{message}"
```

**Purpose**: Creates structured CSV-format log entries with timestamps and user information for audit trails.

### C. Email Validation (`is_valid_email`)
```python
def is_valid_email(email: str) -> bool:
    try:
        validate_email(email.strip(), check_deliverability=False)
        # Additional sendmail compatibility checks
        if len(email) > 320: return False
        problematic_chars = ['|', '`', '$', '\\']
        if any(char in email for char in problematic_chars):
            return False
        return True
    except EmailNotValidError:
        return False
```

**Purpose**: Validates email syntax using `email_validator` library and adds additional checks for sendmail compatibility.

## 4. File Operations

### A. Reading Files (`read_file`, `read_recipients`)
```python
def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()

def read_recipients(path: Path, delimiters: str = ";") -> List[str]:
    valid = []
    for line in path.read_text(encoding="utf-8").splitlines():
        for email in extract_emails(line.strip(), delimiters):
            if is_valid_email(email):
                valid.append(email)
    return valid
```

**Purpose**: Safely reads text files and processes recipient lists with email validation and delimiter splitting.

### B. Recipient Management (`merge_recipients`, `deduplicate_file`)
```python
def merge_recipients(base_recipients: List[str], additional_recipients: List[str]) -> List[str]:
    seen = set()
    merged = []
    for email in base_recipients + additional_recipients:
        email_lower = email.lower()
        if email_lower not in seen:
            seen.add(email_lower)
            merged.append(email)
    return merged
```

**Purpose**: Combines recipient lists while removing duplicates and preserving order.

## 5. File Validation System

### Required Files Check (`check_required_files`)
```python
def check_required_files(base: Path, required: List[str], dry_run: bool = True) -> None:
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        raise MissingRequiredFilesError(f"Missing required files: {', '.join(missing)}")
    
    if not dry_run:
        # Check for at least one recipient source
        has_to = (base / "to.txt").is_file()
        has_filters = (base / "filter.txt").is_file() and INVENTORY_PATH.is_file()
        has_additional = (base / "additional_to.txt").is_file()
        
        if not (has_to or has_filters or has_additional):
            raise MissingRequiredFilesError("Missing recipient source")
```

**Purpose**: Ensures all required files exist before proceeding. In live mode, validates at least one recipient source is available.

### Required Files:
- `subject.txt` - Email subject line
- `body.html` - HTML email body
- `from.txt` - Sender email address
- `approver.txt` - Approver emails for dry-run mode

### Recipient Sources (at least one needed for live mode):
- `to.txt` - Direct recipient list
- `filter.txt` + `inventory.csv` - Filter-based recipient selection
- `additional_to.txt` - Additional recipients to merge

## 6. Email Composition and Sending

### A. Attachment Handling (`add_attachments`)
```python
def add_attachments(msg: MIMEMultipart, attachment_folder: Path) -> None:
    for file_path in attachment_folder.iterdir():
        if file_path.is_file():
            ctype, encoding = mimetypes.guess_type(str(file_path))
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            
            maintype, subtype = ctype.split('/', 1)
            with open(file_path, 'rb') as fp:
                attachment = MIMEBase(maintype, subtype)
                attachment.set_payload(fp.read())
                encoders.encode_base64(attachment)
                attachment.add_header('Content-Disposition', 
                                    f'attachment; filename="{sanitize_filename(file_path.name)}"')
                msg.attach(attachment)
```

**Purpose**: Automatically attaches all files from the `attachment/` folder to emails with proper MIME type detection.

### B. Sendmail Integration (`send_via_sendmail`)
```python
def send_via_sendmail(recipients: List[str], subject: str, body_html: str, 
                     from_address: str, attachment_folder: Path = None, 
                     dry_run: bool = False) -> bool:
    if dry_run:
        log_and_print("info", f"Dry run: Would send email to {len(recipients)} recipients")
        return True
    
    msg = create_email_message(recipients, subject, body_html, from_address, attachment_folder)
    email_content = msg.as_string()
    sendmail_path = find_sendmail_path()
    sendmail_cmd = [sendmail_path, '-t', '-f', from_address] + recipients
    
    process = subprocess.Popen(sendmail_cmd, stdin=subprocess.PIPE, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate(input=email_content, timeout=60)
    
    return process.returncode == 0
```

**Purpose**: Sends emails using the system's sendmail command. In dry-run mode, it only logs what would be sent.

## 7. Filtering System

### Filter Logic (`apply_filter_logic`)
```python
def apply_filter_logic(filters: List[str], inventory_path: Path) -> List[str]:
    filtered_recipients = []
    with open(inventory_path, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if matches_filter_conditions(row, filters):
                if 'email' in row and is_valid_email(row['email']):
                    filtered_recipients.append(row["email"])
    return filtered_recipients

def matches_filter_conditions(row: Dict, filters: List[str]) -> bool:
    for filter_condition in filters:
        if '=' in filter_condition:
            key, value = filter_condition.split('=', 1)
            if key.strip() in row and str(row[key.strip()]).lower() == value.strip().lower():
                continue
            else:
                return False
        else:
            # Substring search in all values
            if any(filter_condition.lower() in str(v).lower() for v in row.values()):
                continue
            else:
                return False
    return True
```

**Purpose**: Implements flexible filtering against a CSV inventory file using key=value pairs or substring matching.

## 8. Batch Processing System

### Batch Email Sending (`send_email_batch`)
```python
def send_email_batch(recipients: List[str], subject: str, body_html: str, 
                    from_address: str, batch_size: int, dry_run: bool = False, 
                    delay: float = 5.0, attachment_folder: Path = None) -> None:
    total_recipients = len(recipients)
    successful_batches = 0
    failed_batches = 0
    
    for i in range(0, total_recipients, batch_size):
        batch = recipients[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total_recipients + batch_size - 1) // batch_size
        
        if send_via_sendmail(batch, subject, body_html, from_address, attachment_folder, dry_run):
            successful_batches += 1
        else:
            failed_batches += 1
        
        # Add delay between batches (except for the last batch)
        if i + batch_size < total_recipients and not dry_run:
            time.sleep(delay)
```

**Purpose**: Processes emails in configurable batches with delays to avoid overwhelming mail servers and respect rate limits.

## 9. Main Execution Flow

### Command Line Interface
```python
parser = argparse.ArgumentParser(description="Send batch emails with attachments.")
parser.add_argument("--base-folder", required=True, help="Base folder name inside /notifybot/basefolder.")
parser.add_argument("--dry-run", action="store_true", help="Simulate sending emails.")
parser.add_argument("--force", action="store_true", help="Skip confirmation prompt.")
parser.add_argument("--batch-size", type=int, default=500, help="Number of emails per batch (default: 500).")
parser.add_argument("--delay", type=float, default=5.0, help="Delay in seconds between batches (default: 5.0).")
```

### Main Processing Steps:

1. **Setup and Validation**
   - Initialize logging system
   - Rotate previous log file
   - Validate base folder path
   - Check required files exist

2. **Content Loading**
   - Read email subject, body, from address
   - Load approver emails for dry-run

3. **Recipient Resolution Priority**
   - **Priority 1**: Use `to.txt` if exists, merge with `additional_to.txt` if present
   - **Priority 2**: Apply filter logic from `filter.txt` + `inventory.csv`, merge with `additional_to.txt`
   - **Priority 3**: Use only `additional_to.txt`
   - **Fallback**: Use approver emails for dry-run mode

4. **Pre-send Validation**
   - Validate essential content (subject, body, from address)
   - Check for attachment folder
   - Display email summary

5. **Confirmation and Execution**
   - Prompt user for confirmation (unless `--force` used)
   - Execute batch email sending with specified parameters

## 10. Key Features

### Security Features
- Path validation prevents directory traversal
- Email validation with sendmail compatibility checks
- Filename sanitization for attachments
- Audit logging with timestamps and user tracking

### Flexibility Features
- Multiple recipient source options with priority system
- Configurable batch sizes and delays
- Dry-run mode for testing
- Automatic deduplication and merging
- Support for any file type as attachments

### Reliability Features
- Comprehensive error handling and logging
- Log file rotation
- Backup creation before file modifications
- Timeout protection for sendmail operations
- Graceful handling of missing files

## 11. Usage Examples

```bash
# Dry run test
python notifybot.py --base-folder campaign1 --dry-run

# Live send with custom batch settings
python notifybot.py --base-folder campaign1 --batch-size 100 --delay 10.0

# Automated send without confirmation
python notifybot.py --base-folder campaign1 --force
```

## 12. File Structure Example

```
/notifybot/
├── basefolder/
│   └── campaign1/
│       ├── subject.txt          # Required: Email subject
│       ├── body.html            # Required: HTML email body  
│       ├── from.txt             # Required: Sender address
│       ├── approver.txt         # Required: Approver emails
│       ├── to.txt              # Optional: Direct recipients
│       ├── filter.txt          # Optional: Filter conditions
│       ├── additional_to.txt   # Optional: Additional recipients
│       └── attachment/         # Optional: Attachment files
├── inventory/
│   └── inventory.csv           # Master inventory for filtering
└── logs/
    └── notifybot.log          # Current log file
```

This script provides a robust, enterprise-ready solution for automated email campaigns with comprehensive logging, error handling, and flexible recipient management.
