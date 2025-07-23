# NotifyBot Functions Explained

## 1. MissingRequiredFilesError

```python
class MissingRequiredFilesError(Exception):
    """Exception raised when required input files are missing."""
```

**Line-by-line explanation:**
- **Line 1**: Defines a custom exception class that inherits from Python's built-in `Exception` class
- **Line 2**: Provides a docstring explaining that this exception is raised when required input files are missing from the base folder
- **Purpose**: This custom exception allows the program to handle missing file scenarios specifically, making error handling more precise and user-friendly

---

## 2. validate_base_folder

```python
def validate_base_folder(base_folder: str) -> Path:
    """Ensure that the base folder is a valid relative path inside /notifybot/basefolder"""
    base_folder_path = BASEFOLDER_PATH / base_folder
    
    # Ensure the base folder is inside /notifybot/basefolder
    if not base_folder_path.is_dir():
        raise ValueError(f"Invalid base folder: {base_folder}. It must be a directory inside '/notifybot/basefolder'.")

    # Return the validated path
    return base_folder_path
```

**Line-by-line explanation:**
- **Line 1**: Function signature that takes a string `base_folder` parameter and returns a `Path` object
- **Line 2**: Docstring explaining the function's purpose - to validate the base folder path
- **Line 3**: Creates a full path by combining `BASEFOLDER_PATH` (which is `/notifybot/basefolder`) with the provided `base_folder` string
- **Line 4**: Empty line for readability
- **Line 5**: Comment explaining the validation check
- **Line 6**: Checks if the constructed path exists and is a directory using `is_dir()` method
- **Line 7**: If the directory doesn't exist, raises a `ValueError` with a descriptive error message
- **Line 8**: Empty line for readability
- **Line 9**: Comment indicating the return statement
- **Line 10**: Returns the validated `Path` object if all checks pass

---

## 3. csv_log_entry

```python
def csv_log_entry(message: str) -> str:
    """Generate log entry in CSV format."""
    timestamp_epoch = time.time_ns() // 1_000_000  # Nanoseconds to milliseconds
    try:
        username = os.getlogin()  # Get the username of the executor
    except OSError:
        # Fallback for environments where getlogin() fails
        username = os.getenv('USER', os.getenv('USERNAME', 'unknown'))
    return f"{timestamp_epoch},{username},{message}"
```

**Line-by-line explanation:**
- **Line 1**: Function signature taking a string `message` and returning a formatted string
- **Line 2**: Docstring explaining the function generates CSV-formatted log entries
- **Line 3**: Gets current time in nanoseconds using `time.time_ns()`, then converts to milliseconds by integer division
- **Line 4**: Begins a try block to handle potential exceptions when getting username
- **Line 5**: Attempts to get the current user's login name using `os.getlogin()`
- **Line 6**: Catches `OSError` which can occur in some environments (like containers or SSH sessions)
- **Line 7**: Comment explaining this is a fallback mechanism
- **Line 8**: Uses environment variables as fallback: first tries 'USER', then 'USERNAME', finally defaults to 'unknown'
- **Line 9**: Returns a CSV-formatted string with timestamp, username, and message separated by commas

---

## 4. setup_logging

```python
def setup_logging() -> None:
    """Configure logging to INFO+ level in LOG_FILENAME with structured CSV format."""
    # Ensure log directory exists
    LOG_FILENAME.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        filename=LOG_FILENAME,
        level=logging.INFO,
        format='%(message)s',
        filemode='a'
    )
    
    def log_and_print(level: str, message: str) -> None:
        """Log and color-print a message at INFO/WARNING/ERROR levels in CSV format."""
        # Emoji mappings for log levels
        emoji_mapping = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
            "processing": "⏳",
            "backup": "💾",
            "file": "📂",
            "confirmation": "✋",
            "draft": "📝"
        }

        # Get emoji for level
        emoji = emoji_mapping.get(level.lower(), "")
        csv_log = csv_log_entry(f"{emoji} {message}")
        log_func = getattr(logging, level.lower(), logging.info)
        log_func(csv_log)
        print(f"{csv_log}")  # Print to the console as well

    globals()['log_and_print'] = log_and_print
```

