# NotifyBot Project

## What is NotifyBot? 🤖

NotifyBot is a Python-based email automation tool designed to:
- Filter email recipients from CSV data using flexible matching rules
- Send bulk emails in batches with rate limiting
- Support attachments and multiple recipient types (TO, CC, BCC)
- Provide dry-run capabilities for testing
- Log all operations for audit trails

## Key Features ✨

- **Flexible Filtering**: Support for exact match, contains, and regex patterns
- **Email Validation**: Built-in email validation using `email-validator`
- **Batch Processing**: Send emails in configurable batches with delays
- **Attachment Support**: Automatic attachment handling with size limits
- **Dry Run Mode**: Test campaigns by sending to approvers only
- **Deduplication**: Automatic removal of duplicate email addresses
- **Comprehensive Logging**: All operations logged to `notifybot.log`

## Prerequisites 📋

### Required Dependencies

```bash
pip install email-validator
```

### System Requirements

- Python 3.6+
- Local SMTP server (localhost) or modify the code for external SMTP
- Access to write files in the campaign directory

## Overview ✅

NotifyBot automates the process of:
- Filtering emails from a CSV (inventory.csv)
- Matching rows based on flexible rules in filter.txt
- Preparing a deduplicated to.txt email list
- Sending emails in batches (or doing a dry run to approvers)

## Directory Structure & File Requirements 📁

### Required Files

Your campaign directory must contain these files:

```
campaign1/
├── from.txt              # Sender email address
├── subject.txt           # Email subject line
├── body.html            # HTML email body
├── approver.txt         # List of approvers (for dry-run)
├── inventory.csv        # Source data for filtering
└── filter.txt           # Filtering rules
```

### Optional Files

```
campaign1/
├── to.txt               # Generated recipient list
├── cc.txt               # CC recipients
├── bcc.txt              # BCC recipients (hidden)
├── additional_to.txt    # Extra recipients to add
└── attachments/         # Directory for email attachments
    ├── document1.pdf
    ├── image1.jpg
    └── spreadsheet1.xlsx
```

### File Descriptions

| File | Purpose | Format |
|------|---------|---------|
| `from.txt` | Sender email | Plain text: `sender@company.com` |
| `subject.txt` | Email subject | Plain text: `Important Update` |
| `body.html` | Email content | HTML format |
| `approver.txt` | Approver emails | One email per line |
| `inventory.csv` | Source data | CSV with headers |
| `filter.txt` | Filter rules | CSV: `field,value,mode` |
| `to.txt` | Recipients | One email per line (auto-generated) |
| `cc.txt` | CC recipients | One email per line |
| `bcc.txt` | BCC recipients | One email per line |
| `additional_to.txt` | Extra recipients | One email per line |

## File Structure 🧩

## Step-by-Step Setup Guide 🧪

### Step 1: Prepare Your Campaign Directory

Create a new directory for your email campaign:

```bash
mkdir my_campaign
cd my_campaign
```

### Step 2: Create Required Files

#### 2.1 Create `from.txt`
```bash
echo "notifications@company.com" > from.txt
```

#### 2.2 Create `subject.txt`
```bash
echo "Important System Update - Action Required" > subject.txt
```

#### 2.3 Create `body.html`
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>System Update</title>
</head>
<body>
    <h1>Important System Update</h1>
    <p>Dear Team,</p>
    <p>We are implementing a critical system update...</p>
    <p>Best regards,<br>IT Team</p>
