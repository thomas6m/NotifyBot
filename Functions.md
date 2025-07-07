# NotifyBot Functions Documentation

## File and Logging Functions

### `rotate_log_file()`
**Purpose:** Rotates the log file by renaming the current log file with a timestamp suffix.

**How:** If notifybot.log exists, rename it to something like notifybot_20250707_120000.log.

**Why:** Prevents the log file from growing indefinitely and helps keep historical logs.

### `setup_logging()`
**Purpose:** Configures the Python logging module.

**How:** Sets up logging to write INFO-level and above logs to notifybot.log with timestamps, function name, and line number.

**Why:** Provides consistent, timestamped logs for debugging and monitoring.

### `log_and_print(level: str, message: str)`
**Purpose:** Logs a message at a specified level and prints it to the console with color coding.

**How:** Supports 'info' (blue), 'warning' (yellow), and 'error' (red) with colored output and logs to file.

**Why:** Makes logs visible in terminal and keeps a permanent record in the log file.

## Email and File Utilities

### `is_valid_email(email: str) -> bool`
**Purpose:** Validates an email address using the email_validator library.

**How:** Returns True if the email is syntactically valid, False otherwise.

**Why:** Ensures only correctly formatted emails are processed.

### `read_file(path: Path) -> str`
**Purpose:** Reads the entire content of a text file and strips whitespace.

**How:** Opens file with UTF-8 encoding, reads, strips, and returns content.

**Why:** Simplifies file reading and error handling in one place.

### `extract_emails(raw: str, delimiters: str = ";") -> List[str]`
**Purpose:** Splits a string by specified delimiters and returns a list of trimmed email strings.

**How:** Uses regex to split by any delimiter character (like ; or ,) and filters out empty parts.

**Why:** Handles multiple emails in one string separated by various delimiters.

### `read_recipients(path: Path, delimiters: str = ";") -> List[str]`
**Purpose:** Reads emails from a file, validates them, and returns a list of valid emails.

**How:** For each line, splits emails by delimiters, validates each, logs warnings on invalids.

**Why:** Safely loads recipient emails from files, skipping malformed or invalid addresses.

### `write_to_txt(emails: List[str], path: Path) -> None`
**Purpose:** Appends a list of emails to a text file.

**How:** Opens the file in append mode and writes one email per line.

**Why:** Used to update recipient lists dynamically.

### `deduplicate_file(path: Path) -> None`
**Purpose:** Removes duplicate lines in a text file, backing it up first.

**How:** Copies original file with timestamp, reads all lines, filters duplicates, writes back.

**Why:** Keeps recipient or email lists clean without duplicates.

### `check_required_files(base: Path, required: List[str]) -> None`
**Purpose:** Checks if required files exist in a folder.

**How:** Checks each filename and raises a custom exception if any missing.

**Why:** Ensures program prerequisites are met before continuing.

## Filter and Matching Functions

### `parse_filter_file(filter_path: Path) -> Tuple[List[str], List[Dict[str, str]]]`
**Purpose:** Parses a CSV filter file (filter.txt) and returns headers and rows.

**How:** Reads CSV into dictionaries, sets defaults for missing fields like "mode", "regex_flags".

**Why:** Processes filter criteria to be applied to inventory.

### `match_condition(actual: str, expected: str, mode: str = "exact", regex_flags: str = "") -> bool`
**Purpose:** Compares two strings based on matching mode: exact, contains, or regex.

**How:**
- **Exact:** case-insensitive equality.
- **Contains:** substring check (case-insensitive).
- **Regex:** regex match with optional flags like IGNORECASE.

**Why:** Flexible matching for filtering inventory entries.

### `get_filtered_emailids(base: Path, delimiters: str = ";") -> List[str]`
**Purpose:** Retrieves filtered email addresses from inventory.csv matching conditions in filter.txt.

**How:** Reads filters, applies all to each inventory row, collects matching emails, excludes existing recipients, validates emails.

**Why:** Dynamically build recipient lists based on inventory data and filter rules.

## Email Sending Functions

### `sanitize_filename(filename: str) -> str`
**Purpose:** Cleans filenames for attachment safety, converting to ASCII and replacing unsafe characters.

**How:** Unicode normalization, ASCII encoding ignoring errors, regex replacing non-word characters with _.

**Why:** Avoids problems with non-ASCII or unsafe characters in email attachments.

### `send_email(recipients: List[str], subject: str, body: str, attachments: List[Path], smtp_server: str = "localhost", dry_run: bool = False) -> None`
**Purpose:** Sends an email with subject, body, and attachments to multiple recipients.

**How:**
- Prepares an EmailMessage object.
- Checks attachment sizes (<15MB), sanitizes filenames.
- Supports dry-run mode (doesn't actually send).
- Sends email via SMTP server.

**Why:** Core function to deliver notification emails with attachments.

### `send_email_from_folder(base_folder: str, dry_run: bool = False, batch_size: int = 10, retries: int = 3, delay: int = 3) -> None`
**Purpose:** Orchestrates the entire process: read inputs from a folder, prepare recipients, batch emails, and send.

**How:**
- Rotates logs and sets up logging.
- Checks required files.
- Reads subject, body, recipients.
- Adds filtered recipients, deduplicates.
- Loads attachments.
- Sends emails in batches with retry logic.

**Why:** Entry point that ties all other functions together to automate email notification sending.
