# NotifyBot Python Script - Line by Line Explanation

## Script Header and Documentation (Lines 1-25)

**Line 1:** `#!/usr/bin/env python3`
- Shebang line that tells the system to use Python 3 interpreter when executing this script directly

**Lines 2-25:** Multi-line docstring
- Comprehensive documentation explaining what NotifyBot does: automated email batch sending
- Shows usage examples with different command-line options
- Lists all CLI options and their purposes
- Explains the required file structure inside the base folder

## Import Statements (Lines 27-44)

**Lines 27-44:** Import all necessary modules
- `argparse`: For parsing command-line arguments
- `csv`: For reading CSV files (inventory data)
- `logging`: For structured logging to files
- `mimetypes`: For detecting file types for email attachments
- `re`: For regular expressions (email validation, filename sanitization)
- `shutil`: For file operations like copying
- `sys`: For system operations and exit codes
- `time`: For delays between email batches
- `traceback`: For detailed error reporting
- `os`: For operating system interface
- `json`: For JSON data handling
- `datetime`: For timestamp operations
- `email.*` modules: For creating and formatting email messages
- `pathlib.Path`: For cross-platform file path handling
- `typing`: For type hints
- `subprocess`: For running external commands (sendmail)
- `email_validator`: For robust email address validation

## Path Configuration Constants (Lines 46-50)

**Line 46:** `NOTIFYBOT_ROOT = Path("/notifybot")`
- Sets the root directory for the entire NotifyBot system

**Line 47:** `BASEFOLDER_PATH = NOTIFYBOT_ROOT / "basefolder"`
- Defines where all email campaign folders must be located

**Line 48:** `LOG_FILENAME = NOTIFYBOT_ROOT / "logs" / "notifybot.log"`
- Specifies the location for log files

**Line 49:** `INVENTORY_PATH = NOTIFYBOT_ROOT / "inventory" / "inventory.csv"`
- Sets the location of the main inventory CSV file used for filtering

## Custom Exception Class (Lines 51-53)

**Lines 51-53:** `class MissingRequiredFilesError(Exception):`
- Creates a custom exception for when required input files are missing
- Makes error handling more specific and informative

## Base Folder Validation Function (Lines 55-66)

**Line 55:** `def validate_base_folder(base_folder: str) -> Path:`
- Function to ensure the base folder is valid and secure

**Line 57:** `base_folder_path = BASEFOLDER_PATH / base_folder`
- Constructs the full path by combining the base path with user input

**Lines 60-61:** Security check
- Ensures the folder exists and is actually a directory
- Prevents path traversal attacks by restricting to basefolder location

**Line 65:** `return base_folder_path`
- Returns the validated Path object

## CSV Logging Utility (Lines 68-76)

**Line 68:** `def csv_log_entry(message: str) -> str:`
- Creates structured log entries in CSV format for better parsing

**Line 70:** `timestamp_epoch = int(time.time())`
- Gets current Unix timestamp for precise timing

**Lines 71-75:** Username detection
- Tries to get the current user's username
- Has fallback logic for different operating systems and environments

**Line 76:** Returns formatted CSV entry with timestamp, user, and message

## Logging Setup Function (Lines 78-110)

**Line 78:** `def setup_logging() -> None:`
- Configures the logging system for the entire application

**Lines 80-81:** `LOG_FILENAME.parent.mkdir(parents=True, exist_ok=True)`
- Creates the log directory if it doesn't exist

**Lines 84-90:** `logging.basicConfig(...)`
- Configures Python's logging system to write to file
- Sets INFO level and custom format

**Lines 92-110:** `def log_and_print(level: str, message: str) -> None:`
- Nested function that both logs to file and prints to console
- Uses emoji mapping for different log levels (info=ℹ️, error=❌, etc.)
- Makes the function available globally for use throughout the script

## Sendmail Path Detection (Lines 112-134)

**Line 112:** `def find_sendmail_path() -> str:`
- Locates the sendmail executable on the system

**Lines 114-120:** `common_paths = [...]`
- Lists typical locations where sendmail might be installed

**Lines 122-125:** Check each common path
- Iterates through known locations and returns first found

