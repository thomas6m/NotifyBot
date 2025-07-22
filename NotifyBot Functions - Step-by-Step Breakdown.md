# NotifyBot Functions - Step-by-Step Breakdown

## Configuration & Validation Functions

### `validate_base_folder(base_folder: str) -> Path`
**Purpose**: Ensures the base folder is valid and within the allowed directory structure.

**Steps**:
1. Constructs full path by joining `BASEFOLDER_PATH` with provided `base_folder`
2. Checks if the resulting path is an existing directory
3. Raises `ValueError` if directory doesn't exist
4. Returns validated `Path` object if successful

### `csv_log_entry(message: str) -> str`
**Purpose**: Creates structured CSV log entries with timestamp and username.

**Steps**:
1. Gets current timestamp in milliseconds (`time.time_ns() // 1_000_000`)
2. Attempts to get current username using `os.getlogin()`
3. Falls back to environment variables (`USER`, `USERNAME`) if `getlogin()` fails
4. Returns formatted CSV string: `"timestamp,username,message"`

### `setup_logging() -> None`
**Purpose**: Configures logging system and creates the global `log_and_print` function.

**Steps**:
1. Creates log directory if it doesn't exist
2. Configures Python logging to write to `LOG_FILENAME`
3. Sets format to raw message (for CSV structure)
4. Creates inner function `log_and_print(level, message)` that:
   - Maps log levels to emojis (info=ℹ️, warning=⚠️, error=❌, etc.)
   - Formats message with emoji
   - Creates CSV log entry using `csv_log_entry()`
   - Logs to file and prints to console
5. Makes `log_and_print` available globally

## Email Validation & Processing Functions

### `find_sendmail_path() -> str`
**Purpose**: Locates the sendmail executable on the system.

**Steps**:
1. Checks common sendmail locations:
   - `/usr/sbin/sendmail`
   - `/usr/bin/sendmail` 
   - `/sbin/sendmail`
   - `/usr/lib/sendmail`
2. If not found, tries `which sendmail` command
3. Logs warning if not found in standard locations
4. Returns found path or default fallback `/usr/sbin/sendmail`

### `is_valid_email(email: str) -> bool`
**Purpose**: Validates email addresses for syntax and sendmail compatibility.