</body>
</html>
```

#### 2.4 Create `approver.txt`
```bash
echo "manager@company.com" > approver.txt
echo "it-lead@company.com" >> approver.txt
```

### Step 3: Prepare Your Data Files

#### 3.1 Create `inventory.csv` (your source data)

```csv
name,department,location,emailids,role
Alice Johnson,Engineering,India,alice@company.com,Senior Developer
Bob Smith,Marketing,US,bob@company.com,Marketing Manager
Charlie Brown,Engineering,India,charlie@company.com,Lead Engineer
David Wilson,Engineering,India,david@company.com;backup@company.com,DevOps Engineer
Eve Davis,HR,US,eve@company.com,HR Manager
Frank Miller,Engineering,UK,frank@company.com,Software Architect
```

#### 3.2 Create `filter.txt` (your filtering rules)

```csv
field,value,mode
department,Engineering,exact
location,India,contains
emailids,@company\.com$,regex
```

This filter will select:
- Records where `department` exactly equals "Engineering" (case-insensitive)
- Records where `location` contains "India" (case-insensitive)
- Records where `emailids` ends with "@company.com" (regex pattern)

### Step 4: Test with Dry Run

Always test your campaign first:

```bash
python3 notifybot.py my_campaign --dry-run
```

**Expected Output:**
```
Added 3 filtered addresses.
DRY-RUN: sending draft to approvers only.
Sent to 2 recipients.
```

### Step 5: Review Generated Files

Check the generated `to.txt` file:
```bash
cat my_campaign/to.txt
```

You should see:
```
alice@company.com
charlie@company.com
david@company.com
```

### Step 6: Run the Actual Campaign

Once you're satisfied with the dry run results:

```bash
python3 notifybot.py my_campaign
```

## Step-by-Step with Example 🧪

## Advanced Features & Configuration ⚙️

### Command Line Options

```bash
python3 notifybot.py <campaign_folder> [options]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run` | Send to approvers only | `False` |
| `--batch-size` | Recipients per batch | `500` |
| `--delay` | Seconds between batches | `5` |
| `--attachments-folder` | Custom attachment directory | `attachments/` |
| `--max-attachment-size` | Max MB per attachment | `10` |

### Examples

```bash
# Basic dry run
python3 notifybot.py my_campaign --dry-run

# Custom batch size and delay
python3 notifybot.py my_campaign --batch-size 100 --delay 10

# Custom attachment settings
python3 notifybot.py my_campaign --attachments-folder /path/to/files --max-attachment-size 25
```

### Adding Attachments

1. Create an `attachments/` directory in your campaign folder
2. Place files to attach (PDF, images, documents, etc.)
3. Files larger than `max-attachment-size` will be skipped

```bash
mkdir my_campaign/attachments
cp document.pdf my_campaign/attachments/
cp image.jpg my_campaign/attachments/
```

### Additional Recipients

Add extra recipients without modifying the filter:

```bash
echo "emergency@company.com" >> my_campaign/additional_to.txt
echo "backup@company.com" >> my_campaign/additional_to.txt
```

### CC and BCC Recipients

```bash
# CC recipients (visible to all)
echo "manager@company.com" >> my_campaign/cc.txt
echo "team-lead@company.com" >> my_campaign/cc.txt

# BCC recipients (hidden from others)
echo "audit@company.com" >> my_campaign/bcc.txt
```

## Filtering System Deep Dive 🔍

### How Filtering Works

The filtering system reads your `filter.txt` file and applies ALL conditions to each row in `inventory.csv`. A row must match ALL filter conditions to be included.

```python
# Simplified logic
for row in inventory_data:
    match = all(
        match_condition(
            actual=row.get(condition["field"], ""),
            expected=condition["value"],
            mode=condition.get("mode", "exact")
        )
        for condition in filter_conditions
    )
    if match:
        extract_emails_from_row(row)