**Lines 128-133:** Fallback using `which` command
- Uses system's `which` command to find sendmail in PATH
- Has error handling in case `which` fails

**Line 135:** Returns default fallback path if nothing found

## Email Validation Function (Lines 136-158)

**Line 136:** `def is_valid_email(email: str) -> bool:`
- Comprehensive email validation with sendmail compatibility

**Lines 138-139:** `validate_email(email.strip(), check_deliverability=False)`
- Uses the email_validator library for RFC-compliant validation
- Strips whitespace and skips deliverability checks for speed

**Lines 142-146:** Length validation
- Checks RFC 5321 limit of 320 characters
- Logs warning for overly long emails

**Lines 149-154:** Character safety check
- Identifies characters that might cause issues with sendmail
- Prevents command injection through malicious email addresses

**Lines 156-158:** Error handling
- Catches validation errors and logs them appropriately

## File Reading Utility (Lines 160-167)

**Line 160:** `def read_file(path: Path) -> str:`
- Safely reads text files with error handling

**Lines 162-163:** `return path.read_text(encoding="utf-8").strip()`
- Reads file content using UTF-8 encoding and removes whitespace

**Lines 164-167:** Exception handling
- Logs errors and returns empty string if file read fails

## Email Parsing Functions (Lines 169-189)

**Lines 169-173:** `def extract_emails(raw: str, delimiters: str = ";") -> List[str]:`
- Parses email addresses from delimited strings
- Uses regex to split on semicolons or other delimiters
- Returns clean list of email addresses

**Lines 175-189:** `def read_recipients(path: Path, delimiters: str = ";") -> List[str]:`
- Reads and validates emails from files
- Processes each line and validates each email
- Logs warnings for invalid emails but continues processing
- Has comprehensive error handling

## Recipient File Writing (Lines 191-215)

**Line 191:** `def write_recipients_to_file(path: Path, recipients: List[str]) -> None:`
- Writes recipient lists to files with deduplication

**Lines 194-202:** Deduplication logic
- Uses case-insensitive comparison to remove duplicates
- Preserves original casing and order

**Lines 204-207:** File writing
- Writes one email per line in UTF-8 encoding

**Lines 209-215:** Logging and error handling
- Reports how many duplicates were removed
- Logs success and handles write errors

## Recipient Merging Function (Lines 217-237)

**Line 217:** `def merge_recipients(base_recipients: List[str], additional_recipients: List[str]) -> List[str]:`
- Merges two email lists while removing duplicates

**Lines 219-221:** Initialize tracking
- Uses set for O(1) lookup of seen emails
- Maintains order with separate list

**Lines 224-229:** Process base recipients first
- Adds base recipients while tracking seen emails

**Lines 232-237:** Add additional recipients
- Only adds recipients not already seen
- Maintains order preference (base first, then additional)

## File Deduplication Function (Lines 239-258)

**Line 239:** `def deduplicate_file(path: Path) -> None:`
- Creates backup and removes duplicate lines from files

**Lines 242-245:** Backup creation
- Creates timestamped backup before modifying original
- Uses current datetime in filename

**Lines 247-253:** Deduplication process
- Reads all lines and tracks unique ones
- Preserves order of first occurrence

**Lines 255-258:** Write back and error handling
- Overwrites original file with deduplicated content
- Comprehensive error logging

## Required Files Validation (Lines 260-275)

**Line 260:** `def check_required_files(base: Path, required: List[str], dry_run: bool = True) -> None:`
- Ensures all necessary files exist before processing

**Lines 262-264:** Basic file existence check
- Verifies all required files are present
- Raises custom exception if any are missing

**Lines 266-275:** Recipient source validation for live mode
- In live mode, ensures at least one recipient source exists
- Checks for to.txt, filter.txt+inventory.csv, or additional_to.txt
- Prevents accidentally sending emails without recipients

## Filename Sanitization (Lines 277-280)

**Line 277:** `def sanitize_filename(filename: str) -> str:`
- Cleans filenames for safe attachment handling

**Line 280:** Uses regex to remove problematic characters
- Keeps only word characters, spaces, dots, and hyphens
- Prevents security issues with malicious filenames

