# NotifyBot Email Sender

A Python script for sending batch emails with support for filtering, attachments, dry-run mode, and comprehensive logging.

## Features

- **Batch Email Sending**: Send emails to multiple recipients in configurable batches
- **Dry Run Mode**: Test email content by sending drafts to approvers only
- **Email Filtering**: Filter recipients from CSV inventory using condition files
- **Attachment Support**: Automatically attach files from specified folders
- **Duplicate Prevention**: Automatic deduplication of recipient lists
- **Comprehensive Logging**: Detailed logging with timestamps and error tracking
- **Email Validation**: Regex-based email address validation
- **Colored Output**: Visual feedback with colored console output for errors and warnings

## Requirements

- Python 3.6+
- Local SMTP server (configured for localhost)
- Required Python modules (all standard library):
  - `smtplib`
  - `email`
  - `csv`
  - `pathlib`
  - `logging`

## Installation

1. Download the `notifybot.py` script
2. Ensure you have a local SMTP server running (e.g., Postfix, Sendmail)
3. Make the script executable: `chmod +x notifybot.py`

## Usage

### Basic Usage

```bash
python notifybot.py /path/to/email/folder
```

### Advanced Usage

```bash
python notifybot.py /path/to/email/folder \
    --dry-run \
    --batch-size 100 \
    --delay 10 \
    --attachments-folder /path/to/attachments
```

### Command Line Options

- `base_folder`: **Required**. Directory containing email configuration files
- `--dry-run`: Send draft email to approvers only (no actual recipients)
- `--batch-size`: Number of emails per batch (default: 500)
- `--delay`: Delay in seconds between batches (default: 5)
- `--attachments-folder`: Custom path for attachments (default: `attachments/` in base folder)

## File Structure

Your email folder must contain these **required files**:

```
email_campaign/
├── from.txt          # Sender email address
├── subject.txt       # Email subject line
├── body.html         # HTML email body
├── approver.txt      # Approver email addresses (one per line)
├── to.txt            # Primary recipients (auto-generated/managed)
├── cc.txt            # CC recipients (optional)
├── bcc.txt           # BCC recipients (optional)
├── additional_to.txt # Additional recipients to add (optional)
├── inventory.csv     # Recipient database (optional, for filtering)
├── filter.txt        # Filter conditions (optional, CSV format)
└── attachments/      # Folder for email attachments (optional)
    ├── document1.pdf
    ├── image1.jpg
    └── spreadsheet.xlsx
```

### File Descriptions

#### Required Files

- **`from.txt`**: Contains the sender's email address
- **`subject.txt`**: Contains the email subject line
- **`body.html`**: Contains the HTML email body content
- **`approver.txt`**: Contains approver email addresses (one per line) for dry-run mode

#### Optional Files

- **`to.txt`**: Primary recipients list (automatically managed by the script)
- **`cc.txt`**: CC recipients (one per line)
- **`bcc.txt`**: BCC recipients (one per line)
- **`additional_to.txt`**: Additional recipients to add to the main list
- **`inventory.csv`**: Database of potential recipients with metadata
- **`filter.txt`**: CSV file defining filter conditions for inventory

#### Inventory and Filtering

The `inventory.csv` should contain recipient data with at least an `emailids` column:

```csv
name,department,emailids,status
John Doe,Engineering,john.doe@company.com,active
Jane Smith,Marketing,jane.smith@company.com;j.smith@company.com,active
```

The `filter.txt` defines conditions to filter recipients:

```csv
department,status
Engineering,active
Marketing,active
```

## Logging

The script creates a detailed log file (`notifybot.log`) with:

- Timestamp for each action
- Function names and line numbers
- Detailed error messages with full tracebacks
- Summary statistics including timing information

## Error Handling

The script includes comprehensive error handling:

- **File Validation**: Checks for required files before execution
- **Email Validation**: Validates email addresses using regex
- **Backup Creation**: Creates timestamped backups before file modifications
- **Colored Output**: Uses colored console output for better visibility:
  - 🔴 Red: Critical errors
  - 🟡 Yellow: Warnings
  - ⚪ White: Normal output

## Security Considerations

- The script connects to `localhost` SMTP server only
- Email addresses are validated before sending
- No sensitive data is logged (passwords, API keys)
- Backup files are created to prevent data loss

## Troubleshooting

### Common Issues

1. **"Missing required files" error**
   - Ensure all required files exist in the base folder
   - Check file permissions

2. **"Failed to send email" error**
   - Verify SMTP server is running on localhost
   - Check firewall settings
   - Verify sender email address is valid

3. **"Invalid email address" warnings**
   - Review recipient lists for malformed email addresses
   - Check for extra spaces or special characters

4. **Attachment failures**
   - Ensure attachment files exist and are readable
   - Check file size limits on your SMTP server
   - Verify attachment folder path

### Log Analysis

Check `notifybot.log` for detailed information about:
- Email sending success/failure
- File reading errors
- Attachment processing
- Performance statistics

## Examples

### Example 1: Simple Campaign

```bash
# Send emails to all recipients in to.txt
python notifybot.py /home/user/campaigns/newsletter
```

### Example 2: Dry Run Test

```bash
# Test email content by sending only to approvers
python notifybot.py /home/user/campaigns/newsletter --dry-run
```

### Example 3: Large Campaign with Custom Settings

```bash
# Send large campaign with smaller batches and longer delays
python notifybot.py /home/user/campaigns/announcement \
    --batch-size 50 \
    --delay 30 \
    --attachments-folder /shared/attachments
```

## Best Practices

1. **Always test with --dry-run first**
2. **Use appropriate batch sizes** (50-500 depending on server capacity)
3. **Set reasonable delays** between batches to avoid overwhelming the server
4. **Monitor logs** during and after sending
5. **Keep backups** of recipient lists before major campaigns
6. **Validate email content** in HTML format before sending

## License

This script is provided as-is for educational and internal use purposes.
