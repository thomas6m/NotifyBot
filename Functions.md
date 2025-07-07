# NotifyBot Step-by-Step Documentation

## 1. Log File Management

### `rotate_log_file()`
**Purpose:** Prevents the main log file from growing too large by renaming it with a timestamp.

**Input:** None

**Process:**
- Checks if `notifybot.log` exists
- If yes, renames it to `notifybot_YYYYMMDD_HHMMSS.log` using current datetime
- Logs or prints success/failure message

**Output:** Log file renamed if it exists, else no action

### `setup_logging()`
**Purpose:** Sets up the logging system for the script.

**Input:** None

**Process:**
- Configures logging to write INFO and above level messages to `notifybot.log`
- Format includes timestamp, log level, function name, line number, and message

**Output:** Logging ready for script-wide use

## 2. Logging & Console Output

### `log_and_print(level: str, message: str)`
**Purpose:** Logs a message at a specified level and prints it on the console with color for visibility.

**Input:**
- `level`: One of "info", "warning", "error"
- `message`: The text message to log and print

**Process:**
- Uses color codes for terminal output based on level
- Logs message using Python's logging module at appropriate level
- Prints colored message on terminal

**Output:** Colored console output and logged message

## 3. Email Validation

### `is_valid_email(email: str) -> bool`
**Purpose:** Validates the syntax of an email address.

**Input:**
- `email`: String email address to validate

**Process:**
- Uses `email_validator` package to validate email
- Catches and returns False if invalid

**Output:** Boolean: True if valid, False otherwise

## 4. File Reading

### `read_file(path: Path) -> str`
**Purpose:** Reads entire content of a file safely.

**Input:**
- `path`: Path object pointing to the file

**Process:**
- Opens file with UTF-8 encoding
- Reads all text and strips whitespace
- Logs error and returns empty string on failure

**Output:** Content of the file as a string or empty string on error

## 5. Email Extraction & Processing

### `extract_emails(raw: str, delimiters: str = ";") -> List[str]`
**Purpose:** Extract multiple emails from a string using delimiters.

**Input:**
- `raw`: String containing multiple emails separated by delimiters
- `delimiters`: Delimiter characters (default `;`)

**Process:**
- Uses regex splitting on delimiters
- Strips and filters out empty parts

**Output:** List of email strings

### `read_recipients(path: Path, delimiters: str = ";") -> List[str]`
**Purpose:** Reads recipient emails from a file and validates them.

**Input:**
- `path`: Path to recipients file
- `delimiters`: Delimiters separating emails in file

**Process:**
- Checks if file exists
- Reads line by line
- Extracts emails using `extract_emails()`
- Validates each using `is_valid_email()`
- Logs warnings for invalid emails

**Output:** List of validated email strings

### `write_to_txt(emails: List[str], path: Path) -> None`
**Purpose:** Appends emails to a text file.

**Input:**
- `emails`: List of emails to append
- `path`: Path to the file

**Process:**
- Opens file in append mode with UTF-8 encoding
- Writes each email on a new line
- Logs success or failure

**Output:** Appended emails to file

### `deduplicate_file(path: Path) -> None`
**Purpose:** Removes duplicate lines from a file safely.

**Input:**
- `path`: Path to the file

**Process:**
- Creates timestamped backup copy of the original file
- Reads all lines, removes duplicates preserving order
- Writes back unique lines to the original file
- Logs success or errors

**Output:** File updated with unique lines only

## 6. File Existence Validation

### `check_required_files(base: Path, required: List[str]) -> None`
**Purpose:** Ensures required files exist before proceeding.

**Input:**
- `base`: Base folder Path
- `required`: List of required filenames

**Process:**
- Checks existence of each file inside base
- Collects missing files
- Logs error and raises `MissingRequiredFilesError` if any are missing

**Output:** None, but raises exception if missing files found

## 7. Filter File Parsing

### `parse_filter_file(filter_path: Path) -> Tuple[List[str], List[Dict[str, str]]]`
**Purpose:** Reads filter rules from a CSV file.

**Input:**
- `filter_path`: Path to `filter.txt`

**Process:**
- Reads CSV as dictionaries
- Returns headers and list of row dicts
- Adds default values for missing keys like "mode" and "regex_flags"

