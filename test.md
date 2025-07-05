# NotifyBot Code - Step by Step Explanation

## 1. Import Statements and Setup

```python
import os
import csv
import re
import time
import logging
import smtplib
import sys
import mimetypes
from email.message import EmailMessage
from pathlib import Path
from typing import List, Tuple, Dict
```

**Purpose:** Import all necessary modules for the script
- `os`: Operating system interface (not actively used in current code)
- `csv`: Reading and writing CSV files for inventory and filter data
- `re`: Regular expressions for email validation
- `time`: Adding delays between email batches
- `logging`: Comprehensive logging system
- `smtplib`: SMTP client for sending emails
- `sys`: System-specific parameters (for `sys.exit()`)
- `mimetypes`: Detecting file types for attachments
- `email.message.EmailMessage`: Creating email objects
- `pathlib.Path`: Modern path handling
- `typing`: Type hints for better code documentation

## 2. Color Configuration for Logging

```python
LOG_COLORS = {
    'DEBUG': '\033[36m',   # Cyan
    'INFO': '\033[32m',    # Green
    'WARNING': '\033[33m', # Yellow
    'ERROR': '\033[31m',   # Red
    'RESET': '\033[0m'     # Reset to default
}
```

**Purpose:** Define ANSI color codes for terminal output
- Each log level gets a different color for better visibility
- Makes it easier to spot errors and warnings in console output

## 3. Custom Logging Formatter

```python
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname
        msg = super().format(record)
        color = LOG_COLORS.get(levelname, LOG_COLORS['RESET'])
        reset = LOG_COLORS['RESET']
        return f"{color}{msg}{reset}"
```

**Step by step:**
1. **Inherits from `logging.Formatter`** to customize log message appearance
2. **Gets the log level** (DEBUG, INFO, WARNING, ERROR) from the record
3. **Formats the message** using parent class formatter
4. **Looks up the color** for this log level from LOG_COLORS dictionary
5. **Wraps the message** with color codes and reset code
6. **Returns colored message** for console display

## 4. Custom Exception Class

```python
class MissingRequiredFilesError(Exception):
    """Custom exception for missing required files."""
    pass
```

**Purpose:** Create a specific exception type for missing files
- Makes error handling more specific and clear
- Allows catching this specific error type separately from other exceptions

## 5. Email Validation Function

```python
def is_valid_email(email: str) -> bool:
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None
```

**Step by step:**
1. **Uses regex pattern** `[^@]+@[^@]+\.[^@]+` to validate email format
2. **Pattern breakdown:**
   - `[^@]+`: One or more characters that are not '@' (username part)
   - `@`: Literal '@' symbol
   - `[^@]+`: One or more characters that are not '@' (domain name)
   - `\.`: Literal '.' (escaped dot)
   - `[^@]+`: One or more characters that are not '@' (domain extension)
3. **Returns True** if pattern matches, **False** otherwise

## 6. File Reading Function

```python
def read_file(path: Path) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Failed to read file {path}: {e}")
        return ""
```

**Step by step:**
1. **Try to open file** with UTF-8 encoding
2. **Read entire file content** and strip whitespace
3. **Return the content** as a string
4. **If any error occurs:**
   - Log the error with file path and error message
   - Return empty string as fallback

## 7. Recipients Reading Function

```python
def read_recipients(path: Path) -> List[str]:
    if not path.is_file():
        logging.warning(f"{path.name} does not exist. Continuing without it.")
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and is_valid_email(line.strip())]
    except Exception as e:
        logging.error(f"Failed to read recipients from {path}: {e}")
        return []
```

**Step by step:**
1. **Check if file exists** using `path.is_file()`
2. **If file doesn't exist:**
   - Log warning message
   - Return empty list (graceful handling)
3. **If file exists:**
   - Open file with UTF-8 encoding
   - Read each line and strip whitespace
   - Filter lines that are not empty AND are valid emails
   - Return list of valid email addresses