**Line-by-line explanation:**
- **Line 1**: Function signature with no parameters and no return value
- **Line 2**: Docstring explaining the logging configuration purpose
- **Line 3**: Comment about ensuring log directory exists
- **Line 4**: Creates the parent directory of the log file if it doesn't exist (`parents=True` creates intermediate directories, `exist_ok=True` doesn't raise error if directory exists)
- **Line 5**: Empty line for readability
- **Line 6**: Comment about configuring logging
- **Lines 7-11**: Configures Python's logging system with:
  - `filename`: Specifies the log file path
  - `level`: Sets minimum logging level to INFO
  - `format`: Uses only the message (no timestamp/level prefixes since CSV format handles this)
  - `filemode`: Appends to existing log file rather than overwriting
- **Line 12**: Empty line for readability
- **Line 13**: Defines an inner function for enhanced logging functionality
- **Line 14**: Docstring for the inner function
- **Line 15**: Comment about emoji mappings
- **Lines 16-26**: Dictionary mapping log levels to corresponding emojis for visual identification
- **Line 27**: Empty line for readability
- **Line 28**: Comment about getting emoji
- **Line 29**: Retrieves emoji for the given level, defaults to empty string if level not found
- **Line 30**: Creates CSV log entry by combining emoji and message
- **Line 31**: Gets the appropriate logging function (info, warning, error, etc.) using `getattr`, defaults to `logging.info`
- **Line 32**: Calls the logging function with the CSV-formatted message
- **Line 33**: Also prints the message to console for immediate feedback
- **Line 34**: Empty line for readability
- **Line 35**: Makes the inner function available globally so other parts of the program can use it

---

## 5. find_sendmail_path

```python
def find_sendmail_path() -> str:
    """Find sendmail executable path."""
    common_paths = [
        '/usr/sbin/sendmail',
        '/usr/bin/sendmail',
        '/sbin/sendmail',
        '/usr/lib/sendmail'
    ]
    
    for path in common_paths:
        if Path(path).exists():
            return path
    
    # Try to find in PATH
    try:
        result = subprocess.run(['which', 'sendmail'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    log_and_print("warning", "Sendmail not found in common locations")
    return '/usr/sbin/sendmail'  # Default fallback
```

**Line-by-line explanation:**
- **Line 1**: Function signature returning a string path to sendmail executable
- **Line 2**: Docstring explaining the function's purpose
- **Lines 3-8**: List of common locations where sendmail is typically installed on Linux/Unix systems
- **Line 9**: Empty line for readability
- **Line 10**: Begins loop through each common path
- **Line 11**: Checks if the path exists using `Path(path).exists()`
- **Line 12**: Returns the first valid path found
- **Line 13**: Empty line for readability
- **Line 14**: Comment explaining the fallback search in system PATH
- **Line 15**: Begins try block to handle potential exceptions
- **Line 16**: Runs the `which` command to search for sendmail in system PATH, capturing output
- **Line 17**: Checks if the command succeeded (return code 0 means success)
- **Line 18**: Returns the path found by `which`, stripped of whitespace
- **Line 19**: Catches any exception that might occur during the subprocess call
- **Line 20**: Does nothing on exception (silent fail)
- **Line 21**: Empty line for readability
- **Line 22**: Logs a warning that sendmail wasn't found in expected locations
- **Line 23**: Returns a default fallback path (most common location) even if not verified to exist
---

## 6. `is_valid_email(email: str) -> bool`

```python
def is_valid_email(email: str) -> bool:
    """Check email syntax using email_validator with sendmail compatibility."""
```
- **Line 1**: Function definition with type hints: takes string, returns boolean
- **Line 2**: Docstring explains the function's purpose

```python
    try:
        validate_email(email.strip(), check_deliverability=False)
```
- **Line 3**: Start try block for error handling
- **Line 4**: Call `validate_email()` from email_validator library
  - `email.strip()` removes whitespace before validation
  - `check_deliverability=False` skips DNS/SMTP checks (syntax only)

```python
        # Additional checks for sendmail compatibility
        email = email.strip()
```
- **Line 5**: Comment explains these are sendmail-specific checks
- **Line 6**: Strip whitespace again and store in local variable

```python
        if len(email) > 320:  # RFC 5321 limit
            log_and_print("warning", f"Email too long (>320 chars): {email}")
            return False
```
- **Line 7**: Check if email exceeds 320 character limit from RFC 5321
- **Line 8**: If too long, log warning with the problematic email
- **Line 9**: Return False (invalid)

```python
        # Check for characters that might cause issues with sendmail
        problematic_chars = ['|', '`', '$', '\\']
