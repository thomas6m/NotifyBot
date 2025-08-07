# Multi-Mode Recipient Functions Documentation

## Overview

These two functions work together to handle recipient management in multi-mode email campaigns, where multiple personalized emails are sent based on different filter conditions.

## `get_recipients_for_multi_mode` Function

### Purpose
This function processes multiple filter conditions to generate individual email configurations, each with its own recipient list and field values for template substitution.

### Parameters
- `base_folder: Path` - The base folder containing configuration files
- `dry_run: bool` - Whether this is a dry-run (sends to approvers instead)

### Returns
A tuple containing:
- `email_configs: List[Dict]` - List of email configurations, one per filter
- `final_cc_recipients: List[str]` - CC recipients for each email
- `final_bcc_recipients: List[str]` - BCC recipients for each email
- `total_original_recipients_count: int` - Total TO recipients across all emails
- `original_cc_count: int` - Number of CC recipients per email
- `original_bcc_count: int` - Number of BCC recipients per email

### Key Features

#### 1. Filter Processing
```python
# Read filter conditions from filter.txt
filters = read_file(base_folder / "filter.txt").splitlines()
filters = [f.strip() for f in filters if f.strip() and not f.strip().startswith('#')]
```

#### 2. Field Value Extraction
```python
# Extract field values for template substitution
if field_names:
    field_values = extract_field_values_from_matched_rows(
        filter_line, field_names, INVENTORY_PATH, base_folder
    )
```

#### 3. Email Configuration Creation
For each filter, creates a configuration with:
- Filter condition
- Current recipients (modified for dry-run)
- Original recipients (preserved)
- Field values for substitution
- Metadata

#### 4. Dry-Run Handling
```python
if dry_run:
    # Replace recipients with approvers but preserve original data
    for config in email_configs:
        config['recipients'] = approver_emails  # For sending
        # config['original_recipients'] remains unchanged for reference
```

---

## `save_multi_mode_recipients` Function

### Purpose
Saves detailed recipient information to files for reference, creating organized documentation of who will receive each email.

### Parameters
- `base_folder: Path` - Base folder for saving files
- `email_configs: List[Dict]` - Email configurations from multi-mode
- `cc_recipients: List[str]` - CC recipients (optional)
- `bcc_recipients: List[str]` - BCC recipients (optional)

### File Structure Created

```
basefolder/
└── recipients/
    ├── filter_001_sector_finance.txt
    ├── filter_002_region_us_east.txt
    ├── filter_003_cluster_prod.txt
    ├── cc_recipients.txt
    ├── bcc_recipients.txt
    ├── all_unique_recipients.txt
    └── multi_mode_summary.txt
```

### Generated Files

#### 1. Individual Filter Files
```
# filter_001_sector_finance.txt
# Filter 1: sector=finance
# Generated: 2025-01-15 14:30:25
# Recipients: 45
# Field values: {'sector': 'finance', 'region': 'us-east,us-west'}
#
user1@company.com
user2@company.com
...
```

#### 2. Summary File
Contains comprehensive statistics:
- Total filters processed
- Unique recipient counts
- Breakdown by filter
- File listing
- Grand totals

#### 3. Consolidated Files
- `all_unique_recipients.txt` - All unique TO recipients across filters
- `cc_recipients.txt` - CC recipients (sent with each email)
- `bcc_recipients.txt` - BCC recipients (sent with each email)

### Key Features

#### Safe Filename Generation
```python
safe_filter_name = re.sub(r'[^\w\s.-]', '_', filter_line)[:50]
safe_filter_name = re.sub(r'\s+', '_', safe_filter_name)
```

#### Comprehensive Statistics
```python
# Calculates totals, unique counts, and percentages
total_to_recipients = sum(config['recipient_count'] for config in filter_summaries)
grand_total = total_to_recipients + (len(cc_recipients) + len(bcc_recipients)) * len(email_configs)
```

#### Error Handling
Each file operation is wrapped in try-catch blocks to ensure partial failures don't break the entire process.

---

## Workflow Integration

### Multi-Mode Process Flow

1. **Filter Reading**: Read conditions from `filter.txt`
2. **Field Definition**: Read field names from `field.txt` (optional)
3. **Recipient Generation**: Apply each filter to `inventory.csv`
4. **Field Extraction**: Extract values for template substitution
5. **Configuration Creation**: Build email configs with all metadata
6. **Dry-Run Handling**: Replace recipients with approvers if needed
7. **File Saving**: Document all recipient data for reference

### Example Usage Scenario

```python
# Multi-mode with 3 filters
email_configs, cc, bcc, total_count, cc_count, bcc_count = get_recipients_for_multi_mode(
    base_folder=Path("/notifybot/basefolder/campaign1"),
    dry_run=False
)

# This would generate:
# - 3 individual emails with personalized content
# - Each email targets different recipients based on filters
# - CC/BCC added to each email
# - All recipient data saved to recipients/ folder
```

### Benefits

1. **Transparency**: Complete audit trail of who receives what
2. **Recovery**: Can recreate campaigns from saved data
3. **Validation**: Easy to verify recipient targeting before sending
4. **Debugging**: Clear visibility into filter matching and field extraction
5. **Compliance**: Documentation for email campaign records

## Function Signatures

### `get_recipients_for_multi_mode`
```python
def get_recipients_for_multi_mode(base_folder: Path, dry_run: bool) -> Tuple[
    List[Dict], List[str], List[str], int, int, int
]:
```

### `save_multi_mode_recipients`
```python
def save_multi_mode_recipients(
    base_folder: Path, 
    email_configs: List[Dict], 
    cc_recipients: List[str] = None, 
    bcc_recipients: List[str] = None
) -> None:
```

## Email Configuration Structure

Each email configuration dictionary contains:
```python
{
    'filter_line': str,           # Original filter condition
    'recipients': List[str],      # Current recipients (modified for dry-run)
    'original_recipients': List[str],  # Original recipients (preserved)
    'field_values': Dict[str, str],    # Values for template substitution
    'filter_number': int,         # Sequential filter number
    'original_recipients_count': int   # Count of original recipients
}
```

This system ensures that multi-mode campaigns are both powerful and well-documented, providing the flexibility of personalized targeting while maintaining full accountability and traceability.