4. **If any error occurs:**
   - Log error message
   - Return empty list

## 8. Write to Text File Function

```python
def write_to_txt(emails: List[str], path: Path) -> None:
    try:
        with open(path, 'a', encoding='utf-8') as f:
            for email in emails:
                f.write(email + '\n')
        logging.info(f"Appended {len(emails)} new emails to {path.name}.")
    except Exception as e:
        logging.error(f"Failed to write to {path}: {e}")
```

**Step by step:**
1. **Open file in append mode** ('a') with UTF-8 encoding
2. **Loop through each email** in the provided list
3. **Write each email** to file with newline character
4. **Log success message** with count of emails written
5. **If error occurs:**
   - Log error message with file path and error details

## 9. Deduplication Function

```python
def deduplicate_file(path: Path) -> None:
    try:
        if not path.is_file():
            return
        with open(path, 'r', encoding='utf-8') as f:
            seen = set()
            lines = []
            for line in f:
                stripped = line.strip()
                if stripped and is_valid_email(stripped) and stripped not in seen:
                    seen.add(stripped)
                    lines.append(stripped)
        with open(path, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(line + '\n')
        logging.info(f"Deduplicated entries in {path.name}.")
    except Exception as e:
        logging.error(f"Failed to deduplicate file {path}: {e}")
```

**Step by step:**
1. **Check if file exists** - return early if not
2. **Read file and process each line:**
   - Create empty set `seen` to track unique emails
   - Create empty list `lines` to store unique emails
   - For each line in file:
     - Strip whitespace
     - Check if line is not empty AND is valid email AND not already seen
     - If all conditions met: add to seen set and lines list
3. **Write back to file:**
   - Open file in write mode (overwrites existing content)
   - Write each unique email with newline
4. **Log success** or **error** as appropriate

## 10. Required Files Validation

```python
def check_required_files(base_path: Path, required_files: List[str]) -> None:
    missing = [f for f in required_files if not (base_path / f).is_file()]
    if missing:
        message = f"Missing required files: {', '.join(missing)}"
        logging.error(message)
        raise MissingRequiredFilesError(message)
```

**Step by step:**
1. **Create list of missing files** using list comprehension:
   - Check each file in required_files list
   - Add to missing list if file doesn't exist in base_path
2. **If any files are missing:**
   - Create error message with comma-separated list of missing files
   - Log the error message
   - Raise custom exception with the message

## 11. Filter File Parser

```python
def parse_filter_file(filter_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    try:
        with open(filter_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            lines = list(reader)
        keys = lines[0]
        conditions = [dict(zip(keys, row)) for row in lines[1:]]
        return keys, conditions
    except Exception as e:
        logging.error(f"Failed to parse filter file {filter_path}: {e}")
        return [], []
```

**Step by step:**
1. **Open filter file** as CSV with UTF-8 encoding
2. **Read all lines** using csv.reader and convert to list
3. **Extract header row** (first line) as keys
4. **Create condition dictionaries:**
   - For each row after header (lines[1:])
   - Use zip(keys, row) to pair header with row values
   - Convert to dictionary
5. **Return tuple** of (keys, conditions)
6. **If error occurs:**
   - Log error message
   - Return empty lists as fallback

## 12. Email Filtering Function

```python
def get_filtered_emailids(base_path: Path) -> List[str]:
    inventory_file = base_path / 'inventory.csv'
    filter_file = base_path / 'filter.txt'

    if not inventory_file.is_file() or not filter_file.is_file():
        logging.warning("inventory.csv or filter.txt missing.")
        return []

    keys, conditions = parse_filter_file(filter_file)
    email_set = set()

    try:
        with open(inventory_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                for cond in conditions:
                    if all(row.get(k, '').strip() == v.strip() for k, v in cond.items()):
                        for email in re.split(r'[;,]', row.get('emailids', '')):
                            email_clean = email.strip()
                            if email_clean and is_valid_email(email_clean):
                                email_set.add(email_clean)
    except Exception as e:
        logging.error(f"Error reading inventory file: {e}")

    existing_to = set(read_recipients(base_path / 'to.txt'))
    return sorted(email_set.difference(existing_to))
```