```
- **Line 10**: Comment explaining character safety check
- **Line 11**: Define list of characters that could break sendmail commands
  - These characters could be used for command injection

```python
        if any(char in email for char in problematic_chars):
            log_and_print("warning", f"Email contains potentially problematic characters: {email}")
            return False
```
- **Line 12**: Use `any()` to check if email contains any problematic characters
- **Line 13**: If found, log warning and return False
- **Line 14**: Return False (invalid)

```python
        return True
```
- **Line 15**: If all checks pass, return True (valid email)

```python
    except EmailNotValidError as exc:
        log_and_print("error", f"Invalid email format: {email}. Error: {exc}")
        return False
```
- **Line 16**: Catch validation errors from email_validator library
- **Line 17**: Log the error with the invalid email and specific error message
- **Line 18**: Return False (invalid)

---

## 7. `read_file(path: Path) -> str`

```python
def read_file(path: Path) -> str:
    """Read text file content and strip, or log an error."""
```
- **Line 1**: Function definition: takes Path object, returns string
- **Line 2**: Docstring explains it reads and strips content

```python
    try:
        return path.read_text(encoding="utf-8").strip()
```
- **Line 3**: Try to read file using Path's `read_text()` method
- **Line 4**: 
  - Specify UTF-8 encoding explicitly
  - Strip whitespace from beginning and end
  - Return the cleaned content

```python
    except Exception as exc:
        log_and_print("error", f"Failed to read {path}: {exc}")
        return ""
```
- **Line 5**: Catch any exception that occurs during file reading
- **Line 6**: Log error with file path and exception details
- **Line 7**: Return empty string as fallback

---

## 8. `extract_emails(raw: str, delimiters: str = ";") -> List[str]`

```python
def extract_emails(raw: str, delimiters: str = ";") -> List[str]:
    """Split and trim emails from a raw string by delimiters."""
```
- **Line 1**: Function definition with default delimiter of semicolon
  - Takes raw string and optional delimiters, returns list of strings
- **Line 2**: Docstring explains the function's purpose

```python
    if not raw:
        return []
```
- **Line 3**: Check if input string is empty or None
- **Line 4**: Return empty list immediately if no input

```python
    return [e.strip() for e in re.split(f"[{re.escape(delimiters)}]", raw) if e.strip()]
```
- **Line 5**: Use list comprehension to process split results
  - `re.split(f"[{re.escape(delimiters)}]", raw)`: 
    - Create regex pattern with escaped delimiters in character class
    - Split the raw string by any of the delimiter characters
  - `e.strip()` for each split result: remove whitespace
  - `if e.strip()`: only include non-empty results after stripping
  - Return list of cleaned email strings

---

## 9. `read_recipients(path: Path, delimiters: str = ";") -> List[str]`

```python
def read_recipients(path: Path, delimiters: str = ";") -> List[str]:
    """Read and validate emails from a file (semicolon-separated)."""
```
- **Line 1**: Function definition with default semicolon delimiter
- **Line 2**: Docstring explains it reads and validates emails

```python
    valid = []
```
- **Line 3**: Initialize empty list to store valid emails

```python
    if not path.is_file():
        log_and_print("warning", f"{path.name} missing, skipping.")
        return valid
```
- **Line 4**: Check if path exists and is a file
- **Line 5**: If not, log warning with filename and return empty list
- **Line 6**: Return empty list (early exit)

```python
    try:
```
- **Line 7**: Start try block for file processing errors

```python
        for line in path.read_text(encoding="utf-8").splitlines():
```
- **Line 8**: 
  - Read entire file with UTF-8 encoding
  - Split into individual lines
  - Iterate through each line

```python
            for email in extract_emails(line.strip(), delimiters):
```
- **Line 9**: 
  - Strip whitespace from current line
  - Use `extract_emails()` to split line by delimiters
  - Iterate through each extracted email

```python
                if is_valid_email(email):
                    valid.append(email)
```
- **Line 10**: Validate each email using `is_valid_email()`
- **Line 11**: If valid, add to the valid list

```python
                else:
                    log_and_print("warning", f"Invalid email skipped: {email}")
```
- **Line 12**: If invalid, continue to else block
- **Line 13**: Log warning with the problematic email

```python
    except Exception as exc:
        log_and_print("error", f"Error processing recipients in {path}: {exc}")
```
- **Line 14**: Catch any file processing errors
- **Line 15**: Log error with file path and exception details

```python
    return valid
