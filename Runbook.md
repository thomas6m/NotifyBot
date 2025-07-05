# NotifyBot Email Sender Documentation

## Overview

NotifyBot is a comprehensive batch email sender that automates email distribution based on content stored in files. It provides advanced features including attachment handling, recipient filtering, batch processing with delays, comprehensive logging, validation, error handling, and deduplication capabilities.

## Key Features

- **Batch Processing**: Send emails in configurable batches with customizable delays
- **Recipient Filtering**: Advanced filtering based on CSV data conditions
- **Attachment Support**: Automatic MIME type detection and file attachment
- **Validation**: Email format validation and required file checking
- **Logging**: Comprehensive logging with timestamps and error tracking
- **Deduplication**: Automatic removal of duplicate recipients
- **Dry Run Mode**: Test mode for sending drafts to approvers only
- **Backup System**: Automatic backup creation before file modifications

## Dependencies and Imports

### Core Libraries
- `os` - File and directory operations
- `csv` - CSV file processing (inventory.csv)
- `re` - Regular expressions for email validation
- `time` - Batch delay management
- `logging` - Comprehensive logging functionality
- `smtplib` - SMTP email sending
- `sys` - System-specific parameters
- `mimetypes` - Automatic file type detection for attachments
- `shutil` - File operations and backup creation

### Email and Utility Libraries
- `email.message.EmailMessage` - Email composition and sending
- `pathlib.Path` - Object-oriented file path handling
- `typing` - Type hints for better code documentation
- `email.utils.parseaddr` - Email address parsing
- `datetime` - Timestamp generation and time calculations

## Core Components

### Email Validation
```python
EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")
```
Regular expression pattern for validating email addresses in standard format (example@domain.com).

### Logging Configuration
```python
logging.basicConfig(
    filename='notifybot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(funcName)s [line %(lineno)d] - %(message)s'
)
```
Configures detailed logging with timestamps, log levels, function names, and line numbers.

### Custom Exception Handling
```python
class MissingRequiredFilesError(Exception):
    """Custom exception raised when required input files are missing."""
    pass
```

## File Operations

### File Reading Functions

#### `read_file(path: Path) -> str`
- Reads and returns the complete content of a file as a string
- Handles file encoding and error cases

#### `read_recipients(path: Path) -> List[str]`
- Reads email addresses from a file
- Validates each email using regex pattern
- Returns only valid email addresses
- Filters out malformed entries

### File Writing and Management

#### `write_to_txt(emails: List[str], path: Path) -> None`
- Appends a list of email addresses to a text file
- Ensures proper formatting and line breaks

#### `deduplicate_file(path: Path) -> None`
- Creates a backup of the original file
- Removes duplicate lines while preserving order
- Overwrites the original file with deduplicated content

## Validation and Filtering

### File Validation
#### `check_required_files(base_path: Path, required_files: List[str]) -> None`
Verifies the presence of all required files in the base directory:
- `from.txt` - Sender email address
- `subject.txt` - Email subject line
- `body.html` - HTML email body content
- `approver.txt` - Approver email addresses for dry runs

### Filter Processing
#### `parse_filter_file(filter_path: Path) -> Tuple[List[str], List[Dict[str, str]]]`
- Parses the `filter.txt` file
- Extracts filtering conditions for CSV data processing
- Returns structured filter criteria

#### `get_filtered_emailids(base_path: Path) -> List[str]`
- Applies filter conditions to `inventory.csv`
- Excludes email IDs already present in `to.txt`
- Returns unique, filtered email addresses

## Email Sending Engine

### Core Sending Function
#### `send_email()` Parameters:
- `from_email: str` - Sender email address
- `subject: str` - Email subject line
- `body_html: str` - HTML formatted email body
- `recipients: List[str]` - Primary recipient list
- `cc_emails: List[str]` - CC recipient list
- `bcc_emails: List[str]` - BCC recipient list
- `attachments: List[Path]` - Optional file attachments
- `log_sent: bool` - Enable detailed logging

#### Functionality:
1. Composes EmailMessage object with all components
2. Validates and attaches files with automatic MIME type detection
3. Establishes SMTP connection and sends email
4. Logs success/failure status with detailed information
5. Handles connection errors and retry logic

## Recipient Management

### `prepare_to_txt(base_path: Path) -> None`
Comprehensive recipient list preparation:
1. Adds newly filtered emails from inventory
2. Appends additional emails from `additional_to.txt`
3. Deduplicates the entire recipient list
4. Creates backup before modifications

## Main Execution Logic

### `send_email_from_folder()` Parameters:
- `base_folder: str` - Directory containing all email files
- `dry_run: bool = False` - Enable test mode (sends only to approvers)
- `batch_size: int = 500` - Number of emails per batch
- `delay: int = 5` - Seconds to wait between batches
- `attachments_folder: str = None` - Custom attachment directory

### Execution Flow:
1. **Validation Phase**: Checks for required files and validates content
2. **Preparation Phase**: Reads email components and prepares recipient lists
3. **Dry Run Mode**: Sends test email to approvers only
4. **Batch Processing**: Sends emails in configured batches with delays
5. **Logging**: Records all activities and errors

## Command-Line Interface

### Usage
```bash
python notifybot.py <base_folder> [OPTIONS]
```

### Arguments
- `base_folder` - **Required**: Directory containing email files

### Options
- `--dry-run` - Send draft to approvers only (no actual email distribution)
- `--batch-size <number>` - Emails per batch (default: 500)
- `--delay <seconds>` - Delay between batches (default: 5)
- `--attachments-folder <path>` - Custom attachment directory

### Examples
```bash
# Regular email sending
python notifybot.py /path/to/email/folder

# Dry run with custom batch size
python notifybot.py /path/to/email/folder --dry-run --batch-size 100

# Custom delay and attachments
python notifybot.py /path/to/email/folder --delay 10 --attachments-folder /path/to/attachments
```

## Required File Structure

### Base Folder Contents
```
email_folder/
├── from.txt          # Sender email address
├── subject.txt       # Email subject line
├── body.html         # HTML email body
├── approver.txt      # Approver emails (for dry run)
├── to.txt            # Primary recipient list
├── cc.txt            # CC recipient list (optional)
├── bcc.txt           # BCC recipient list (optional)
├── additional_to.txt # Additional recipients (optional)
├── filter.txt        # Filtering conditions (optional)
├── inventory.csv     # Source data for filtering (optional)
└── attachments/      # Attachment files (optional)
```

## Error Handling and Logging

### Logging Features
- Comprehensive activity logging to `notifybot.log`
- Timestamp tracking for all operations
- Error categorization and detailed error messages
- Function-level tracking with line numbers

### Error Handling
- Custom exception for missing required files
- SMTP connection error handling
- File I/O error management
- Email validation error reporting
- Graceful failure recovery

## Best Practices

### Performance Optimization
- Use appropriate batch sizes to avoid server overload
- Implement delays between batches for server stability
- Monitor log files for performance issues

### Security Considerations
- Validate all email addresses before sending
- Use secure SMTP connections
- Implement proper error handling to avoid information leakage
- Regular backup of important files

### Maintenance
- Regular log file rotation and cleanup
- Periodic validation of email lists
- Monitor for bounced emails and update lists accordingly
- Test with dry run mode before production sends