## Email Attachment Handling (Lines 282-307)

**Line 282:** `def add_attachments(msg: MIMEMultipart, attachment_folder: Path) -> None:`
- Adds all files from attachment folder to email

**Lines 284-286:** Folder validation
- Checks if attachment folder exists before processing

**Lines 289-291:** File iteration
- Processes each file in the attachment folder

**Lines 293-297:** MIME type detection
- Automatically detects file types for proper email formatting
- Falls back to binary octet-stream if type unknown

**Lines 299-307:** Attachment creation and error handling
- Creates proper MIME attachment with headers
- Sanitizes filename for security
- Logs each attachment and handles errors gracefully

## Email Message Creation (Lines 309-325)

**Line 309:** `def create_email_message(...) -> MIMEMultipart:`
- Creates properly formatted email messages with attachments

**Lines 312-316:** Message structure setup
- Creates multipart message container
- Sets From, To, and Subject headers
- Handles multiple recipients properly

**Lines 318-320:** HTML body attachment
- Adds HTML content as properly formatted MIME part
- Uses UTF-8 encoding for international character support

**Lines 322-325:** Attachment integration
- Calls attachment function if folder provided
- Returns complete message object

## Sendmail Email Sending (Lines 327-387)

**Line 327:** `def send_via_sendmail(...) -> bool:`
- Core function for sending emails via system sendmail

**Lines 330-340:** Dry run handling
- Logs what would be sent without actually sending
- Shows recipients, subject, and attachment info
- Returns success without doing anything

**Lines 343-346:** Message preparation
- Creates properly formatted email message
- Converts to string format for sendmail

**Lines 348-351:** Sendmail command setup
- Finds sendmail executable path
- Constructs command with proper arguments
- Includes sender and recipient information

**Lines 353-359:** Process execution
- Uses subprocess to call sendmail
- Sets up proper input/output pipes
- Includes timeout for safety

**Lines 361-378:** Result handling and error cases
- Checks return code for success/failure
- Handles various error conditions (not found, timeout, etc.)
- Provides detailed error logging

## Batch Email Sending (Lines 389-424)

**Line 389:** `def send_email_batch(...) -> None:`
- Manages sending emails in batches with delays

**Lines 393-396:** Initialization
- Sets up counters for successful and failed batches
- Logs start of batch processing

**Lines 398-401:** Batch iteration
- Splits recipients into chunks of batch_size
- Calculates batch numbers for progress tracking

**Lines 403-404:** Progress logging
- Shows current batch progress with recipient count

**Lines 407-413:** Individual batch processing
- Calls sendmail function for each batch
- Tracks success/failure rates
- Logs results for each batch

**Lines 416-419:** Inter-batch delay
- Waits specified time between batches (except last)
- Only delays in live mode, not dry runs

**Lines 422-424:** Final summary
- Reports overall success/failure statistics
- Provides completion confirmation

## Legacy Compatibility Function (Lines 426-430)

**Lines 426-430:** `def send_email(...)`
- Maintains backward compatibility with older code
- Routes to the sendmail implementation
- Placeholder for attachment folder (set in main)

## Filter Logic Application (Lines 432-458)

**Line 432:** `def apply_filter_logic(filters: List[str], inventory_path: Path) -> List[str]:`
- Applies filtering rules to inventory CSV data

**Lines 435-439:** Inventory file validation
- Checks if inventory file exists
- Returns empty list if not found

**Lines 442-444:** CSV processing setup
- Opens inventory file with proper encoding
- Creates CSV reader with headers

**Lines 446-452:** Row-by-row filtering
- Applies filter conditions to each row
- Extracts and validates email addresses
- Logs warnings for invalid data

**Lines 454-458:** Results and error handling
- Logs how many recipients were selected
- Handles any processing errors gracefully

## Filter Condition Matching (Lines 460-484)

**Line 460:** `def matches_filter_conditions(row: Dict, filters: List[str]) -> bool:`
- Determines if a CSV row matches filter criteria