```
- **Line 16**: Return list of validated emails

---

## 10. `write_recipients_to_file(path: Path, recipients: List[str]) -> None`

```python
def write_recipients_to_file(path: Path, recipients: List[str]) -> None:
    """Write recipients list to a file, one per line, with deduplication."""
```
- **Line 1**: Function definition: takes Path and list, returns nothing
- **Line 2**: Docstring explains writing with deduplication

```python
    try:
```
- **Line 3**: Start try block for error handling

```python
        # Deduplicate recipients (case-insensitive)
        seen = set()
        unique_recipients = []
```
- **Line 4**: Comment explains case-insensitive deduplication
- **Line 5**: Initialize empty set to track seen emails (lowercase)
- **Line 6**: Initialize empty list for unique recipients (original case)

```python
        for email in recipients:
            email_lower = email.lower()
```
- **Line 7**: Iterate through input recipients
- **Line 8**: Convert current email to lowercase for comparison

```python
            if email_lower not in seen:
                seen.add(email_lower)
                unique_recipients.append(email)
```
- **Line 9**: Check if lowercase version hasn't been seen
- **Line 10**: If unique, add lowercase to seen set
- **Line 11**: Add original case email to unique list

```python
        with path.open('w', encoding='utf-8') as f:
```
- **Line 12**: 
  - Open file for writing with UTF-8 encoding
  - Use context manager for proper file handling

```python
            for email in unique_recipients:
                f.write(f"{email}\n")
```
- **Line 13**: Write each unique email to file
- **Line 14**: Add newline after each email

```python
        if len(recipients) != len(unique_recipients):
            duplicates_removed = len(recipients) - len(unique_recipients)
            log_and_print("info", f"Removed {duplicates_removed} duplicate email(s)")
```
- **Line 15**: Compare original and unique list lengths
- **Line 16**: Calculate number of duplicates removed
- **Line 17**: Log info about duplicates if any were found

```python
        log_and_print("file", f"Written {len(unique_recipients)} unique recipients to {path.name}")
```
- **Line 18**: Log successful write with count and filename

```python
    except Exception as exc:
        log_and_print("error", f"Error writing recipients to {path}: {exc}")
```
- **Line 19**: Catch any file writing errors
- **Line 20**: Log error with path and exception details

---

## 11. `merge_recipients(base_recipients: List[str], additional_recipients: List[str]) -> List[str]`

```python
def merge_recipients(base_recipients: List[str], additional_recipients: List[str]) -> List[str]:
    """Merge two lists of recipients, removing duplicates while preserving order."""
```
- **Line 1**: Function definition: takes two lists, returns one list
- **Line 2**: Docstring explains merging with deduplication and order preservation

```python
    # Use a set to track seen emails (case-insensitive)
    seen = set()
    merged = []
```
- **Line 3**: Comment explains case-insensitive tracking
- **Line 4**: Initialize set for tracking seen emails (lowercase)
- **Line 5**: Initialize list for merged results (original case)

```python
    # Add base recipients first
    for email in base_recipients:
```
- **Line 6**: Comment explains processing order
- **Line 7**: Iterate through base recipients first

```python
        email_lower = email.lower()
```
- **Line 8**: Convert current email to lowercase for comparison

```python
        if email_lower not in seen:
            seen.add(email_lower)
            merged.append(email)
```
- **Line 9**: Check if lowercase version hasn't been seen
- **Line 10**: If unique, add to seen set
- **Line 11**: Add original case email to merged list

```python
    # Add additional recipients
    for email in additional_recipients:
```
- **Line 12**: Comment explains second phase
- **Line 13**: Iterate through additional recipients

```python
        email_lower = email.lower()
```
- **Line 14**: Convert to lowercase for comparison

```python
        if email_lower not in seen:
            seen.add(email_lower)
            merged.append(email)
```
- **Line 15**: Same deduplication logic as base recipients
- **Line 16**: Only add if not already seen (to seen set)
- **Line 17**: Add to merged list if unique

```python
    return merged
```
- **Line 18**: Return the merged list with duplicates removed

---

## 12. `deduplicate_file(path: Path) -> None`

```python
def deduplicate_file(path: Path) -> None:
    """Back up and deduplicate a file's lines."""
```
- **Line 1**: Function definition: takes Path, returns nothing
- **Line 2**: Docstring explains backup and deduplication

```python
    if not path.is_file():
        return
