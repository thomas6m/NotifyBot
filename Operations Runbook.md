# Email Notification Script Documentation

## Overview

This Python script provides a comprehensive email notification system with advanced features including email validation, attachment handling, CSV-based filtering, logging, deduplication, and dry-run capabilities. It's designed for bulk email operations with proper error handling and batch processing.

## Features

- **Email Validation**: RFC-compliant email validation using the `email_validator` library
- **Attachment Filtering**: Size-based attachment filtering with configurable limits
- **Comprehensive Logging**: Detailed logging with timestamps and function tracking
- **Deduplication**: Automatic removal of duplicate email addresses
- **Dry-run Mode**: Test mode for sending emails only to approvers
- **CSV Filtering**: Advanced recipient filtering based on CSV data
- **Batch Processing**: Configurable batch sizes with delays between sends
- **Error Handling**: Robust error handling with custom exceptions

## Dependencies

```python
#!/usr/bin/env python3

# Core Python modules
from pathlib import Path
import shutil
import smtplib
from email.message import EmailMessage
import csv
import re
import logging
import time
import sys
from datetime import datetime
from typing import List, Optional, Tuple, Dict

# External dependencies
from email_validator import validate_email, EmailNotValidError
```

## Configuration

### Logging Setup

```python
logging.basicConfig(
    filename="notifybot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s",
)
```

Creates a log file `notifybot.log` that captures:
- Timestamps
- Log levels
- Function names
- Line numbers
- Detailed messages

### Custom Exception

```python
class MissingRequiredFilesError(Exception):
    """Raised when required input files are missing."""
    pass
```

## Core Functions

### 1. Email Validation

```python
def is_valid_email(email: str) -> bool:
    """Validates email addresses using RFC standards."""
```

- Uses the `email_validator` package for RFC-compliant validation
- Strips whitespace from input
- Returns `True` for valid emails, `False` otherwise

### 2. File Operations

#### Read File Content
```python
def read_file(path: Path) -> str:
    """Reads entire file content as a string, returns empty on failure."""
```

#### Read and Validate Recipients
```python
def read_recipients(path: Path) -> List[str]:
    """Reads emails line-by-line, validates and filters invalid emails."""
```

- Reads email addresses from text files
- Validates each email address
- Logs warnings for invalid emails
- Returns list of valid email addresses

#### Write Emails to File
```python
def write_to_txt(emails: List[str], path: Path) -> None:
    """Appends given emails (one per line) to a specified text file."""
```

#### File Deduplication
```python
def deduplicate_file(path: Path) -> None:
    """Creates backup, removes duplicates, writes unique lines back."""
```

- Creates a backup of the original file
- Removes duplicate entries
- Preserves original file structure

### 3. File System Validation

```python
def check_required_files(base: Path, required: List[str]) -> None:
    """Checks if all required files exist in base directory."""
```

- Validates presence of required input files
- Raises `MissingRequiredFilesError` if any files are missing

### 4. CSV Processing

#### Parse Filter File
```python
def parse_filter_file(filter_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """Parses CSV file, returns headers and list of dictionaries (rows)."""
```

#### Get Filtered Email IDs
```python
def get_filtered_emailids(base: Path) -> List[str]:
    """Filters inventory based on conditions and extracts valid emails."""
```

This function:
- Reads `inventory.csv` and `filter.txt` from the base folder
- Filters inventory rows matching filter conditions
- Extracts emails from the 'emailids' column
- Validates extracted emails
- Excludes emails already present in `to.txt`
- Returns list of new valid emails

### 5. Email Sending

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

**Features:**
- Composes emails with HTML content and plain text fallback
- Handles attachments with configurable size limits
- Uses local SMTP server (localhost) for sending
- Comprehensive logging of success and errors
- Real-time feedback via console output

### 6. Recipient List Preparation

```python
def prepare_to_txt(base: Path) -> None:
    """Prepares the to.txt recipient list with filtering and deduplication."""
```

**Process:**
1. If `to.txt` doesn't exist:
   - Gets filtered emails from inventory and filter files
   - Writes filtered emails to `to.txt`
2. Appends emails from `additional_to.txt` (if exists)
3. Deduplicates the final `to.txt` file

## Main Workflow

### Primary Sending Function

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

**Workflow Steps:**

1. **File Validation**: Checks for required files:
   - `from.txt` - Sender email address
   - `subject.txt` - Email subject line
   - `body.html` - HTML email content
   - `approver.txt` - Approver email addresses

2. **Content Reading**: Reads sender, subject, body, and approver information

3. **Recipient Preparation**: Calls `prepare_to_txt()` to build recipient list

4. **Dry-run Mode**: If enabled, sends draft only to approvers for review

5. **Production Mode**: 
   - Reads recipient lists from `to.txt`, `cc.txt`, and `bcc.txt`
   - Processes attachments from specified folder
   - Sends emails in configurable batches
   - Implements delays between batches

6. **Final Processing**: 
   - Performs final deduplication
   - Logs comprehensive summary
   - Reports sent emails, errors, and total execution time

## Command Line Interface

```python
def main() -> None:
    """Command line interface with argparse for configuration."""
```

**Available Options:**
- `--base-folder`: Directory containing email files
- `--dry-run`: Enable dry-run mode (send only to approvers)
- `--batch-size`: Number of emails per batch (default: 500)
- `--delay`: Delay between batches in seconds (default: 5)
- `--attachments-folder`: Directory containing attachment files
- `--max-attachment-size`: Maximum attachment size in MB (default: 10)

## Required File Structure

```
email_folder/
├── from.txt          # Sender email address
├── subject.txt       # Email subject line
├── body.html         # HTML email content
├── approver.txt      # Approver email addresses
├── inventory.csv     # Main data source (optional)
├── filter.txt        # Filter conditions (optional)
├── additional_to.txt # Additional recipients (optional)
├── cc.txt           # CC recipients (optional)
├── bcc.txt          # BCC recipients (optional)
└── to.txt           # Main recipients (auto-generated)
```

## Usage Examples

### Basic Usage
```bash
python3 email_script.py --base-folder /path/to/email/folder
```

### Dry-run Mode
```bash
python3 email_script.py --base-folder /path/to/email/folder --dry-run
```

### Custom Batch Configuration
```bash
python3 email_script.py \
    --base-folder /path/to/email/folder \
    --batch-size 100 \
    --delay 10 \
    --attachments-folder /path/to/attachments \
    --max-attachment-size 25
```

## Logging and Monitoring

The script provides comprehensive logging through:

- **File Logging**: All activities logged to `notifybot.log`
- **Console Output**: Real-time feedback during execution
- **Error Tracking**: Detailed error messages and stack traces
- **Performance Metrics**: Execution time and batch processing statistics

## Error Handling

The script includes robust error handling for:

- Missing required files
- Invalid email addresses
- SMTP connection failures
- Attachment size violations
- CSV parsing errors
- File system permissions

## Security Considerations

- Uses local SMTP server (localhost) for sending
- Validates all email addresses before processing
- Implements file size limits for attachments
- Provides dry-run mode for testing
- Comprehensive logging for audit trails

## Best Practices

1. **Always test with dry-run mode** before production sends
2. **Monitor log files** for errors and warnings
3. **Use appropriate batch sizes** to avoid overwhelming SMTP servers
4. **Implement proper delays** between batches
5. **Validate recipient lists** before bulk operations
6. **Regular backup** of important data files
7. **Monitor attachment sizes** to prevent delivery issues
