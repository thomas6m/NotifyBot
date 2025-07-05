# NotifyBot Email Sender

A Python-based bulk email automation tool that sends personalized emails to filtered recipients from CSV inventory data.

## Features

- **Bulk Email Sending**: Send emails to hundreds of recipients with batch processing
- **CSV Filtering**: Filter recipients from inventory CSV files using flexible conditions
- **Email Validation**: Automatic validation of email addresses
- **Attachments Support**: Send multiple file attachments
- **Dry Run Mode**: Preview emails by sending drafts to approvers
- **Deduplication**: Automatic removal of duplicate email addresses
- **Batch Processing**: Send emails in configurable batches with delays
- **Comprehensive Logging**: Colored console output and detailed file logging
- **Multiple Recipients**: Support for TO, CC, and BCC recipients

## Requirements

- Python 3.6+
- Local SMTP server (configured to run on localhost)
- CSV files with inventory data
- Required email template files

## Quick Start

1. **Setup your email folder structure**:
   ```
   your_email_folder/
   ├── from.txt          # Sender email address
   ├── subject.txt       # Email subject
   ├── body.html         # HTML email body
   ├── approver.txt      # Approver email addresses
   ├── inventory.csv     # Recipient data
   ├── filter.txt        # Filter conditions (CSV format)
   ├── to.txt            # Additional recipients (optional)
   ├── cc.txt            # CC recipients (optional)
   ├── bcc.txt           # BCC recipients (optional)
   ├── additional_to.txt # Extra recipients (optional)
   └── attachment/       # Folder for attachments (optional)
       ├── file1.pdf
       └── file2.jpg
   ```

2. **Run dry-run first** (recommended):
   ```bash
   python notifybot.py your_email_folder --dry-run
   ```

3. **Send actual emails**:
   ```bash
   python notifybot.py your_email_folder
   ```

## File Formats

### Required Files

- **from.txt**: Single line with sender email address
- **subject.txt**: Single line with email subject
- **body.html**: HTML formatted email body
- **approver.txt**: One email address per line for approval recipients

### Optional Files

- **inventory.csv**: CSV file with recipient data including 'emailids' column
- **filter.txt**: CSV format filter conditions
- **to.txt**: Additional recipients (one per line)
- **cc.txt**: CC recipients (one per line)
- **bcc.txt**: BCC recipients (one per line)
- **additional_to.txt**: Extra recipients to be merged into to.txt

### Filter File Format

The `filter.txt` file should be in CSV format where:
- First row contains column headers matching your inventory.csv
- Subsequent rows contain filter conditions

Example:
```csv
department,location,status
IT,New York,active
HR,Boston,active
```

## Command Line Options

```bash
python notifybot.py <base_folder> [OPTIONS]

Arguments:
  base_folder           Path to folder containing email files

Options:
  --dry-run            Send draft email to approvers only
  --batch-size N       Number of emails per batch (default: 500)
  --delay N            Seconds between batches (default: 5)
  --log-level LEVEL    Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
```

## Examples

### Basic Usage
```bash
python notifybot.py ./email_campaign
```

### Dry Run with Custom Batch Size
```bash
python notifybot.py ./email_campaign --dry-run --batch-size 100
```

### Debug Mode with Custom Delay
```bash
python notifybot.py ./email_campaign --log-level DEBUG --delay 10
```

## Logging

The script creates detailed logs in:
- **Console**: Colored output showing progress and errors
- **File**: `notifybot.log` with detailed timestamps and function information

## Error Handling

The script includes comprehensive error handling for:
- Missing required files
- Invalid email addresses
- SMTP connection issues
- File read/write errors
- CSV parsing errors

## Security Notes

- Ensure your SMTP server is properly configured
- Review recipient lists before sending
- Use dry-run mode to test campaigns
- Keep logs secure as they contain email addresses

## Support

For issues or questions, check the log files for detailed error information. The script provides clear error messages and suggestions for common problems.