```

### Matching Modes

| Mode | Behavior | Example Usage |
|------|----------|---------------|
| `exact` | Case-insensitive exact match | `department,Engineering,exact` |
| `contains` | Case-insensitive substring search | `location,New York,contains` |
| `regex` | Python regular expression | `email,.*@company\.com$,regex` |

### Filter Examples

#### Example 1: Department and Location Filter
```csv
field,value,mode
department,IT,exact
location,US,contains
```
Matches: Records with department="IT" AND location containing "US"

#### Example 2: Email Domain Filter
```csv
field,value,mode
emailids,@(company|subsidiary)\.com$,regex
```
Matches: Emails ending in @company.com or @subsidiary.com

#### Example 3: Multi-condition Filter
```csv
field,value,mode
department,Engineering,exact
role,Senior,contains
location,India,exact
status,Active,exact
```
Matches: Senior Engineering roles in India with Active status

### Email Extraction

The system extracts emails from the `emailids` column, which can contain:
- Single email: `user@company.com`
- Multiple emails: `user@company.com;backup@company.com`
- Comma-separated: `user@company.com,backup@company.com`

Invalid emails are automatically filtered out and logged.

## Process Flow & File Operations 📊

### 1. Validation Phase
- Check for required files (`from.txt`, `subject.txt`, `body.html`, `approver.txt`)
- Validate email addresses in all recipient files
- Parse and validate filter conditions

### 2. Filtering Phase
- Read `inventory.csv` and `filter.txt`
- Apply all filter conditions to each row
- Extract valid email addresses from matching rows
- Remove duplicates and invalid emails

### 3. Preparation Phase
- Generate or update `to.txt` with filtered recipients
- Add recipients from `additional_to.txt` if present
- Create backup of existing `to.txt` before deduplication
- Load CC and BCC recipients if specified

### 4. Execution Phase
- **Dry Run**: Send test email to approvers only
- **Production**: Send emails in batches with delays
- Process attachments (skip files exceeding size limit)
- Log all operations and errors

### File Backup System

Before deduplication, NotifyBot creates timestamped backups:
```
to_20241207_143522.txt  # Backup of original to.txt
to.txt                  # Deduplicated version
```

## Logging & Troubleshooting 🧹

### Log Files

All operations are logged to `notifybot.log` in the current directory:

```
2024-12-07 14:35:22,123 - INFO - send_email_from_folder [line 125] - Start sending from my_campaign
2024-12-07 14:35:22,456 - INFO - write_to_txt [line 89] - Appended 3 emails to to.txt
2024-12-07 14:35:22,789 - INFO - deduplicate_file [line 102] - Deduplicated to.txt
2024-12-07 14:35:23,012 - INFO - send_email [line 234] - Sent to: alice@company.com, charlie@company.com
```

### Console Output

Terminal output uses color coding:
- 🟡 **Yellow**: Warnings (invalid emails, skipped attachments)
- 🔴 **Red**: Errors (missing files, send failures)
- ⚪ **Normal**: Information messages

### Common Issues & Solutions

#### Issue: "Missing required files"
```
Missing: from.txt, subject.txt
```
**Solution**: Create the missing files in your campaign directory.

#### Issue: "No recipients"
```
No recipients.
```
**Solution**: Check your `filter.txt` conditions - they might be too restrictive.

#### Issue: "Invalid email skipped"
```
Invalid email skipped: not-an-email
```
**Solution**: Fix email addresses in your `inventory.csv` or recipient files.

#### Issue: "Attachment failed"
```
Attachment failed: large_file.pdf
```
**Solution**: Reduce file size or increase `--max-attachment-size`.

#### Issue: "Failed to send"
```
Failed to send to recipients: [Errno 61] Connection refused
```
**Solution**: Check your SMTP server configuration (default: localhost).

### Debug Mode

Enable verbose logging by checking `notifybot.log` for detailed information about:
- File parsing operations
- Filter matching results
- Email validation details
- SMTP communication

## Best Practices & Tips 💡

### Pre-Campaign Checklist

- [ ] All required files are present and populated
- [ ] `inventory.csv` has proper headers and data
- [ ] `filter.txt` uses valid field names from your CSV
- [ ] Approver emails are valid and accessible
- [ ] SMTP server is configured and accessible
- [ ] Attachments are under size limit
- [ ] Dry run completed successfully

### Filter Design Guidelines

1. **Start Simple**: Begin with basic filters and add complexity gradually
2. **Test Thoroughly**: Always run dry-run first
3. **Validate Field Names**: Ensure filter fields exist in your CSV
4. **Case Sensitivity**: Remember that `exact` and `contains` are case-insensitive
5. **Regex Caution**: Test regex patterns separately before using

### Email Content Best Practices

1. **HTML Compatibility**: Test your HTML across different email clients
2. **Plain Text Fallback**: The script automatically adds a plain text version
3. **Subject Lines**: Keep under 50 characters for better deliverability
4. **Attachment Sizes**: Keep attachments small (under 10MB by default)

### Production Deployment

1. **Test Environment**: Always test in a safe environment first
2. **Batch Sizes**: Start with smaller batches (50-100) for large campaigns
3. **Rate Limiting**: Increase delays between batches if needed
4. **Monitoring**: Watch logs during campaign execution
5. **Backup**: Keep backups of your campaign directories

### Security Considerations

- **Email Validation**: All emails are validated before sending
- **File Permissions**: Ensure proper file permissions on campaign directories
- **Log Security**: Protect log files as they contain email addresses
- **SMTP Security**: Use secure SMTP configurations in production

## Troubleshooting Guide 🔧

### Campaign Not Sending

1. Check required files exist
2. Verify SMTP server connectivity
3. Validate sender email address
4. Check recipient file format

### No Recipients After Filtering

1. Verify filter conditions match your data
2. Check field names in `filter.txt`
3. Test with simpler filter conditions
4. Examine `inventory.csv` data format

### Attachment Issues

1. Check file sizes against limit
2. Verify file permissions
3. Test with different file types
4. Check attachment directory path

### Email Delivery Problems

1. Verify SMTP server settings
2. Check sender reputation
3. Review email content for spam triggers
4. Test with smaller recipient batches

## Example Workflow Summary ✅

### Complete Campaign Workflow

1. **Setup Phase**
   ```bash
   mkdir new_campaign
   cd new_campaign
   ```

2. **File Preparation**
   ```bash
   # Create required files
   echo "sender@company.com" > from.txt
   echo "Important Update" > subject.txt
   echo "manager@company.com" > approver.txt
   
   # Create HTML content
   cat > body.html << 'EOF'
   <html><body><h1>Update</h1><p>Content here</p></body></html>
   EOF
   ```

3. **Data Setup**
   ```bash
   # Prepare your inventory.csv and filter.txt
   # (See examples above)
   ```

4. **Testing Phase**
   ```bash
   # Dry run first
   python3 notifybot.py new_campaign --dry-run
   
   # Review results
   cat new_campaign/to.txt
   tail -f notifybot.log
   ```

5. **Production Execution**
   ```bash
   # Run actual campaign
   python3 notifybot.py new_campaign --batch-size 100 --delay 10
   ```

6. **Monitoring**
   ```bash
   # Monitor progress
   tail -f notifybot.log
   
   # Check completion
   grep "Summary" notifybot.log
   ```

## Advanced Use Cases 🚀

### Multi-Stage Campaigns

Run different campaigns for different audiences:

```bash
# Campaign for managers
python3 notifybot.py manager_campaign