```
- **Line 3**: Check if path exists and is a file
- **Line 4**: Exit early if file doesn't exist

```python
    try:
```
- **Line 5**: Start try block for error handling

```python
        backup = path.with_name(f"{path.stem}_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}")
```
- **Line 6**: Create backup filename using original path
  - `path.stem`: filename without extension
  - `datetime.now():%Y%m%d_%H%M%S`: timestamp format (YYYYMMDD_HHMMSS)
  - `path.suffix`: original file extension
  - Example: `file.txt` becomes `file_20240115_143022.txt`

```python
        shutil.copy2(path, backup)
```
- **Line 7**: Copy original file to backup location
  - `copy2` preserves metadata (timestamps, permissions)

```python
        log_and_print("backup", f"💾 Backup created: {backup.name}")
```
- **Line 8**: Log backup creation with emoji and backup filename

```python
        unique, seen = [], set()
```
- **Line 9**: 
  - Initialize empty list for unique lines
  - Initialize empty set for tracking seen lines

```python
        for line in path.read_text(encoding="utf-8").splitlines():
```
- **Line 10**: 
  - Read entire file with UTF-8 encoding
  - Split into individual lines
  - Iterate through each line

```python
            if line and line not in seen:
```
- **Line 11**: Check if line is not empty AND not previously seen
  - This preserves first occurrence of duplicates

```python
                seen.add(line)
                unique.append(line)
```
- **Line 12**: Add line to seen set for future duplicate detection
- **Line 13**: Add line to unique list for output

```python
        path.write_text("\n".join(unique) + "\n", encoding="utf-8")
```
- **Line 14**: 
  - Join unique lines with newlines
  - Add final newline at end of file
  - Write back to original file path with UTF-8 encoding

```python
        log_and_print("info", f"Deduplicated {path.name}")
```
- **Line 15**: Log successful deduplication with filename

```python
    except Exception as exc:
        log_and_print("error", f"Error during file deduplication for {path}: {exc}")
```
- **Line 16**: Catch any errors during the process
- **Line 17**: Log error with file path and exception details

---

## 13. check_required_files

```python
def check_required_files(base: Path, required: List[str], dry_run: bool = True) -> None:
    """Ensure required files exist. In real mode, ensure valid recipient source."""
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        raise MissingRequiredFilesError(f"Missing required files: {', '.join(missing)}")
    
    if not dry_run:
        has_to = (base / "to.txt").is_file()
        has_filters = (base / "filter.txt").is_file() and INVENTORY_PATH.is_file()
        has_additional = (base / "additional_to.txt").is_file()
        has_cc = (base / "cc.txt").is_file()
        has_bcc = (base / "bcc.txt").is_file()
        
        if not (has_to or has_filters or has_additional or has_cc or has_bcc):
            raise MissingRequiredFilesError(
                "Missing recipient source: Provide at least one of 'to.txt', 'filter.txt + inventory.csv', 'additional_to.txt', 'cc.txt', or 'bcc.txt'."
            )
```

**Line-by-line explanation:**
- **Line 1**: Function signature taking base Path, list of required files, and optional dry_run boolean
- **Line 2**: Docstring explaining the function validates required files and recipient sources
- **Line 3**: Creates list of missing files by checking if each required file exists in the base directory
- **Line 4**: Checks if any files are missing
- **Line 5**: Raises custom exception with comma-separated list of missing files
- **Line 6**: Empty line for readability
- **Line 7**: Only performs recipient validation if not in dry-run mode
- **Line 8**: Checks if "to.txt" file exists (direct recipient list)
- **Line 9**: Checks if both "filter.txt" and inventory.csv exist (filtered recipients)
- **Line 10**: Checks if "additional_to.txt" exists (supplementary recipients)
- **Line 11**: Checks if "cc.txt" exists (carbon copy recipients)
- **Line 12**: Checks if "bcc.txt" exists (blind carbon copy recipients)
- **Line 13**: Empty line for readability
- **Line 14**: Validates at least one recipient source exists
- **Lines 15-17**: Raises exception with detailed message about valid recipient sources

---

## 14. sanitize_filename

```python
def sanitize_filename(filename: str) -> str:
    """Sanitize the filename to prevent issues with special characters."""
    return re.sub(r"[^\w\s.-]", "", filename)
