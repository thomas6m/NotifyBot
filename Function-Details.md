# NotifyBot Validation Functions Analysis

## Overview

These four functions form a hierarchical validation system that ensures NotifyBot has all required files and that field names used in configuration files match available data columns. The system uses a priority-based approach for inventory validation.

## Function Details

### 1. `validate_base_folder(base_folder)` - Path Security
**Purpose**: Ensures the base folder is secure and properly located

```python
def validate_base_folder(base_folder: str) -> Path:
    base_folder_path = BASEFOLDER_PATH / base_folder  # /notifybot/basefolder/[user_folder]
    
    if not base_folder_path.is_dir():
        raise ValueError(f"Invalid base folder: {base_folder}")
    
    return base_folder_path
```

**How it works**:
- Takes a relative folder name (e.g., "campaign_2024")
- Constructs full path: `/notifybot/basefolder/campaign_2024`
- Validates the directory exists
- Returns validated `Path` object
- **Security**: Prevents path traversal attacks by enforcing base directory

---

### 2. `validate_fields_against_inventory()` - Basic Field Validation
**Purpose**: Original validation function (now largely replaced by the priority-based version)

**Key Logic**:
```python
# Read inventory headers
with open(inventory_path, mode="r", newline="", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    available_fields = set(reader.fieldnames or [])

# Validate filter.txt field names
for condition in filter_conditions:
    # Extract field name from conditions like "department=sales" or "region!=europe"
    field_name = extract_field_from_condition(condition)
    if field_name not in available_fields:
        errors.append(f"Field '{field_name}' not found in inventory.csv")

# Validate field.txt (only in multi mode)
if mode == "multi":
    for field_name in field_names:
        if field_name not in available_fields:
            errors.append(f"Field '{field_name}' not found in inventory.csv")
```

---

### 3. `validate_fields_with_priority()` - Enhanced Priority-Based Validation
**Purpose**: The main validation engine with sophisticated inventory prioritization

#### Priority System:
1. **Local field-inventory.csv** (highest priority)
2. **Global inventory.csv** (fallback)

#### Validation Rules:
```python
# RULE 1: filter.txt always validates against GLOBAL inventory
if filter_file_path.exists():
    validate_filter_against_global_inventory()
    
    # BONUS: If local field-inventory exists, also validate against it
    if local_field_inventory_exists():
        validate_filter_against_local_inventory()

# RULE 2: field.txt uses LOCAL inventory if available
if mode == "multi" and field_file_path.exists():
    if local_field_inventory_exists():
        validate_field_txt_against_local_inventory()  # Priority
    else:
        validate_field_txt_against_global_inventory()  # Fallback
```

#### Critical Fix for Whitespace:
```python
# FIXED: Strip whitespace from headers (common CSV issue)
local_available_fields = set(field.strip() for field in (reader.fieldnames or []))
```

**Example Scenario**:
- Global inventory has: `["name", "email", "department", "region"]`
- Local field-inventory has: `["name", "department", "project", "team"]`
- filter.txt contains: `department=sales` ✅ (exists in global)
- field.txt contains: `project` ✅ (exists in local, gets priority)

---

### 4. `check_required_files()` - Master Validation Orchestrator
**Purpose**: Coordinates all validation checks and enforces business rules

#### File Requirements by Mode:

**Single Mode**:
```python
# Must have at least ONE recipient source:
recipient_sources = [
    "to.txt",                    # Direct recipient list
    "filter.txt + inventory.csv", # Filtered from database
    "additional_to.txt",         # Additional recipients
    "cc.txt",                    # Carbon copy
    "bcc.txt"                    # Blind carbon copy
]
```

**Multi Mode**:
```python
# MUST have both:
required_files = [
    "filter.txt",        # Multiple filter conditions
    "inventory.csv"      # Data source
]
```

#### Validation Flow:
```python
def check_required_files(base, required, dry_run=True, mode="single"):
    # 1. Check basic required files exist
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        raise MissingRequiredFilesError(f"Missing: {', '.join(missing)}")
    
    # 2. Mode-specific validations
    if mode == "multi":
        if not (base / "filter.txt").is_file():
            raise MissingRequiredFilesError("Multi mode requires filter.txt")
    
    if mode == "single":
        # Check at least one recipient source exists
        validate_recipient_sources()
    
    # 3. Field validation (the key part)
    needs_inventory = (
        mode == "multi" or 
        (mode == "single" and uses_filters())
    )
    
    if needs_inventory:
        log_and_print("info", "Validating field names with priority-based inventory checking...")
        is_valid, validation_errors = validate_fields_with_priority(base, mode)
        
        if not is_valid:
            # Show helpful error messages
            for error in validation_errors:
                log_and_print("error", f"  {error}")
            raise MissingRequiredFilesError("Field validation failed")
        else:
            log_and_print("success", "Field validation passed - all field names are valid")
```