# Campaign for developers  
python3 notifybot.py developer_campaign

# Campaign for all staff
python3 notifybot.py all_staff_campaign
```

### Scheduled Campaigns

Use cron for scheduled sends:

```bash
# Edit crontab
crontab -e

# Add entry for daily 9 AM send
0 9 * * * cd /path/to/campaigns && python3 notifybot.py daily_update
```

### Integration with Other Tools

Generate CSV from database:
```bash
# Export from database
mysql -u user -p -e "SELECT name,email,department FROM users" db > inventory.csv

# Run campaign
python3 notifybot.py db_campaign
```

## API Reference 📚

### Core Functions

#### `send_email_from_folder()`
Main function that orchestrates the entire email campaign.

**Parameters:**
- `base_folder` (str): Path to campaign directory
- `dry_run` (bool): Whether to send to approvers only
- `batch_size` (int): Number of recipients per batch
- `delay` (int): Seconds between batches
- `attachments_folder` (str): Path to attachments directory
- `max_attachment_size_mb` (int): Maximum attachment size in MB

#### `match_condition()`
Evaluates filter conditions against data.

**Parameters:**
- `actual` (str): Value from CSV row
- `expected` (str): Expected value from filter
- `mode` (str): Matching mode (exact/contains/regex)

**Returns:** Boolean indicating match result

### File Format Specifications

#### `filter.txt` Format
```csv
field,value,mode
column_name,match_value,exact|contains|regex
```

#### `inventory.csv` Format
- Must have headers in first row
- `emailids` column can contain multiple emails separated by `;` or `,`
- All other columns are available for filtering

This comprehensive documentation should help you understand and effectively use the NotifyBot system for your email campaigns. Remember to always test with dry-run before sending to production recipients!
