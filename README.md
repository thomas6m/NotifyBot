# NotifyBot Email Sender

A powerful, RFC-compliant email sending tool designed for bulk email campaigns with advanced filtering, attachment handling, and comprehensive logging capabilities.

## Features

- **RFC-compliant email validation** using `email-validator` library
- **Bulk email sending** with configurable batch sizes and delays
- **Advanced filtering** based on CSV inventory data
- **Attachment handling** with size filtering
- **Comprehensive logging** with detailed error tracking
- **Dry-run mode** for testing before actual sending
- **Email deduplication** to prevent duplicate sends
- **Multi-recipient support** (To, CC, BCC)
- **HTML email support** with plain-text fallback

## Installation

### Prerequisites

- Python 3.6+
- SMTP server (configured on localhost by default)

### Dependencies

Install the required Python packages:

```bash
pip install email-validator
```

## Project Structure

Your project folder should contain the following files:

### Required Files

- `from.txt` - Sender email address
- `subject.txt` - Email subject line
- `body.html` - HTML email body content
- `approver.txt` - List of approver email addresses (one per line)

### Optional Files

- `to.txt` - Primary recipient list (auto-generated if not present)
- `cc.txt` - CC recipient list
- `bcc.txt` - BCC recipient list
- `additional_to.txt` - Additional recipients to append
- `inventory.csv` - CSV data for filtering recipients
- `filter.txt` - CSV filter conditions
- `attachments/` - Directory containing email attachments

## Usage

### Basic Usage

```bash
python notifybot.py /path/to/email/folder
```

### Command Line Options

```bash
python notifybot.py [OPTIONS] BASE_FOLDER
```

#### Options

- `--dry-run` - Send test email to approvers only
- `--batch-size INTEGER` - Number of recipients per batch (default: 500)
- `--delay INTEGER` - Seconds to wait between batches (default: 5)
- `--attachments-folder PATH` - Custom attachments folder path
- `--max-attachment-size INTEGER` - Maximum attachment size in MB (default: 10)

### Examples

#### Dry Run (Testing)
```bash
python notifybot.py --dry-run /path/to/campaign
```

#### Custom Batch Settings
```bash
python notifybot.py --batch-size 100 --delay 10 /path/to/campaign
```

#### With Custom Attachments Folder
```bash
python notifybot.py --attachments-folder /custom/attachments /path/to/campaign
```

## File Formats

### Email Address Files
All email files should contain one email address per line:
```
user1@example.com
user2@example.com
User Name <user3@example.com>
```

### inventory.csv
CSV file containing contact data with an `emailids` column:
```csv
name,department,emailids,status
John Doe,IT,john@example.com;jane@example.com,active
Jane Smith,HR,jane.smith@example.com,active
```

### filter.txt
CSV file defining filter conditions:
```csv
department,status
IT,active
HR,active
```

### HTML Email Body
The `body.html` file should contain valid HTML:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Newsletter</title>
</head>
<body>
    <h1>Welcome!</h1>
    <p>This is your newsletter content.</p>
</body>
</html>
```

## How It Works

1. **Validation**: Checks for required files and validates email addresses
2. **Filtering**: If `inventory.csv` and `filter.txt` exist, generates filtered recipient list
3. **Recipient Management**: 
   - Creates `to.txt` with filtered emails (if it doesn't exist)
   - Appends emails from `additional_to.txt`
   - Deduplicates all recipients
4. **Sending**: Sends emails in batches with specified delays
5. **Logging**: Records all activities in `notifybot.log`

## Logging

All activities are logged to `notifybot.log` with timestamps and detailed information:

- Email validation results
- File operations
- Send attempts and results
- Error messages and warnings

## Error Handling

The script includes comprehensive error handling for:

- Missing or invalid files
- Invalid email addresses
- SMTP connection issues
- Attachment processing errors
- CSV parsing errors

## Security Features

- **Email validation** prevents invalid addresses
- **Attachment size limits** prevent oversized files
- **Dry-run mode** for safe testing
- **Comprehensive logging** for audit trails

## Best Practices

1. **Always test first** using `--dry-run`
2. **Use appropriate batch sizes** to avoid overwhelming SMTP servers
3. **Monitor logs** for any issues during sending
4. **Validate email lists** before large campaigns
5. **Keep attachments small** and relevant

## Troubleshooting

### Common Issues

**Missing Required Files**
```
Error: Missing: from.txt, subject.txt
```
Ensure all required files are present in your base folder.

**Invalid Email Addresses**
```
Warning: Invalid email skipped: bad-email
```
Check and correct email addresses in your recipient files.

**SMTP Connection Issues**
```
Error: Failed to send to [...]: Connection refused
```
Verify your SMTP server is running and accessible.

**Attachment Too Large**
```
Warning: Skipping large-file.pdf: 15.2MB > limit
```
Reduce attachment size or increase the limit with `--max-attachment-size`.

### Log Analysis

Check `notifybot.log` for detailed information about:
- Which emails were sent successfully
- Which emails failed and why
- File processing activities
- Validation results

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source. Please check the license file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the log files
3. Open an issue with detailed information about your problem

---

**Note**: This tool is designed for legitimate email campaigns. Please ensure compliance with anti-spam laws and regulations in your jurisdiction.
