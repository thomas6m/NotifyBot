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
#######################################################################################

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