```

**Line-by-line explanation:**
- **Line 1**: Function signature taking filename string and returning sanitized string
- **Line 2**: Docstring explaining the function removes problematic characters
- **Line 3**: Uses regex substitution to remove all characters except:
  - `\w`: Word characters (letters, digits, underscore)
  - `\s`: Whitespace characters
  - `.`: Periods
  - `-`: Hyphens
  - All other characters are replaced with empty string

---

## 15. add_attachments

```python
def add_attachments(msg: MIMEMultipart, attachment_folder: Path) -> None:
    """Add all files from attachment folder to the email message."""
    if not attachment_folder or not attachment_folder.exists():
        return
        
    try:
        for file_path in attachment_folder.iterdir():
            if file_path.is_file():
                # Get MIME type
                ctype, encoding = mimetypes.guess_type(str(file_path))
                if ctype is None or encoding is not None:
                    ctype = 'application/octet-stream'
                
                maintype, subtype = ctype.split('/', 1)
                
                with open(file_path, 'rb') as fp:
                    attachment = MIMEBase(maintype, subtype)
                    attachment.set_payload(fp.read())
                    encoders.encode_base64(attachment)
                    attachment.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{sanitize_filename(file_path.name)}"'
                    )
                    msg.attach(attachment)
                
                log_and_print("info", f"Attached file: {file_path.name}")
                
    except Exception as exc:
        log_and_print("error", f"Error adding attachments: {exc}")
```

**Line-by-line explanation:**
- **Line 1**: Function signature taking MIMEMultipart message and attachment folder Path
- **Line 2**: Docstring explaining the function adds all files from folder as attachments
- **Line 3**: Checks if folder exists and is not None
- **Line 4**: Returns early if no valid attachment folder
- **Line 5**: Empty line for readability
- **Line 6**: Begins try block to handle potential file access errors
- **Line 7**: Iterates through all items in the attachment folder
- **Line 8**: Checks if current item is a file (not directory)
- **Line 9**: Comment explaining MIME type detection
- **Line 10**: Guesses MIME type and encoding based on file extension
- **Line 11**: If MIME type can't be determined or file is encoded, use generic binary type
- **Line 12**: Sets fallback MIME type for unknown file types
- **Line 13**: Empty line for readability
- **Line 14**: Splits MIME type into main type and subtype (e.g., "image/jpeg" → "image", "jpeg")
- **Line 15**: Empty line for readability
- **Line 16**: Opens file in binary read mode
- **Line 17**: Creates MIMEBase object with detected MIME type
- **Line 18**: Sets the attachment payload to file contents
- **Line 19**: Encodes attachment data in base64 format for email transmission
- **Line 20-23**: Adds Content-Disposition header marking as attachment with sanitized filename
- **Line 24**: Attaches the prepared attachment to the email message
- **Line 25**: Empty line for readability
- **Line 26**: Logs successful attachment addition
- **Line 27**: Empty line for readability
- **Line 28**: Catches any exceptions during attachment processing
- **Line 29**: Logs error if attachment processing fails

---

## 16. create_email_message

```python
def create_email_message(recipients: List[str], subject: str, body_html: str, 
                        from_address: str, attachment_folder: Path = None,
                        base_folder: Path = None, cc_recipients: List[str] = None,
                        bcc_recipients: List[str] = None) -> MIMEMultipart:
    """Create a properly formatted email message with embedded images and attachments."""
    cc_recipients = cc_recipients or []
    bcc_recipients = bcc_recipients or []
    
    # Embed images if base_folder is provided
    embedded_images = []
    if base_folder:
        body_html, embedded_images = embed_images_in_html(body_html, base_folder)
    
    # Create multipart message - CHANGED from 'mixed' to 'related' for embedded images
    if embedded_images:
        msg = MIMEMultipart('related')  # Use 'related' when we have embedded images
    else:
        msg = MIMEMultipart('mixed')    # Use 'mixed' for attachments only
    
    msg['From'] = from_address
    msg['To'] = ', '.join(recipients)
    if cc_recipients:
        msg['Cc'] = ', '.join(cc_recipients)
        log_and_print("info", f"CC: {len(cc_recipients)} recipient(s)")
       
    # Note: BCC headers are intentionally NOT added to prevent recipients from seeing BCC list
    if bcc_recipients:
        log_and_print("info", f"BCC: {len(bcc_recipients)} recipient(s)")
       
    msg['Subject'] = subject
    
    # Create multipart alternative for HTML content if we have embedded images
    if embedded_images:
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)
        
        # Add HTML body to alternative
        html_part = MIMEText(body_html, 'html', 'utf-8')
        msg_alternative.attach(html_part)
        
        # Add embedded images to main message
        for img in embedded_images:
            msg.attach(img)
    else:
        # No embedded images, add HTML directly
        html_part = MIMEText(body_html, 'html', 'utf-8')
        msg.attach(html_part)
    
    # Add attachments if folder exists
    if attachment_folder:
        add_attachments(msg, attachment_folder)
    
    return msg