## Validation Flow Example

### Scenario: Multi-mode campaign with local customization

**Setup**:
- Global inventory: `/notifybot/inventory/inventory.csv` with fields: `name, email, department, region`
- Local inventory: `/notifybot/basefolder/campaign2024/field-inventory.csv` with fields: `name, department, project, budget` 
- filter.txt: `department=engineering,region!=asia`
- field.txt: `project\nbudget`

**Validation Steps**:

1. **Path Validation**:
   ```python
   base_folder = validate_base_folder("campaign2024")
   # Result: /notifybot/basefolder/campaign2024/ ✅
   ```

2. **File Existence**:
   ```python
   check_required_files(base_folder, ["subject.txt", "body.html", ...], mode="multi")
   # Checks: subject.txt ✅, body.html ✅, filter.txt ✅, etc.
   ```

3. **Priority-based Field Validation**:
   ```python
   validate_fields_with_priority(base_folder, "multi")
   
   # Global inventory fields: {name, email, department, region}
   # Local inventory fields: {name, department, project, budget}
   
   # RULE 1: Validate filter.txt against GLOBAL
   # "department=engineering" → "department" in global ✅
   # "region!=asia" → "region" in global ✅
   
   # RULE 2: Validate field.txt against LOCAL (priority)
   # "project" in local ✅
   # "budget" in local ✅
   
   # Result: ✅ All validations pass
   ```

## Error Handling Examples

### Missing Field Error:
```
❌ Field validation failed:
  filter.txt line 1: Field 'invalid_field' not found in global inventory.csv
  field.txt line 2: Field 'nonexistent' not found in local field-inventory.csv

Available fields:
Global inventory.csv: department, email, name, region
Local field-inventory.csv: budget, department, name, project
```

### Helpful Suggestions:
```
ℹ️  Available fields in inventory.csv: department, email, name, region
ℹ️  Local field-inventory.csv found with fields: budget, department, name, project
ℹ️  Using local field-inventory.csv for field.txt validation (priority)
✅ All field.txt field names validated successfully against local field-inventory.csv
```
##################################
5. csv_log_entry(message)
This function creates properly formatted CSV log entries with these components:
Purpose: Generates a single CSV line for logging with proper escaping to handle special characters in log messages.
What it does:

Timestamp: Creates a millisecond-precision timestamp using time.time_ns() // 1_000_000
Username: Attempts to get the current user with os.getlogin(), with fallbacks to environment variables (USER, USERNAME) or "unknown" if unavailable
Message: The log message passed as parameter
CSV Escaping: Uses Python's csv.writer to properly escape the message field, handling commas, quotes, and newlines that could break CSV format

Returns: A properly escaped CSV line as a string (timestamp, username, message)
Example output: 1704067200000,john_doe,"Email sent to 150 recipients successfully"
6. setup_logging()
This function configures the application's logging system and creates a global logging utility.
What it does:

Directory Setup: Ensures the log directory exists at /notifybot/logs/
Logging Configuration:

Sets up file logging to /notifybot/logs/notifybot.log
Uses INFO level and above (INFO, WARNING, ERROR)
Uses a simple format that just outputs the message (since CSV formatting is handled elsewhere)
Uses append mode to preserve existing logs


Global Function Creation: Creates a log_and_print() function that:

Dual Output: Both logs to file AND prints to console
Emoji Support: Maps log levels to emojis (ℹ️ for info, ⚠️ for warning, ❌ for error, etc.)
CSV Formatting: Uses csv_log_entry() to format all log entries consistently
Level Mapping: Supports custom levels like "success", "processing", "backup", etc.



The log_and_print() function:
pythondef log_and_print(level: str, message: str) -> None:
    emoji = emoji_mapping.get(level.lower(), "")
    csv_log = csv_log_entry(f"{emoji} {message}")
    log_func = getattr(logging, level.lower(), logging.info)
    log_func(csv_log)
    print(f"{csv_log}")  # Also print to console
Usage throughout the application:
pythonlog_and_print("info", "Processing 150 recipients")
log_and_print("success", "Email sent successfully") 
log_and_print("error", "Failed to send email")
####################################



