# NotifyBot Email Automation Script - Complete Analysis

## Overview
NotifyBot is a comprehensive email batch sender that supports filtering, logging, dry-run testing, and attachment handling. It's designed for automated email campaigns with robust error handling and safety features.

## Core Architecture

### Path Configuration Constants
```python
NOTIFYBOT_ROOT = Path("/notifybot")
BASEFOLDER_PATH = NOTIFYBOT_ROOT / "basefolder"
LOG_FILENAME = NOTIFYBOT_ROOT / "logs" / "notifybot.log"
INVENTORY_PATH = NOTIFYBOT_ROOT / "inventory" / "inventory.csv"
```
These define the fixed directory structure that NotifyBot expects.

## Function-by-Function Analysis

### 1. Directory Validation
```python
def validate_base_folder(base_folder: str) -> Path:
```
**Purpose**: Security function that ensures the base folder is within the allowed `/notifybot/basefolder` directory.
- Prevents path traversal attacks
- Returns validated Path object
- Raises ValueError if folder is outside allowed area

### 2. Logging Infrastructure

#### CSV Log Entry Generation
```python
def csv_log_entry(message: str) -> str:
```
**Purpose**: Creates structured log entries in CSV format with timestamp and user information.
- Uses epoch timestamp for consistency
- Captures the executing user's username
- Handles cases where username detection fails

#### Logging Setup
```python
def setup_logging() -> None:
```
**Purpose**: Configures the logging system and creates a colored logging function.
- Sets up file logging to `/notifybot/logs/notifybot.log`
- Creates `log_and_print()` function with emoji-based level indicators
- Logs to both file and console simultaneously

#### Log Rotation
```python
def rotate_log_file() -> None:
```
**Purpose**: Archives current log file with timestamp before starting new session.
- Prevents log files from growing indefinitely
- Creates timestamped backups
- Handles rotation errors gracefully

### 3. Email Infrastructure

#### Sendmail Discovery
```python
def find_sendmail_path() -> str:
```
**Purpose**: Locates the sendmail executable on the system.
- Checks common installation paths
- Falls back to PATH search using `which`
- Returns default path if not found

#### Email Validation
```python
def is_valid_email(email: str) -> bool:
```
**Purpose**: Validates email addresses for syntax and sendmail compatibility.
- Uses `email_validator` library for RFC compliance
- Checks for 320-character limit (RFC 5321)
- Filters out characters that could cause sendmail issues (`|`, `\``, `$`, `\\`)

### 4. File Operations

