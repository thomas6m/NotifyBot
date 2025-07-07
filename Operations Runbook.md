# NotifyBot Email Sender - Step by Step Explanation

## Overview
NotifyBot is a Python-based email automation script designed for bulk email sending with advanced filtering, validation, and safety features. It supports dry-run testing, batch processing, and comprehensive logging.

## Key Features
- **Flexible Filtering**: Supports exact, contains, and regex matching
- **Email Validation**: Validates all email addresses before sending
- **Batch Processing**: Sends emails in configurable batches with delays
- **Log Rotation**: Automatically rotates log files with timestamps
- **Dry Run Mode**: Test mode that sends only to approvers
- **Attachment Support**: Handles file attachments with size limits
- **Deduplication**: Removes duplicate email addresses

## Step-by-Step Execution Flow

### 1. **Initialization Phase**
```
./notifybot.py /path/to/email/folder [options]
```
- **Log Rotation**: Renames existing `notifybot.log` to `notifybot_YYYYMMDD_HHMMSS.log`
- **Logging Setup**: Configures new logging with detailed format including function names and line numbers
- **Argument Parsing**: Processes command line arguments for folder path and options

### 2. **File Validation Phase**
The script checks for required files in the specified folder:
- `from.txt` - Sender email address
- `subject.txt` - Email subject line
- `body.html` - HTML email body content
- `approver.txt` - List of approver email addresses

**If any required files are missing, the script exits with an error.**

### 3. **Content Loading Phase**
- **Read Core Files**: Loads sender email, subject, and HTML body
- **Load Approvers**: Reads and validates approver email addresses
- **Validation**: Ensures all core content is present and valid

### 4. **Recipient Preparation Phase**

#### 4.1 **Inventory Filtering** (if `to.txt` doesn't exist)
- **Read Filter Configuration**: Parses `filter.txt` (CSV format with field, value, mode columns)
- **Process Inventory**: Reads `inventory.csv` and applies filters
- **Flexible Matching**: Supports three matching modes:
  - `exact`: Case-insensitive exact match
  - `contains`: Substring matching
  - `regex`: Regular expression matching
- **Extract Emails**: Collects email addresses from matching records
- **Validation**: Validates extracted email addresses

#### 4.2 **Additional Recipients**
- **Load Additional**: Reads `additional_to.txt` for extra recipients
- **Append to Main List**: Adds to the main recipient list

#### 4.3 **Deduplication**
- **Backup Creation**: Creates timestamped backup of `to.txt`
- **Remove Duplicates**: Eliminates duplicate email addresses
- **Update File**: Writes clean recipient list back to `to.txt`

### 5. **Dry Run Mode** (if `--dry-run` flag is used)
- **Test Email**: Sends email with "[DRAFT]" prefix to approvers only
- **No Attachments**: Skips attachment processing in dry run
- **Validation**: Allows testing of email content and formatting
- **Exit**: Terminates after sending test email

### 6. **Production Sending Phase**

#### 6.1 **Recipient List Preparation**
- **Load Recipients**: Reads final recipient lists from:
  - `to.txt` (main recipients)
  - `cc.txt` (carbon copy recipients)
  - `bcc.txt` (blind carbon copy recipients)
- **Final Validation**: Validates all email addresses

#### 6.2 **Attachment Processing**
- **Scan Attachments Folder**: Looks for files in `attachments/` directory
- **Size Validation**: Checks file sizes against maximum limit (default 10MB)
- **MIME Type Detection**: Automatically detects file types
- **Attachment Preparation**: Prepares files for email attachment

#### 6.3 **Batch Processing**
- **Batch Division**: Splits recipient list into configurable batches (default 500)
- **Sequential Sending**: Processes batches one at a time
- **Delay Management**: Waits between batches (default 5 seconds)
- **Error Handling**: Continues processing even if individual batches fail

### 7. **Email Composition and Sending**

#### 7.1 **Message Construction**
- **Headers**: Sets From, To, Cc, Subject headers
- **Multi-part Content**: Creates both plain text and HTML versions
- **Attachment Integration**: Adds validated attachments to message

#### 7.2 **SMTP Delivery**
- **Local SMTP**: Connects to localhost SMTP server
- **Batch Transmission**: Sends to all recipients (To, Cc, Bcc)
- **Error Handling**: Logs and reports any delivery failures

### 8. **Logging and Monitoring**

#### 8.1 **Comprehensive Logging**
- **Function-level Tracking**: Logs function names and line numbers
- **Error Reporting**: Detailed error messages with context
- **Success Tracking**: Records successful operations
- **Performance Metrics**: Tracks timing and batch statistics

#### 8.2 **Console Output**
- **Color-coded Messages**: Uses ANSI colors for different message types
- **Progress Indicators**: Shows batch processing progress
- **Summary Statistics**: Final report with sent count, errors, and duration

## File Structure Requirements

```
email_folder/
├── from.txt              # Sender email (required)
├── subject.txt           # Email subject (required)
├── body.html            # HTML email body (required)
├── approver.txt         # Approver emails (required)
├── to.txt               # Main recipients (auto-generated)
├── cc.txt               # CC recipients (optional)
├── bcc.txt              # BCC recipients (optional)
├── additional_to.txt    # Extra recipients (optional)
├── inventory.csv        # Data source for filtering (optional)
├── filter.txt           # Filter configuration (optional)
└── attachments/         # Attachment files (optional)
```

## Filter Configuration Format

The `filter.txt` file uses CSV format with these columns:
- **field**: Column name in inventory.csv
- **value**: Value to match against
- **mode**: Matching mode (exact/contains/regex)

Example:
```csv
field,value,mode
department,Engineering,exact
status,active,contains
email,.*@company\.com,regex
```

## Command Line Options

```bash
# Basic usage
./notifybot.py /path/to/email/folder

# Dry run mode
./notifybot.py /path/to/email/folder --dry-run

# Custom batch size and delay
./notifybot.py /path/to/email/folder --batch-size 100 --delay 10

# Custom attachment settings
./notifybot.py /path/to/email/folder --attachments-folder /custom/path --max-attachment-size 5
```

## Safety Features

1. **Email Validation**: All email addresses are validated before sending
2. **Dry Run Testing**: Test emails before production sending
3. **Batch Processing**: Prevents overwhelming mail servers
4. **File Backups**: Creates backups before modifying files
5. **Error Isolation**: Batch failures don't stop entire process
6. **Attachment Limits**: Prevents oversized attachments
7. **Comprehensive Logging**: Full audit trail of all operations

## Error Handling

The script includes robust error handling for:
- Missing or invalid files
- Invalid email addresses
- SMTP connection failures
- Attachment processing errors
- File I/O operations
- Regex compilation errors

All errors are logged with detailed context and many display user-friendly console messages with color coding for easy identification.