```

**Line-by-line explanation:**
- **Lines 1-3**: Function signature with multiple parameters for email components
- **Line 4**: Docstring explaining comprehensive email creation functionality
- **Line 5**: Ensures cc_recipients is empty list if None provided
- **Line 6**: Ensures bcc_recipients is empty list if None provided
- **Line 7**: Empty line for readability
- **Line 8**: Comment about image embedding functionality
- **Line 9**: Initializes empty list for embedded images
- **Line 10**: Checks if base folder is provided for image embedding
- **Line 11**: Calls function to embed images and get modified HTML and image objects
- **Line 12**: Empty line for readability
- **Line 13**: Comment explaining MIME multipart type selection
- **Line 14**: Checks if there are embedded images
- **Line 15**: Uses 'related' multipart type for embedded images (allows cid: references)
- **Line 16**: Uses 'mixed' multipart type for attachments only
- **Line 17**: Empty line for readability
- **Line 18**: Sets From header
- **Line 19**: Sets To header with comma-separated recipients
- **Line 20**: Checks if CC recipients exist
- **Line 21**: Sets CC header with comma-separated CC recipients
- **Line 22**: Logs CC recipient count
- **Line 23**: Empty line for readability
- **Line 24**: Comment explaining why BCC headers are omitted (security)
- **Line 25**: Checks if BCC recipients exist
- **Line 26**: Logs BCC recipient count (but doesn't add to headers)
- **Line 27**: Empty line for readability
- **Line 28**: Sets Subject header
- **Line 29**: Empty line for readability
- **Line 30**: Comment about handling embedded images
- **Line 31**: Checks if embedded images exist
- **Line 32**: Creates alternative multipart container for HTML content
- **Line 33**: Attaches alternative container to main message
- **Line 34**: Empty line for readability
- **Line 35**: Comment about adding HTML body
- **Line 36**: Creates HTML part with UTF-8 encoding
- **Line 37**: Attaches HTML part to alternative container
- **Line 38**: Empty line for readability
- **Line 39**: Comment about adding embedded images
- **Line 40**: Iterates through embedded images
- **Line 41**: Attaches each image to main message
- **Line 42**: Handles case with no embedded images
- **Line 43**: Comment explaining direct HTML attachment
- **Line 44**: Creates HTML part with UTF-8 encoding
- **Line 45**: Attaches HTML directly to main message
- **Line 46**: Empty line for readability
- **Line 47**: Comment about adding attachments
- **Line 48**: Checks if attachment folder exists
- **Line 49**: Calls function to add all attachments
- **Line 50**: Empty line for readability
- **Line 51**: Returns completed email message

---

## 17. matches_filter_conditions

```python
def matches_filter_conditions(row: Dict, filters: List[str]) -> bool:
    """
    Check if a row matches the filter conditions with wildcard support.
    Each line in filters represents an OR condition.
    Within each line, comma-separated conditions are AND conditions.
    
    Supports wildcards:
    - * matches any sequence of characters
    - ? matches any single character
    - [seq] matches any character in seq
    - [!seq] matches any character not in seq
    
    Example filter:
        department=sales*,status=active
        department=marketing,region=west*
        role=*manager*
        email=*@company.com
    
    Logic: (sales* AND active) OR (marketing AND west*) OR (*manager*) OR (*@company.com)
    """
    if not filters:
        return True  # No filters means include all
    
    def matches_pattern(text: str, pattern: str) -> bool:
        """Check if text matches pattern with wildcard support."""
        # Convert both to lowercase for case-insensitive matching
        text = str(text).lower()
        pattern = pattern.lower()
        
        # Use fnmatch for Unix shell-style wildcards
        return fnmatch.fnmatch(text, pattern)
    
    # Process each line as a separate OR condition
    for filter_line in filters:
        filter_line = filter_line.strip()
        
        # Skip empty lines and comments
        if not filter_line or filter_line.startswith('#'):
            continue
        
        # Split the line into individual AND conditions
        and_conditions = [condition.strip() for condition in filter_line.split(',')]
        
        # Check if ALL conditions in this line match (AND logic)
        line_matches = True
        for condition in and_conditions:
            if not condition:
                continue
                
            if '=' in condition:
                # Key=value format with wildcard support
                key, value = condition.split('=', 1)
                key, value = key.strip(), value.strip()
                
                if key not in row:
                    line_matches = False
                    break  # Key doesn't exist, condition fails
                
                # Use wildcard matching instead of exact matching
                if not matches_pattern(row[key], value):
                    line_matches = False
                    break  # This AND condition failed
            else:
                # Simple wildcard search in all values
                condition_matched = False
                for row_value in row.values():
                    if matches_pattern(row_value, condition):
                        condition_matched = True
                        break
                
                if not condition_matched:
                    line_matches = False
                    break  # This AND condition failed
        
        # If this line matched completely (all AND conditions), return True (OR logic)
        if line_matches:
            return True
    
    # None of the OR conditions matched
    return False