**Step by step:**
1. **Define file paths** for inventory.csv and filter.txt
2. **Check if both files exist** - return empty list if either missing
3. **Parse filter file** to get keys and conditions
4. **Create empty set** for collecting unique emails
5. **Process inventory CSV:**
   - Open as CSV with DictReader for column name access
   - For each row in CSV:
     - For each filter condition:
       - Check if row matches ALL condition criteria
       - If match found, extract emails from 'emailids' column
       - Split emailids by semicolon or comma
       - Clean and validate each email
       - Add valid emails to set
6. **Remove existing recipients:**
   - Read existing recipients from to.txt
   - Return sorted list of new emails (filtered set minus existing)

## 13. Attachments Collection

```python
def get_attachments(base_path: Path) -> List[Tuple[str, bytes, str]]:
    attachments = []
    attach_dir = base_path / 'attachment'
    if not attach_dir.is_dir():
        return attachments

    for file_path in attach_dir.iterdir():
        if file_path.is_file():
            mime_type, _ = mimetypes.guess_type(file_path.name)
            if not mime_type:
                mime_type = 'application/octet-stream'
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                attachments.append((file_path.name, data, mime_type))
            except Exception as e:
                logging.error(f"Failed to read attachment {file_path.name}: {e}")
    return attachments
```

**Step by step:**
1. **Initialize empty attachments list**
2. **Define attachment directory** path
3. **Check if attachment directory exists** - return empty list if not
4. **Process each file in attachment directory:**
   - Skip if not a file (e.g., subdirectories)
   - Guess MIME type from file extension
   - Use default 'application/octet-stream' if type unknown
   - Read file in binary mode ('rb')
   - Create tuple of (filename, file_data, mime_type)
   - Add to attachments list
   - Log errors for unreadable files
5. **Return list of attachment tuples**

## 14. Email Sending Function

```python
def send_email(
    from_email: str,
    subject: str,
    body_html: str,
    recipients: List[str],
    cc_emails: List[str],
    bcc_emails: List[str],
    attachments: List[Tuple[str, bytes, str]] = None,
    log_sent: bool = False
) -> None:
```

**Step by step:**

### 14.1 Email Message Creation
```python
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ', '.join(recipients)
    if cc_emails:
        msg['Cc'] = ', '.join(cc_emails)
    msg.add_alternative(body_html, subtype='html')
```

1. **Create EmailMessage object**
2. **Set email headers:**
   - Subject line
   - From address
   - To recipients (joined with commas)
   - CC recipients if provided
3. **Add HTML body** using add_alternative method

### 14.2 Attachment Processing
```python
    if attachments:
        for filename, data, mime_type in attachments:
            maintype, subtype = mime_type.split('/', 1)
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)
```

1. **Check if attachments exist**
2. **For each attachment:**
   - Split MIME type into main type and subtype
   - Add attachment to message with proper MIME type and filename

### 14.3 Recipient List Processing
```python
    all_recipients = list(dict.fromkeys(recipients + cc_emails + bcc_emails))
```

1. **Combine all recipient lists** (TO, CC, BCC)
2. **Remove duplicates** using dict.fromkeys() trick
3. **Convert back to list** for SMTP sending

### 14.4 Email Sending
```python
    try:
        with smtplib.SMTP('localhost') as server:
            server.send_message(msg, from_addr=from_email, to_addrs=all_recipients)
        print(f"Sent to {len(recipients)} recipient(s).")
        logging.info(f"Sent to {', '.join(recipients)}")
    except Exception as e:
        logging.error(f"Failed to send email to: {recipients}. Error: {e}", exc_info=True)
        print(f"Failed to send to {', '.join(recipients)}")
```

