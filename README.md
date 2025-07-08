# NotifyBot

**NotifyBot** is an automated email batch sender with filtering, logging, and dry-run support. It allows you to send HTML emails with attachments to multiple recipients in batches, with optional filtering based on CSV inventory data.

## Features

- **Batch Email Sending**: Send emails in configurable batches with delays
- **HTML Email Support**: Send rich HTML emails with attachments
- **Email Filtering**: Filter recipients based on CSV inventory data using flexible conditions
- **Dry Run Mode**: Test your email configuration without actually sending emails
- **Email Validation**: Automatic validation of email addresses
- **Attachment Support**: Add multiple file attachments (up to 15MB per file)
- **Logging**: Comprehensive logging with automatic log rotation
- **Deduplication**: Automatic removal of duplicate email addresses

## Installation

### Prerequisites

- Python 3.6 or higher
- `email-validator` library

### Install Dependencies

```bash
pip install email-validator
```

## Project Structure

```
project/
├── notifybot.py           # Main script
└── base/                  # Required base directory
    ├── body.html         # Email body (HTML format) - REQUIRED
    ├── subject.txt       # Email subject line - REQUIRED
    ├── to.txt            # Recipient email addresses (optional)
    ├── inventory.csv     # CSV data for filtering (optional)
    ├── filter.txt        # Filter conditions (optional)
    └── attachment/       # Folder containing attachments (optional)
```

## Usage

### Basic Usage

```bash
# Dry run (simulate sending without actual SMTP)
python notifybot.py --dry-run

# Send emails with default settings
python notifybot.py

# Custom attachment folder
python notifybot.py --attachment-folder attachments

# Custom batch size and delay
python notifybot.py --batch-size 50 --delay 2.0
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run` | Simulate sending emails without actual SMTP send | False |
| `--attachment-folder` | Subfolder name containing attachments | "attachment" |
| `--batch-size` | Number of emails to send per batch | 30 |
| `--delay` | Delay in seconds between batches | 1.0 |

## File Formats

### Required Files

#### `body.html`
HTML content for the email body.

```html
<!DOCTYPE html>
<html>
<head>
    <title>Your Email</title>
</head>
<body>
    <h1>Hello!</h1>
    <p>This is your email content.</p>
</body>
</html>
```

#### `subject.txt`
Plain text file containing the email subject line.

```
Your Email Subject Here
```

### Optional Files

#### `to.txt`
Email addresses separated by semicolons, newlines, or both.

```
user1@example.com; user2@example.com
user3@example.com
```

#### `inventory.csv`
CSV file containing data for filtering recipients. Must include an `emailids` column.

```csv
name,department,emailids
John Doe,Engineering,john@example.com
Jane Smith,Marketing,jane@example.com; jane.smith@company.com
```

#### `filter.txt`
CSV file defining filter conditions for the inventory data.

```csv
field,value,mode,regex_flags
department,Engineering,exact,
name,John,contains,
```

**Filter Modes:**
- `exact`: Exact match (case-insensitive)
- `contains`: Value contains the specified string (case-insensitive)
- `regex`: Regular expression match

**Regex Flags:**
- `I`: Case-insensitive
- `M`: Multiline
- `S`: Dotall
- Multiple flags can be combined with `|` (e.g., `I|M`)

## Email Filtering

When both `inventory.csv` and `filter.txt` are present, NotifyBot will:

1. Apply all filter conditions to the inventory data
2. Extract email addresses from matching rows
3. Validate all email addresses
4. Exclude emails already present in `to.txt`
5. Append new filtered emails to `to.txt`
6. Deduplicate the `to.txt` file

## Logging

NotifyBot creates detailed logs in `notifybot.log` with:

- Timestamp and log level
- Function name and line number
- Detailed error messages and warnings
- Email sending status

Log files are automatically rotated on each run with timestamp suffixes.

## Email Configuration

NotifyBot uses localhost SMTP server by default. The sender email is set to `notifybot@example.com`.

To use a different SMTP configuration, modify the `send_email` function in the code.

## File Size Limits

- Maximum attachment size: 15MB per file
- Files exceeding this limit will be skipped with a warning

## Error Handling

NotifyBot includes comprehensive error handling for:

- Missing required files
- Invalid email addresses
- SMTP connection issues
- File reading errors
- Attachment processing errors

## Examples

### Basic Email Campaign

1. Create the base directory structure:
```
base/
├── body.html
├── subject.txt
└── to.txt
```

2. Run with dry-run first:
```bash
python notifybot.py --dry-run
```

3. Send emails:
```bash
python notifybot.py
```

### Filtered Email Campaign

1. Create the complete directory structure:
```
base/
├── body.html
├── subject.txt
├── inventory.csv
├── filter.txt
└── attachment/
    └── document.pdf
```

2. Run to generate filtered recipients:
```bash
python notifybot.py --dry-run
```

3. Send emails to filtered recipients:
```bash
python notifybot.py --batch-size 20 --delay 2.0
```

## Security Notes

- Always test with `--dry-run` first
- Validate your recipient lists before sending
- Be mindful of email sending limits and spam policies
- Consider using authentication for production SMTP servers

## Troubleshooting

### Common Issues

1. **"Missing required files"**: Ensure `body.html` and `subject.txt` exist in the `base/` directory
2. **"No recipients found"**: Check that `to.txt` contains valid email addresses or that filtering is working correctly
3. **SMTP errors**: Verify your SMTP server configuration and network connectivity
4. **Large attachments skipped**: Files over 15MB are automatically skipped

### Debug Steps

1. Check the log file `notifybot.log` for detailed error messages
2. Use `--dry-run` to test configuration without sending emails
3. Verify file encodings are UTF-8
4. Ensure email addresses are properly formatted