```

**Line-by-line explanation:**
- **Line 1**: Function signature taking dictionary row and list of filter strings
- **Lines 2-16**: Comprehensive docstring explaining filter logic with examples
- **Line 17**: Checks if filters list is empty
- **Line 18**: Returns True if no filters (include all rows)
- **Line 19**: Empty line for readability
- **Line 20**: Defines inner function for pattern matching
- **Line 21**: Docstring for pattern matching function
- **Line 22**: Comment about case-insensitive matching
- **Line 23**: Converts text to lowercase string
- **Line 24**: Converts pattern to lowercase
- **Line 25**: Empty line for readability
- **Line 26**: Uses fnmatch module for Unix shell-style wildcard matching
- **Line 27**: Empty line for readability
- **Line 28**: Comment explaining OR condition processing
- **Line 29**: Iterates through each filter line
- **Line 30**: Strips whitespace from filter line
- **Line 31**: Empty line for readability
- **Line 32**: Comment about skipping empty/comment lines
- **Line 33**: Checks for empty lines or lines starting with #
- **Line 34**: Skips to next iteration if line should be ignored
- **Line 35**: Empty line for readability
- **Line 36**: Comment about splitting into AND conditions
- **Line 37**: Splits line by commas and strips whitespace from each condition
- **Line 38**: Empty line for readability
- **Line 39**: Comment explaining AND logic within line
- **Line 40**: Assumes line matches initially
- **Line 41**: Iterates through each AND condition in the line
- **Line 42**: Skips empty conditions
- **Line 43**: Continues to next condition if current is empty
- **Line 44**: Empty line for readability
- **Line 45**: Checks if condition contains equals sign (key=value format)
- **Line 46**: Comment explaining key=value format
- **Line 47**: Splits condition into key and value parts
- **Line 48**: Strips whitespace from both key and value
- **Line 49**: Empty line for readability
- **Line 50**: Checks if key exists in the row
- **Line 51**: Sets line_matches to False if key missing
- **Line 52**: Breaks out of condition loop (this line fails)
- **Line 53**: Empty line for readability
- **Line 54**: Comment about wildcard matching
- **Line 55**: Checks if row value matches pattern using wildcards
- **Line 56**: Sets line_matches to False if pattern doesn't match
- **Line 57**: Breaks out of condition loop (this AND condition fails)
- **Line 58**: Handles conditions without equals sign
- **Line 59**: Comment explaining search across all values
- **Line 60**: Assumes condition doesn't match initially
- **Line 61**: Iterates through all values in the row
- **Line 62**: Checks if any value matches the pattern
- **Line 63**: Sets condition_matched to True if match found
- **Line 64**: Breaks out of value loop (match found)
- **Line 65**: Empty line for readability
- **Line 66**: Checks if condition matched any value
- **Line 67**: Sets line_matches to False if no values matched
- **Line 68**: Breaks out of condition loop (this AND condition fails)
- **Line 69**: Empty line for readability
- **Line 70**: Comment explaining OR logic between lines
- **Line 71**: Checks if all AND conditions in this line matched
- **Line 72**: Returns True immediately if any line matches (OR logic)
- **Line 73**: Empty line for readability
- **Line 74**: Comment explaining final result
- **Line 75**: Returns False if no filter lines matched

---