**Lines 462-466:** Filter preprocessing
- Skips empty lines and comments (starting with #)
- Processes each filter condition

**Lines 468-477:** Key=value filter format
- Supports simple key=value matching
- Case-insensitive comparison
- Returns false if any condition fails

**Lines 479-484:** Substring search fallback
- If not key=value format, does substring search
- Searches all row values for filter text
- Returns true only if all conditions match

## User Confirmation (Lines 486-489)

**Lines 486-489:** `def prompt_for_confirmation() -> bool:`
- Asks user to confirm before sending emails
- Only accepts explicit "yes" response
- Prevents accidental email sending

## Main Function - Argument Parsing (Lines 491-500)

**Lines 491-500:** Command-line argument setup
- Creates argument parser with description
- Defines all CLI options (base-folder, dry-run, force, etc.)
- Sets default values for batch-size and delay

## Main Function - Initialization (Lines 502-508)

**Lines 502-508:** Setup and validation
- Parses command-line arguments
- Sets up logging system
- Begins try-catch block for error handling

## Main Function - File Validation (Lines 510-514)

**Lines 510-514:** Input validation
- Validates base folder path
- Checks for required files based on mode
- Uses custom exception for missing files

## Main Function - Content Reading (Lines 516-521)

**Lines 516-521:** Email content loading
- Reads subject, body, from address, and approver emails
- Uses helper functions with error handling
- Loads all required email components

## Main Function - Content Validation (Lines 523-532)

**Lines 523-532:** Essential content validation
- Ensures subject and body are not empty
- Validates from address format
- Exits with error code if validation fails

## Main Function - Recipient Loading Logic (Lines 534-597)

**Lines 534-540:** Recipient source setup
- Initializes empty recipient list
- Sets up paths for different recipient sources
- Prepares for priority-based loading

**Lines 542-555:** Priority 1: to.txt processing
- Loads recipients from to.txt if it exists
- Merges with additional_to.txt if available
- Logs recipient counts and merge statistics

**Lines 557-577:** Priority 2: Filter logic
- Uses filter.txt and inventory.csv if to.txt missing
- Applies filtering to select recipients
- Merges with additional recipients
- Creates to.txt for future reference

**Lines 579-587:** Priority 3: Additional only
- Uses additional_to.txt as last resort
- Creates to.txt from additional file
- Ensures consistent file structure

**Lines 589-597:** Dry-run fallback and validation
- Uses approver emails for dry runs
- Ensures at least some recipients exist
- Exits with error if no recipients found

## Main Function - Final Preparations (Lines 599-627)

**Lines 599-602:** Recipient validation
- Final check that recipients list is not empty
- Exits with error if no valid recipients

**Lines 604-611:** Attachment folder setup
- Checks for attachment folder existence
- Counts available attachments
- Sets up for email attachment processing

**Lines 613-621:** Email summary display
- Shows comprehensive email campaign summary
- Includes all key details (from, subject, recipients, etc.)
- Displays mode (dry-run vs live)

**Lines 623-627:** User confirmation
- Prompts for confirmation unless --force used
- Allows user to abort before sending
- Prevents accidental email campaigns

## Main Function - Email Execution (Lines 629-641)

**Lines 629-641:** Email sending execution
- Calls batch sending function with all parameters
- Includes all configuration options
- Logs successful completion

## Main Function - Error Handling (Lines 643-656)

**Lines 643-656:** Comprehensive error handling
- Handles missing files error specifically
- Catches validation errors
- Handles keyboard interrupts gracefully
- Provides detailed error logging and stack traces
- Exits with appropriate error codes

## Script Entry Point (Lines 658-659)

**Lines 658-659:** Standard Python entry point
- Ensures main() only runs when script executed directly
- Prevents execution when imported as module

## Summary

This NotifyBot script is a production-ready email automation system with:

- **Security**: Path validation, email sanitization, filename cleaning
- **Reliability**: Comprehensive error handling, logging, dry-run mode
- **Flexibility**: Multiple recipient sources, filtering, batching
- **Usability**: Clear documentation, progress tracking, confirmation prompts
- **Maintainability**: Type hints, structured logging, modular functions

The script handles everything from basic email sending to complex filtering and batch processing, making it suitable for large-scale email campaigns while maintaining safety and reliability.