**Output:** Tuple: (headers_list, rows_list_of_dicts)

## 8. Matching Conditions

### `match_condition(actual: str, expected: str, mode: str = "exact", regex_flags: str = "") -> bool`
**Purpose:** Matches a value against a condition with multiple modes.

**Input:**
- `actual`: The value to test
- `expected`: The expected pattern/value
- `mode`: One of "exact", "contains", or "regex"
- `regex_flags`: Optional regex flags like "IGNORECASE"

**Process:**
- For "exact", compares case-insensitively
- For "contains", checks substring ignoring case
- For "regex", applies regex with flags, logs invalid regex errors

**Output:** Boolean indicating if actual matches expected

## 9. Filtered Emails Retrieval

### `get_filtered_emailids(base: Path, delimiters: str = ";") -> List[str]`
**Purpose:** Extracts emails from inventory filtered by conditions in `filter.txt`.

**Input:**
- `base`: Base folder containing `inventory.csv` and `filter.txt`
- `delimiters`: Delimiters used to separate emails

**Process:**
- Parses filters from `filter.txt`
- Reads `inventory.csv` row-by-row
- Applies all filter conditions using `match_condition()`
- Collects emails from matching rows
- Removes those already in `to.txt`
- Validates emails before returning

**Output:** List of new filtered valid emails

## 10. Filename Sanitization

### `sanitize_filename(filename: str) -> str`
**Purpose:** Converts filenames to safe ASCII-only strings for attachments.

**Input:**
- `filename`: Original filename string

**Process:**
- Normalizes Unicode to ASCII (removes accents)
- Replaces unsafe characters with underscores
- Defaults to "attachment" if result empty

**Output:** Sanitized filename string

## 11. Email Sending

### `send_email(recipients: List[str], subject: str, body: str, attachments: List[Path], smtp_server: str = "localhost", dry_run: bool = False) -> None`
**Purpose:** Sends an email with subject, body, and attachments.

**Input:**
- `recipients`: List of email addresses
- `subject`: Email subject line
- `body`: Email body content
- `attachments`: List of file paths to attach
- `smtp_server`: SMTP server address (default localhost)
- `dry_run`: If True, do not actually send the email

**Process:**
- Constructs an `EmailMessage`
- Attaches files smaller than 15MB
- Sanitizes attachment filenames
- Sends email through SMTP unless dry_run is True
- Logs actions and warnings

**Output:** Email sent or dry-run simulated

## 12. Main Orchestrator

### `send_email_from_folder(base_folder: str, dry_run: bool = False, batch_size: int = 10, retries: int = 3, delay: int = 3) -> None`
**Purpose:** Coordinates all steps to send emails based on folder contents.

**Input:**
- `base_folder`: Folder with `body.txt`, `subject.txt`, `to.txt`, attachments, etc.
- `dry_run`: Do not actually send emails (default False)
- `batch_size`: Number of recipients per batch email (default 10)
- `retries`: Number of retries if sending fails (default 3)
- `delay`: Seconds to wait between retries (default 3)

**Process:**
- Rotates logs and sets up logging
- Validates required files exist
- Reads subject and body content
- Reads recipients from `to.txt`
- Fetches filtered emails from inventory and filter files, updates `to.txt`
- Loads attachments
- Sends emails in batches, retrying on failure with delays
- Logs progress and errors

**Output:** Emails sent in batches, or simulated in dry-run mode

## Summary

This documentation breaks down the NotifyBot workflow into these key components:

1. **Log rotation & setup** - Manages log files and configures logging
2. **Logging and console output** - Provides colored terminal output and file logging
3. **Email validation & extraction** - Validates email syntax and extracts from strings
4. **File reading/writing & deduplication** - Handles file operations safely
5. **Filter parsing & matching** - Processes filter rules and applies conditions
6. **Building recipient lists** - Dynamically creates email recipient lists
7. **Sanitizing filenames for attachments** - Ensures safe attachment handling
8. **Sending emails with retry and batch support** - Delivers emails reliably
9. **Orchestration of all steps** - Coordinates the entire process from folder-based inputs

The system is designed to be modular, reliable, and easy to debug through comprehensive logging and error handling.