1. **Connect to SMTP server** on localhost
2. **Send email message** with all recipients
3. **Log success** with recipient count and list
4. **Handle errors:**
   - Log detailed error with stack trace
   - Print user-friendly error message

## 15. Recipient List Preparation

```python
def prepare_to_txt(base_path: Path) -> None:
    new_emails = get_filtered_emailids(base_path)
    if new_emails:
        write_to_txt(new_emails, base_path / 'to.txt')
        print(f"Added {len(new_emails)} new email(s) to to.txt")
        logging.debug(f"New emails appended: {new_emails}")

    additional_to = read_recipients(base_path / 'additional_to.txt')
    if additional_to:
        write_to_txt(additional_to, base_path / 'to.txt')
        print(f"Appended {len(additional_to)} email(s) from additional_to.txt to to.txt")
        logging.debug(f"Additional emails appended: {additional_to}")

    deduplicate_file(base_path / 'to.txt')
```

**Step by step:**
1. **Get filtered emails** from inventory based on filter conditions
2. **If new emails found:**
   - Append to to.txt file
   - Print count to user
   - Log details at debug level
3. **Read additional recipients** from additional_to.txt file
4. **If additional recipients found:**
   - Append to to.txt file
   - Print count to user
   - Log details at debug level
5. **Deduplicate final to.txt file** to remove any duplicates

## 16. Main Email Sending Function

```python
def send_email_from_folder(base_folder: str, dry_run: bool = False, batch_size: int = 500, delay: int = 5) -> None:
```

### 16.1 Setup and Validation
```python
    base_path = Path(base_folder)
    logging.info(f"--- Start sending emails from {base_folder} ---")

    required_files = ['from.txt', 'subject.txt', 'body.html', 'approver.txt']

    try:
        check_required_files(base_path, required_files)
    except MissingRequiredFilesError as e:
        print(str(e))
        sys.exit(1)
```

1. **Convert folder path** to Path object
2. **Log start of process**
3. **Define required files** list
4. **Validate required files exist:**
   - Exit with error code 1 if any missing
   - Print error message to user

### 16.2 Read Configuration Files
```python
    subject = read_file(base_path / 'subject.txt')
    body_html = read_file(base_path / 'body.html')
    from_email = read_file(base_path / 'from.txt')
    approvers = read_recipients(base_path / 'approver.txt')
```

1. **Read email subject** from subject.txt
2. **Read HTML body** from body.html
3. **Read sender email** from from.txt
4. **Read approver emails** from approver.txt

### 16.3 Validate Critical Content
```python
    if not subject:
        print("Error: subject.txt is missing or empty. Exiting.")
        logging.error("subject.txt is missing or empty.")
        sys.exit(1)

    if not body_html:
        print("Error: body.html is missing or empty. Exiting.")
        logging.error("body.html is missing or empty.")
        sys.exit(1)

    if not approvers:
        print("Approver list is empty.")
        logging.warning("Approver list is empty.")
        return
```

1. **Check if subject is empty** - exit if so
2. **Check if body is empty** - exit if so  
3. **Check if approvers list is empty** - return early if so

### 16.4 Prepare Data
```python
    prepare_to_txt(base_path)
    attachments = get_attachments(base_path)
```

1. **Prepare recipient list** by combining filtered and additional recipients
2. **Collect attachments** from attachment directory

### 16.5 Handle Dry Run Mode
```python
    if dry_run:
        print("Dry-run mode: Draft email sent to approvers only.")
        send_email(from_email, "[DRAFT] " + subject, body_html, approvers, [], [], attachments=attachments)
        logging.info("Dry-run complete. No actual recipients emailed.")
        return
```

1. **If dry run mode:**
   - Print message to user
   - Send email to approvers only with "[DRAFT]" prefix
   - Log completion
   - Return without sending to actual recipients