**Steps**:
1. Strips whitespace from email
2. Uses `email_validator.validate_email()` with `check_deliverability=False`
3. Additional sendmail compatibility checks:
   - Length must be ≤320 characters (RFC 5321 limit)
   - Must not contain problematic characters: `|`, `` ` ``, `$`, `\`
4. Logs warnings/errors for invalid emails
5. Returns `True` if valid, `False` otherwise

### `read_file(path: Path) -> str`
**Purpose**: Safely reads text files with error handling.

**Steps**:
1. Attempts to read file using UTF-8 encoding
2. Strips whitespace from content
3. Logs error if file reading fails
4. Returns file content or empty string on error

### `extract_emails(raw: str, delimiters: str = ";") -> List[str]`
**Purpose**: Parses email addresses from delimited strings.

**Steps**:
1. Returns empty list if input is empty
2. Uses regex to split by specified delimiters (default semicolon)
3. Strips whitespace from each email
4. Filters out empty strings
5. Returns list of cleaned email addresses

### `read_recipients(path: Path, delimiters: str = ";") -> List[str]`
**Purpose**: Reads and validates email addresses from files.

**Steps**:
1. Checks if file exists, logs warning and returns empty list if not
2. Reads file line by line
3. For each line:
   - Strips whitespace
   - Extracts emails using `extract_emails()`
   - Validates each email using `is_valid_email()`
   - Adds valid emails to result list
   - Logs warnings for invalid emails
4. Logs errors if file processing fails
5. Returns list of valid email addresses

## Recipient Management Functions

### `write_recipients_to_file(path: Path, recipients: List[str]) -> None`
**Purpose**: Writes email lists to files with deduplication.

**Steps**:
1. Creates case-insensitive deduplication:
   - Uses set to track lowercase versions
   - Preserves original case of first occurrence
2. Writes unique recipients to file (one per line)
3. Logs information about duplicates removed
4. Logs file creation success
5. Handles and logs any write errors

### `merge_recipients(base_recipients: List[str], additional_recipients: List[str]) -> List[str]`
**Purpose**: Combines two email lists while removing duplicates and preserving order.

**Steps**:
1. Creates case-insensitive tracking set
2. Adds base recipients first (preserving order)
3. Adds additional recipients that haven't been seen
4. Returns merged list with duplicates removed

### `deduplicate_file(path: Path) -> None`
**Purpose**: Removes duplicate lines from files with backup creation.

**Steps**:
1. Checks if file exists, returns early if not
2. Creates timestamped backup file using `shutil.copy2()`
3. Reads all lines from original file
4. Deduplicates using set (preserves first occurrence)
5. Writes deduplicated content back to original file
6. Logs backup creation and deduplication success
7. Handles and logs any errors

### `check_required_files(base: Path, required: List[str], dry_run: bool = True) -> None`
**Purpose**: Validates that all required files exist and recipient sources are available.

**Steps**:
1. Checks for missing required files from the `required` list
2. Raises `MissingRequiredFilesError` if any required files are missing
3. In non-dry-run mode, validates recipient sources:
   - Checks for `to.txt`
   - Checks for filter setup (`filter.txt` + `inventory.csv`)
   - Checks for `additional_to.txt`, `cc.txt`, `bcc.txt`
4. Raises error if no valid recipient source found in live mode

## Filtering & Logic Functions

### `matches_filter_conditions(row: Dict, filters: List[str]) -> bool`
**Purpose**: Implements complex filtering logic with wildcard support.

**Steps**:
1. Returns `True` if no filters provided
2. For each filter line (OR conditions):
   - Skips empty lines and comments (starting with #)
   - Splits line into comma-separated AND conditions
   - For each AND condition:
     - If format is `key=value`: matches row[key] against value pattern
     - If no `=`: searches pattern in all row values
     - Uses `fnmatch.fnmatch()` for Unix shell-style wildcards
   - Returns `True` if all AND conditions in line match
3. Returns `False` if no OR conditions matched

**Wildcard Support**:
- `*` matches any sequence of characters
- `?` matches any single character  
- `[seq]` matches any character in seq
- `[!seq]` matches any character not in seq

### `apply_filter_logic(filters: List[str], inventory_path: Path) -> List[str]`
**Purpose**: Applies filtering to CSV inventory and extracts matching emails.

**Steps**:
1. Initializes empty result list
2. Checks if inventory file exists
3. Opens CSV file using `csv.DictReader`
4. For each row:
   - Applies `matches_filter_conditions()`
   - If row matches:
     - Extracts emails from 'email' column
     - Handles semicolon-separated emails using `extract_emails()`
     - Validates each email using `is_valid_email()`
     - Adds valid emails to result
5. Logs filtering results and any errors
6. Returns list of filtered email addresses

## Email Creation & Embedding Functions

### `sanitize_filename(filename: str) -> str`
**Purpose**: Cleans filenames for safe attachment handling.

**Steps**:
1. Uses regex to remove all characters except word characters, spaces, dots, and hyphens
2. Pattern: `r"[^\w\s.-]"` replaced with empty string
3. Returns sanitized filename

### `add_attachments(msg: MIMEMultipart, attachment_folder: Path) -> None`
**Purpose**: Adds all files from attachment folder to email message.

**Steps**:
1. Returns early if attachment folder doesn't exist
2. Iterates through all files in attachment folder
3. For each file:
   - Determines MIME type using `mimetypes.guess_type()`
   - Defaults to `application/octet-stream` if unknown
   - Splits MIME type into main/sub types
   - Reads file in binary mode
   - Creates `MIMEBase` object with appropriate type
   - Encodes content using base64
   - Adds Content-Disposition header with sanitized filename
   - Attaches to main message
4. Logs successful attachments and any errors

### `embed_images_in_html(html_content: str, base_folder: Path) -> Tuple[str, List[MIMEImage]]`
**Purpose**: Converts image references to embedded images with CID references.

**Steps**:
1. Locates images folder within base folder
2. Returns original content if no images folder exists
3. Uses regex to find all `<img>` tags with `src` attributes
4. For each image:
   - Skips if already using `cid:` reference
   - Warns about external URLs but leaves them unchanged
   - Locates local image file in images folder
   - Reads image data in binary mode
   - Determines MIME type
   - Creates unique Content-ID
   - Creates `MIMEImage` object with proper headers
   - Replaces `src` attribute with `cid:` reference
   - Adds to embedded images list
5. Returns modified HTML and list of embedded images

### `create_email_message(...)` 
**Purpose**: Creates properly formatted MIME email with all components.

**Steps**:
1. Embeds images if base folder provided
2. Creates `MIMEMultipart` message:
   - Uses 'related' type if embedded images exist
   - Uses 'mixed' type for attachments only
3. Sets email headers:
   - From, To, CC (BCC intentionally omitted from headers)
   - Subject
4. Handles content structure:
   - If embedded images: creates alternative part for HTML, attaches images to main
   - If no embedded images: attaches HTML directly
5. Adds attachments if folder provided
6. Returns complete `MIMEMultipart` message

## Email Sending Functions

### `send_via_sendmail(...)`
**Purpose**: Core email sending function using sendmail command.

**Steps**:
1. **Dry-run mode preparation**:
   - Adds "DRAFT" prefix to subject if not present
   - Creates HTML info box showing original recipient counts
   - Logs draft mode details
2. **Live mode preparation**:
   - Logs live mode recipient details
   - Shows attachment information
3. **Message creation**:
   - Calls `create_email_message()` with all parameters
   - Converts message to string format
4. **Sendmail execution**:
   - Finds sendmail path using `find_sendmail_path()`
   - Combines all recipients (TO + CC + BCC) for delivery
   - Constructs sendmail command: `[sendmail_path, '-f', from_address] + all_recipients`
   - Executes via `subprocess.Popen` with 60-second timeout
   - Passes email content to stdin
5. **Result handling**:
   - Checks return code
   - Logs success or error messages
   - Returns boolean success indicator

### `send_email_batch(...)`
**Purpose**: Manages batch sending with CC/BCC handling and progress tracking.

**Steps**:
1. **Initialization**:
   - Calculates total recipients and batch count
   - Initializes success/failure counters
2. **Edge case handling**:
   - If no TO recipients but CC/BCC exist, sends single email
3. **Batch processing**:
   - Splits TO recipients into batches
   - For each batch:
     - Includes CC/BCC only with first batch (prevents duplicates)
     - Calls `send_via_sendmail()` for current batch
     - Tracks success/failure
     - Adds delay between batches (except last)
4. **Progress logging**:
   - Logs each batch processing start
   - Logs success/failure for each batch
   - Shows final summary with totals

## Main Execution Function

### `main()`
**Purpose**: Orchestrates the entire email sending process.

**Steps**:
1. **Argument parsing**:
   - Parses command line arguments
   - Validates required parameters
2. **Setup and validation**:
   - Calls `setup_logging()`
   - Validates base folder using `validate_base_folder()`
   - Checks required files using `check_required_files()`
3. **Content loading**:
   - Reads email subject, body, from address, approvers
   - Reads optional CC/BCC recipients
   - Validates essential content (subject, body, from address, approvers)
4. **Recipient determination**:
   - **Dry-run mode**: Uses approvers only, counts original recipients for display
   - **Live mode**: Determines actual recipients using priority system:
     - Priority 1: `to.txt` (with optional `additional_to.txt` merge)
     - Priority 2: Filter logic + optional additional
     - Priority 3: `additional_to.txt` only
5. **Attachment handling**:
   - Checks for attachment folder
   - Counts and logs available attachments
6. **Confirmation and summary**:
   - Shows comprehensive email summary
   - Prompts for confirmation unless `--force` used
7. **Execution**:
   - Calls `send_email_batch()` with all parameters
   - Handles and logs any errors
   - Provides final success/failure status

## Utility & Helper Functions

### `prompt_for_confirmation() -> bool`
**Purpose**: Interactive confirmation prompt.

**Steps**:
1. Displays confirmation prompt
2. Reads user input and strips/converts to lowercase
3. Returns `True` only if response is exactly "yes"

### `send_email()` (Legacy)
**Purpose**: Backward compatibility wrapper.

**Steps**:
1. Maintained for backward compatibility
2. Routes to `send_via_sendmail()` with basic parameters
3. Used by older code that might call this function

## Error Handling & Logging

The script includes comprehensive error handling throughout:

- **File operations**: Try-catch blocks with detailed error logging
- **Email validation**: Multiple validation layers with warnings
- **Network operations**: Timeout handling for sendmail
- **User input**: Validation and sanitization
- **Process management**: Proper subprocess handling with cleanup

The logging system provides:
- **Structured CSV format**: Timestamp, username, emoji-prefixed messages
- **Multiple log levels**: Info, warning, error, success, processing, etc.
- **Console and file output**: Dual logging for real-time monitoring
- **Detailed tracking**: Every operation logged with context