#### Safe File Reading
```python
def read_file(path: Path) -> str:
```
**Purpose**: Safely reads text files with error handling.
- Uses UTF-8 encoding
- Strips whitespace
- Returns empty string on errors (doesn't crash the program)

#### Email Extraction
```python
def extract_emails(raw: str, delimiters: str = ";") -> List[str]:
```
**Purpose**: Parses email addresses from delimited strings.
- Default delimiter is semicolon
- Uses regex to split on multiple delimiter types
- Strips whitespace from each email

#### Recipient File Processing
```python
def read_recipients(path: Path, delimiters: str = ";") -> List[str]:
```
**Purpose**: Reads and validates email addresses from files.
- Processes multi-line files
- Validates each email address
- Logs invalid emails but continues processing

#### Recipient File Writing
```python
def write_recipients_to_file(path: Path, recipients: List[str]) -> None:
```
**Purpose**: Writes recipient lists to files for future reference.
- One email per line format
- UTF-8 encoding
- Error handling with logging

### 5. Data Processing

#### Recipient Merging
```python
def merge_recipients(base_recipients: List[str], additional_recipients: List[str]) -> List[str]:
```
**Purpose**: Combines recipient lists while removing duplicates.
- Case-insensitive duplicate detection
- Preserves original order
- Maintains first occurrence of duplicates

#### File Deduplication
```python
def deduplicate_file(path: Path) -> None:
```
**Purpose**: Removes duplicate lines from files with backup creation.
- Creates timestamped backup before modification
- Preserves line order
- Removes empty lines

### 6. File Validation

#### Required Files Check
```python
def check_required_files(base: Path, required: List[str], dry_run: bool = True) -> None:
```
**Purpose**: Ensures all necessary files exist before proceeding.
- Checks basic required files (subject, body, from, approver)
- In live mode, ensures at least one recipient source exists
- Raises `MissingRequiredFilesError` for missing files

### 7. Email Composition and Sending

#### Filename Sanitization
```python
def sanitize_filename(filename: str) -> str:
```
**Purpose**: Cleans filenames for safe attachment handling.
- Removes special characters that could cause issues
- Preserves alphanumeric, spaces, dots, and hyphens

#### Attachment Processing
```python
def add_attachments(msg: MIMEMultipart, attachment_folder: Path) -> None:
```
**Purpose**: Adds all files from attachment folder to email.
- Auto-detects MIME types
- Uses base64 encoding for binary safety
- Handles various file types
- Logs each attachment added

#### Email Message Creation
```python
def create_email_message(recipients: List[str], subject: str, body_html: str, 
                        from_address: str, attachment_folder: Path = None) -> MIMEMultipart:
```
**Purpose**: Creates properly formatted MIME email messages.
- Creates multipart message for HTML + attachments
- Sets proper headers (From, To, Subject)
- Attaches HTML body and files
- Returns complete email object

#### Email Sending via Sendmail
```python
def send_via_sendmail(recipients: List[str], subject: str, body_html: str, 
                     from_address: str, attachment_folder: Path = None, 
                     dry_run: bool = False) -> bool:
```
**Purpose**: Core email sending function using system sendmail.
- **Dry-run mode**: Logs what would be sent without actually sending
- **Live mode**: Uses subprocess to call sendmail with proper arguments
- Handles sendmail timeouts (60 seconds)
- Returns success/failure status

#### Batch Email Processing
```python
def send_email_batch(recipients: List[str], subject: str, body_html: str, 
                    from_address: str, batch_size: int, dry_run: bool = False, 
                    delay: float = 5.0, attachment_folder: Path = None) -> None:
```
**Purpose**: Manages batch sending with rate limiting.
- Splits recipients into configurable batch sizes
- Adds delays between batches to avoid overwhelming mail server
- Tracks successful/failed batches
- Provides progress logging

### 8. Filtering System

#### Filter Application
```python
def apply_filter_logic(filters: List[str], inventory_path: Path) -> List[str]:
```
**Purpose**: Applies filtering rules to CSV inventory data.
- Reads CSV inventory file
- Applies filter conditions to select recipients
- Returns list of matching email addresses
- Handles CSV reading errors gracefully

#### Filter Condition Matching
```python
def matches_filter_conditions(row: Dict, filters: List[str]) -> bool:
```
**Purpose**: Evaluates whether a CSV row matches filter criteria.
- Supports `key=value` format filters
- Supports substring search across all fields
- Ignores empty lines and comments (starting with #)
- Uses case-insensitive matching

### 9. User Interaction

#### Confirmation Prompt
```python
def prompt_for_confirmation() -> bool:
```
**Purpose**: Interactive safety check before sending emails.
- Requires explicit "yes" to proceed
- Prevents accidental sends
- Can be bypassed with `--force` flag

## Main Program Logic

The `main()` function orchestrates the entire process:

### 1. **Argument Parsing**
- Parses command-line arguments for configuration
- Required: `--base-folder`
- Optional: `--dry-run`, `--force`, `--batch-size`, `--delay`

### 2. **Initialization**
- Sets up logging system
- Rotates previous log file
- Validates base folder path

### 3. **File Validation**
- Checks for required files (subject.txt, body.html, from.txt, approver.txt)
- Validates content isn't empty
- Ensures valid from address

### 4. **Recipient Resolution** (Priority System)
The script uses a sophisticated priority system for determining recipients:

**Priority 1**: `to.txt` file
- If `to.txt` exists, uses it as primary source
- Optionally merges with `additional_to.txt` if present

**Priority 2**: Filter logic
- If `to.txt` doesn't exist but `filter.txt` and `inventory.csv` do
- Applies filters to inventory data
- Optionally merges with `additional_to.txt`
- Creates `to.txt` with results for future reference

**Priority 3**: Additional recipients only
- Uses only `additional_to.txt` if nothing else available
- Creates `to.txt` from this source

**Fallback**: Approver emails for dry-run mode

### 5. **Attachment Detection**
- Looks for `attachment/` folder in base directory
- Counts available attachments
- Sets up attachment processing

### 6. **Summary and Confirmation**
- Displays email configuration summary
- Shows recipient count, batch settings, and mode
- Prompts for confirmation (unless `--force` used)

### 7. **Email Execution**
- Calls batch sending function with all parameters
- Handles interruptions and errors
- Logs completion status

## Key Features

### Safety Mechanisms
- **Dry-run mode**: Test without sending
- **Confirmation prompts**: Prevent accidents
- **Input validation**: Email format, file existence
- **Path validation**: Prevent directory traversal
- **Batch limits**: Prevent mail server overwhelming

### Robustness Features
- **Comprehensive logging**: CSV format with timestamps
- **Error handling**: Graceful failure handling
- **File backups**: Before modifications
- **Duplicate handling**: Automatic deduplication
- **Multiple recipient sources**: Flexible input methods

### Operational Features
- **Batch processing**: Configurable batch sizes
- **Rate limiting**: Delays between batches
- **Attachment support**: Automatic MIME handling
- **Filter system**: CSV-based recipient selection
- **Progress tracking**: Batch-by-batch status

## Usage Patterns

### Basic Usage
```bash
# Dry run test
python notifybot.py --base-folder campaign1 --dry-run

# Live sending with confirmation
python notifybot.py --base-folder campaign1

# Automated sending (no prompts)
python notifybot.py --base-folder campaign1 --force --batch-size 100 --delay 10
```

### File Structure Required
```
/notifybot/basefolder/campaign1/
├── subject.txt          # Email subject line
├── body.html           # Email body (HTML format)
├── from.txt            # Sender email address
├── approver.txt        # Approver emails (for dry-run)
├── to.txt              # Direct recipient list (optional)
├── additional_to.txt   # Additional recipients (optional)
├── filter.txt          # Filter conditions (optional)
└── attachment/         # Attachment files (optional)
    ├── document1.pdf
    └── image1.png
```