### 16.6 Read Final Recipient Lists
```python
    to_emails = read_recipients(base_path / 'to.txt')
    cc_emails = read_recipients(base_path / 'cc.txt')
    bcc_emails = read_recipients(base_path / 'bcc.txt')

    if not to_emails:
        print("No recipients found in to.txt.")
        logging.info("No recipients found in to.txt.")
        return
```

1. **Read final recipient lists** from TO, CC, BCC files
2. **Check if TO list is empty** - return early if so

### 16.7 Batch Email Sending
```python
    total_sent = 0

    for i in range(0, len(to_emails), batch_size):
        batch = to_emails[i:i + batch_size]
        logging.debug(f"Sending batch {i // batch_size + 1}: {batch}")
        send_email(from_email, subject, body_html, batch, cc_emails, bcc_emails, attachments=attachments)
        total_sent += len(batch)
        if i + batch_size < len(to_emails):
            print(f"Waiting {delay} seconds before sending next batch...")
            logging.info(f"Waiting {delay} seconds before sending next batch...")
            time.sleep(delay)
```

1. **Initialize total sent counter**
2. **Process emails in batches:**
   - Calculate batch slice (i to i+batch_size)
   - Log batch details at debug level
   - Send email to current batch
   - Update total sent counter
   - If more batches remain:
     - Print delay message
     - Log delay message
     - Wait specified delay time

### 16.8 Final Summary
```python
    print("Emails sent successfully.")
    print(f"Summary:\n - Sent: {total_sent}")
    logging.info(f"Email Summary -> Sent: {total_sent}")
```

1. **Print success message**
2. **Print summary with total count**
3. **Log final summary**

## 17. Command Line Interface

```python
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="NotifyBot Email Sender")
    parser.add_argument("base_folder", help="Base folder containing email files")
    parser.add_argument("--dry-run", action="store_true", help="Only send draft to approver, skip actual email send")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of emails to send per batch (default: 500)")
    parser.add_argument("--delay", type=int, default=5, help="Seconds to wait between batches (default: 5)")
    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help="Set logging level (default: INFO)"
    )

    args = parser.parse_args()
```

**Step by step:**
1. **Create argument parser** with description
2. **Add positional argument** for base folder path
3. **Add optional arguments:**
   - `--dry-run`: Boolean flag for test mode
   - `--batch-size`: Integer for emails per batch
   - `--delay`: Integer for seconds between batches
   - `--log-level`: Choice from predefined log levels
4. **Parse command line arguments**

## 18. Logging Configuration

```python
    # File handler (no colors)
    file_handler = logging.FileHandler('notifybot.log', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s'
    ))

    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s'
    ))

    logger = logging.getLogger()
    logger.handlers = []  # Clear existing handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    numeric_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
```

**Step by step:**
1. **Create file handler:**
   - Logs to 'notifybot.log' file
   - Uses UTF-8 encoding
   - Uses standard formatter (no colors)
2. **Create console handler:**
   - Logs to terminal/console
   - Uses colored formatter for better visibility
3. **Configure root logger:**
   - Clear any existing handlers
   - Add both file and console handlers
   - Set log level from command line argument

## 19. Main Execution

```python
    send_email_from_folder(args.base_folder, dry_run=args.dry_run, batch_size=args.batch_size, delay=args.delay)
```

**Final step:**
1. **Call main function** with all parsed arguments
2. **Script execution begins** with the configured parameters

## Summary of Program Flow

1. **Parse command line arguments**
2. **Setup logging system** (file + colored console)
3. **Validate required files exist**
4. **Read email configuration** (subject, body, sender, approvers)
5. **Prepare recipient lists:**
   - Filter inventory based on conditions
   - Add additional recipients  
   - Deduplicate final list
6. **Collect attachments** from attachment directory
7. **Either:**
   - **Dry run**: Send draft to approvers only
   - **Real run**: Send emails in batches with delays
8. **Log results and provide summary**

The code is well-structured with proper error handling, logging, and modular functions that each handle a specific responsibility.
