# NotifyBot Main Function Explanation

## Overview
The `main()` function is the entry point for NotifyBot, an automated email batch sender that supports two modes: **single mode** (one email to multiple recipients) and **multi mode** (multiple personalized emails based on filters).

## Function Structure

### 1. Argument Parsing & Setup
```python
# Get inventory fields for help text
inventory_fields_help = get_inventory_fields_for_help()

parser = argparse.ArgumentParser(...)
```

**Key Arguments:**
- `--base-folder`: Required folder inside `/notifybot/basefolder/`
- `--mode`: Force single/multi mode (overrides mode.txt)
- `--dry-run`: Send only to approvers with DRAFT prefix
- `--force`: Skip confirmation prompt
- `--batch-size`: Number of emails per batch (default: 500)
- `--delay`: Delay between batches (default: 5.0s)

### 2. Initialization & Validation
```python
setup_logging()
base_folder = validate_base_folder(args.base_folder)
mode = determine_mode(base_folder, args.mode)
```

**Steps:**
- Configure logging system
- Validate the base folder exists in `/notifybot/basefolder/`
- Determine operating mode (CLI arg > mode.txt > default 'single')

### 3. File Validation
```python
required_files = ["subject.txt", "body.html", "from.txt", "approver.txt"]
check_required_files(base_folder, required_files, args.dry_run, mode)
```

**Checks:**
- Required files exist
- Mode-specific requirements (filter.txt for multi mode)
- Field validation against inventory.csv
- Recipient source validation

### 4. Content Loading
```python
subject = read_file(base_folder / "subject.txt")
body_html = read_file(base_folder / "body.html")
from_address = read_file(base_folder / "from.txt")
signature_html = read_signature()
final_body_html = combine_body_and_signature(body_html, signature_html)
```

**Loads:**
- Email subject template
- HTML body template
- From address
- Optional signature from `/notifybot/signature.html`
- Combines body + signature

### 5. Content Validation
```python
if not subject:
    log_and_print("error", "Subject is empty")
    sys.exit(1)
# ... similar validation for body and from_address
```

**Validates:**
- Subject is not empty
- Body HTML is not empty
- From address is valid email format

### 6. Attachment Processing
```python
attachment_folder = base_folder / "attachment"
if attachment_folder.exists():
    attachment_count = len([f for f in attachment_folder.iterdir() if f.is_file()])
    log_and_print("info", f"Found {attachment_count} attachment(s)")
```

## Mode-Specific Processing

### Single Mode Processing
```python
if mode == "single":
    (final_recipients, final_cc_recipients, final_bcc_recipients, 
     original_recipients_count, original_cc_count, original_bcc_count) = get_recipients_for_single_mode(base_folder, args.dry_run)
```

**Single Mode Features:**
- One email sent to multiple recipients
- Recipients from: `to.txt`, `filter.txt + inventory.csv`, `additional_to.txt`, `cc.txt`, `bcc.txt`
- Support for batching large recipient lists
- Merges additional recipients with filtered results

**Summary Display:**
- Shows from address, subject, signature status
- In dry-run: shows approvers count and original target count
- In live mode: shows actual recipient breakdown (TO/CC/BCC)
- Displays batch size and delay settings

### Multi Mode Processing
```python
elif mode == "multi":
    (email_configs, final_cc_recipients, final_bcc_recipients, 
     total_original_recipients_count, original_cc_count, original_bcc_count) = get_recipients_for_multi_mode(base_folder, args.dry_run)
```

**Multi Mode Features:**
- Multiple personalized emails based on filter conditions
- Each line in `filter.txt` creates a separate email
- Template substitution using `field.txt` placeholders
- Field values extracted from inventory.csv for matched rows

**Email Configurations:**
Each filter creates an email config with:
- Filter condition
- Recipient list (filtered from inventory)
- Field values for template substitution
- Original recipient count (for dry-run reference)

## Confirmation & Execution

### User Confirmation
```python
if not args.force:
    if not prompt_for_confirmation():
        log_and_print("info", "Email sending aborted by user.")
        sys.exit(0)
```

Unless `--force` is used, prompts user to confirm before sending.

### Email Sending

**Single Mode:**
```python
send_single_mode_emails(
    final_recipients, 
    subject, 
    final_body_html,
    from_address, 
    args.batch_size, 
    dry_run=args.dry_run,
    # ... other parameters
)
```

**Multi Mode:**
```python
send_multi_mode_emails(
    email_configs,
    subject,  # template
    final_body_html,  # template with signature
    from_address,
    # ... other parameters
)
```

## Dry-Run vs Live Mode

### Dry-Run Mode (`--dry-run`)
- Sends emails only to approvers from `approver.txt`
- Adds "DRAFT" prefix to subject
- Includes recipient count info in email body
- Preserves original recipient data for reference
- Used for testing and approval workflows

### Live Mode
- Sends to actual recipients
- Uses real CC/BCC lists
- Processes in batches with delays
- Saves recipient backup files

## Error Handling
```python
except MissingRequiredFilesError as e:
    log_and_print("error", str(e))
    sys.exit(1)
except ValueError as e:
    log_and_print("error", str(e))
    sys.exit(1)
except KeyboardInterrupt:
    log_and_print("warning", "Operation interrupted by user")
    sys.exit(1)
```

**Handles:**
- Missing required files
- Invalid configuration values
- User interruption (Ctrl+C)
- Unexpected errors with full traceback

## Key Features

### Logging
- CSV-formatted logs with timestamps and usernames
- Colored console output with emojis
- Detailed progress tracking and error reporting

### Batching
- Prevents overwhelming mail servers
- Configurable batch sizes and delays
- Proper CC/BCC handling across batches

### Template Substitution (Multi Mode)
- Placeholder replacement using `{field_name}` syntax
- Field values extracted from CSV data
- Smart comma-separated value formatting

### File Organization
- Saves recipient backups for reference
- Creates organized folder structure
- Generates summary reports

## Usage Examples

**Single Mode Dry-Run:**
```bash
python notifybot.py --base-folder my_campaign --dry-run
```

**Multi Mode Live with Custom Batching:**
```bash
python notifybot.py --base-folder my_campaign --mode multi --batch-size 200 --delay 10.0 --force
```

The main function orchestrates the entire email sending workflow, from initial setup through final execution, with comprehensive error handling and logging throughout the process.
