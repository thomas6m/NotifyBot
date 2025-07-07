# NotifyBot - Enhanced Email Notification System

## Overview

NotifyBot is a robust Python-based email notification system that automates bulk email sending with advanced filtering, validation, and retry mechanisms. It supports batch processing, file attachments, CSV-based recipient filtering, and comprehensive logging.

## Features

- **Batch Email Processing**: Send emails in configurable batches with retry logic
- **Advanced Filtering**: Filter recipients based on CSV data with multiple match modes
- **Email Validation**: Validate email addresses before sending
- **Attachment Support**: Automatically attach files with size and security checks
- **Logging & Monitoring**: Comprehensive logging with automatic log rotation
- **Dry Run Mode**: Test configurations without sending actual emails
- **Error Handling**: Robust error handling with retry mechanisms

## Installation

### Prerequisites

```bash
pip install email-validator
```

### Dependencies

- Python 3.7+
- Standard library modules: `os`, `csv`, `re`, `time`, `logging`, `email`, `smtplib`
- Third-party: `email-validator`

## Project Structure

```
project_root/
├── notifybot.py           # Main script
├── email/                 # Email configuration folder
│   ├── subject.txt        # Email subject template
│   ├── body.txt          # Email body template
│   ├── to.txt            # Direct recipient list
│   ├── inventory.csv     # Data source for filtering
│   ├── filter.txt        # Filtering criteria (CSV format)
│   └── attachments/      # Files to attach
│       ├── file1.pdf
│       └── file2.jpg
└── logs/
    └── notifybot.log     # Application logs
```

## Configuration Files

### 1. subject.txt
```
Your Email Subject Here
```

### 2. body.txt
```
Dear Recipient,

Your email body content goes here.
This can be multiline text with HTML formatting if needed.

Best regards,
Your Team
```

### 3. to.txt
```
user1@example.com
user2@example.com;user3@example.com
```

### 4. inventory.csv
```csv
name,emailids,department,status
John Doe,john@example.com,Engineering,active
Jane Smith,jane@example.com;jane.alt@example.com,Marketing,active
Bob Johnson,bob@example.com,Sales,inactive
```

### 5. filter.txt
```csv
field,value,mode,regex_flags
department,Engineering,exact,
status,active,exact,
name,.*Smith.*,regex,IGNORECASE
```

## Usage

### Command Line Interface

NotifyBot provides a comprehensive CLI with various options for different use cases:

```bash
# Basic usage - send emails from default folder
python notifybot.py

# Show help and all available options
python notifybot.py --help

# Dry run mode (recommended for testing)
python notifybot.py --dry-run

# Custom folder and batch size
python notifybot.py --folder /path/to/email --batch-size 25

# Advanced configuration
python notifybot.py --folder email --batch-size 15 --retries 5 --delay 2 --dry-run
```

### CLI Options Reference

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--folder` | `-f` | string | `"email"` | Base folder containing email configuration |
| `--batch-size` | `-b` | integer | `10` | Number of emails to send in each batch |
| `--retries` | `-r` | integer | `3` | Number of retry attempts on failure |
| `--delay` | `-d` | integer | `3` | Delay in seconds between retry attempts |
| `--dry-run` | `-n` | flag | `False` | Simulate sending without actual delivery |
| `--smtp-server` | `-s` | string | `"localhost"` | SMTP server hostname |
| `--smtp-port` | `-p` | integer | `587` | SMTP server port |
| `--smtp-user` | `-u` | string | `None` | SMTP username |
| `--smtp-pass` | `-w` | string | `None` | SMTP password |
| `--use-tls` | `-t` | flag | `True` | Enable TLS encryption |
| `--log-level` | `-l` | string | `"INFO"` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `--max-attachment-size` | `-m` | integer | `15` | Maximum attachment size in MB |
| `--recipients-file` | | string | `"to.txt"` | Custom recipients file name |
| `--subject-file` | | string | `"subject.txt"` | Custom subject file name |
| `--body-file` | | string | `"body.txt"` | Custom body file name |
| `--filter-file` | | string | `"filter.txt"` | Custom filter file name |
| `--inventory-file` | | string | `"inventory.csv"` | Custom inventory file name |
| `--delimiter` | | string | `";"` | Email delimiter in files |
| `--encoding` | | string | `"utf-8"` | File encoding |
| `--validate-domains` | | flag | `False` | Validate email domains (requires DNS) |
| `--skip-duplicates` | | flag | `True` | Skip duplicate email addresses |
| `--compress-attachments` | | flag | `False` | Compress attachments before sending |
| `--timeout` | | integer | `30` | SMTP connection timeout in seconds |
| `--config` | `-c` | string | `None` | Load settings from JSON config file |
| `--version` | `-v` | flag | | Show version information |
| `--quiet` | `-q` | flag | `False` | Suppress console output |
| `--verbose` | | flag | `False` | Enable verbose logging |

### CLI Examples

#### 1. Basic Dry Run Test
```bash
# Test configuration without sending emails
python notifybot.py --dry-run --verbose
```

#### 2. Production Email Send
```bash
# Send emails in production with custom settings
python notifybot.py \
    --folder /opt/notifybot/campaigns/newsletter \
    --batch-size 50 \
    --retries 3 \
    --delay 5 \
    --smtp-server smtp.gmail.com \
    --smtp-port 587 \
    --smtp-user notifications@company.com \
    --use-tls
```

#### 3. Large Volume Processing
```bash
# Process large email lists with optimization
python notifybot.py \
    --folder campaigns/bulk \
    --batch-size 100 \
    --retries 5 \
    --delay 1 \
    --max-attachment-size 10 \
    --compress-attachments \
    --skip-duplicates \
    --timeout 60
```

#### 4. Development Testing
```bash
# Full development test with custom files
python notifybot.py \
    --folder test_emails \
    --dry-run \
    --batch-size 5 \
    --recipients-file test_recipients.txt \
    --subject-file test_subject.txt \
    --body-file test_body.html \
    --log-level DEBUG \
    --verbose
```

#### 5. Secure Production Setup
```bash
# Production with environment variables for security
export SMTP_USER="notifications@company.com"
export SMTP_PASS="app_password_here"

python notifybot.py \
    --folder production/weekly_report \
    --batch-size 25 \
    --smtp-server smtp.gmail.com \
    --smtp-port 587 \
    --smtp-user $SMTP_USER \
    --smtp-pass $SMTP_PASS \
    --use-tls \
    --validate-domains \
    --log-level INFO
```

#### 6. Configuration File Usage
```bash
# Use JSON configuration file
python notifybot.py --config config/production.json

# Example production.json:
{
    "folder": "campaigns/monthly",
    "batch_size": 30,
    "retries": 3,
    "delay": 2,
    "smtp_server": "smtp.company.com",
    "smtp_port": 587,
    "smtp_user": "notifications@company.com",
    "use_tls": true,
    "max_attachment_size": 20,
    "log_level": "INFO",
    "validate_domains": true,
    "skip_duplicates": true
}
```

#### 7. Debugging and Monitoring
```bash
# Debug mode with detailed logging
python notifybot.py \
    --folder debug_test \
    --dry-run \
    --log-level DEBUG \
    --verbose \
    --batch-size 1 \
    --timeout 10
```

#### 8. Custom File Locations
```bash
# Use custom file names and locations
python notifybot.py \
    --folder /data/email_campaigns \
    --recipients-file customer_emails.txt \
    --subject-file promo_subject.txt \
    --body-file promo_body.html \
    --filter-file vip_filter.csv \
    --inventory-file customer_database.csv \
    --delimiter "," \
    --encoding "utf-8"
```

#### 9. Quick Status Check
```bash
# Check version and configuration
python notifybot.py --version
python notifybot.py --help
```

#### 10. Batch Processing with Monitoring
```bash
# Process with minimal console output but full logging
python notifybot.py \
    --folder campaigns/newsletter \
    --batch-size 40 \
    --quiet \
    --log-level INFO \
    --retries 3 \
    --delay 3 \
    > /dev/null 2>&1 &

# Monitor progress
tail -f notifybot.log
```

### Environment Variables

For secure credential management, NotifyBot supports environment variables:

```bash
# SMTP Configuration
export NOTIFYBOT_SMTP_SERVER="smtp.gmail.com"
export NOTIFYBOT_SMTP_PORT="587"
export NOTIFYBOT_SMTP_USER="your_email@gmail.com"
export NOTIFYBOT_SMTP_PASS="your_app_password"

# Default Settings
export NOTIFYBOT_BATCH_SIZE="20"
export NOTIFYBOT_RETRIES="3"
export NOTIFYBOT_DELAY="2"
export NOTIFYBOT_LOG_LEVEL="INFO"

# Run with environment variables
python notifybot.py --folder campaigns/weekly
```

### Basic Programmatic Usage

```python
from notifybot import send_email_from_folder

# Send emails with default settings
send_email_from_folder("email")

# Dry run mode (recommended for testing)
send_email_from_folder("email", dry_run=True)

# Custom batch size and retries
send_email_from_folder(
    base_folder="email",
    dry_run=False,
    batch_size=20,
    retries=5,
    delay=2
)
```

## Advanced Configuration

### Filtering Modes

| Mode | Description | Example |
|------|-------------|---------|
| `exact` | Case-insensitive exact match | `status = "active"` |
| `contains` | Substring match | `name contains "John"` |
| `regex` | Regular expression match | `email matches ".*@company\.com"` |

### Regex Flags

Supported regex flags for advanced pattern matching:
- `IGNORECASE`: Case-insensitive matching
- `MULTILINE`: Multi-line mode
- `DOTALL`: Dot matches newlines
- `VERBOSE`: Verbose regex mode

### SMTP Configuration

Modify the `send_email` function to configure SMTP settings:

```python
def send_email(
    recipients,
    subject,
    body,
    attachments,
    smtp_server="smtp.gmail.com",  # Custom SMTP server
    smtp_port=587,                 # Custom port
    username="your_email@gmail.com",
    password="your_app_password",
    use_tls=True
):
    # Enhanced SMTP configuration
```

## API Reference

### Core Functions

#### `send_email_from_folder(base_folder, dry_run=False, batch_size=10, retries=3, delay=3)`

Main orchestrator function for sending emails.

**Parameters:**
- `base_folder` (str): Path to email configuration folder
- `dry_run` (bool): If True, simulates sending without actual email delivery
- `batch_size` (int): Number of emails to send in each batch
- `retries` (int): Number of retry attempts on failure
- `delay` (int): Delay in seconds between retry attempts

#### `read_recipients(path, delimiters=";")`

Reads and validates recipient emails from a file.

**Parameters:**
- `path` (Path): Path to recipient file
- `delimiters` (str): Characters used to separate multiple emails

**Returns:**
- `List[str]`: List of validated email addresses

#### `get_filtered_emailids(base_path, delimiters=";")`

Filters email addresses based on CSV data and filtering criteria.

**Parameters:**
- `base_path` (Path): Base directory containing inventory.csv and filter.txt
- `delimiters` (str): Email separation characters

**Returns:**
- `List[str]`: List of filtered email addresses

### Utility Functions

#### `is_valid_email(email)`

Validates email address format using email-validator library.

#### `sanitize_filename(filename)`

Converts filenames to ASCII-safe format for email attachments.

#### `rotate_log_file()`

Rotates log files with timestamp suffixes to prevent unlimited growth.

## Error Handling

### Custom Exceptions

```python
class MissingRequiredFilesError(Exception):
    """Raised when required input files are missing."""
    pass
```

### Common Error Scenarios

1. **Missing Required Files**: Script validates presence of subject.txt and body.txt
2. **Invalid Email Addresses**: Malformed emails are logged and skipped
3. **Large Attachments**: Files larger than 15MB are skipped with warnings
4. **SMTP Failures**: Automatic retry with exponential backoff
5. **CSV Parsing Errors**: Graceful handling of malformed CSV data

## Logging

### Log Levels

- **INFO**: Normal operations, successful sends
- **WARNING**: Skipped emails, large attachments
- **ERROR**: Failed sends, missing files, validation errors

### Log Format

```
2025-07-07 12:00:00,123 - INFO - send_email:245 - Successfully sent email to 5 recipients
2025-07-07 12:00:01,456 - WARNING - read_recipients:89 - Skipped invalid email: invalid@
2025-07-07 12:00:02,789 - ERROR - send_email:267 - Failed to send email: Connection refused
```

### Log Rotation

Logs are automatically rotated with timestamp suffixes:
- `notifybot.log` (current)
- `notifybot_20250707_120000.log` (archived)

## Performance Optimization

### Batch Processing

```python
# Optimal batch sizes for different scenarios
send_email_from_folder("email", batch_size=50)  # High-volume
send_email_from_folder("email", batch_size=10)  # Standard
send_email_from_folder("email", batch_size=5)   # Conservative
```

### Memory Management

- Files are read in chunks to handle large attachments
- Email lists are processed incrementally
- Automatic cleanup of temporary objects

## Security Considerations

### Email Validation

- Comprehensive email format validation
- Domain existence checking (optional)
- Blacklist support for blocked domains

### Attachment Security

- File size limits (15MB default)
- Filename sanitization
- MIME type validation
- Virus scanning integration points

### Data Protection

- Secure credential storage
- Encrypted SMTP connections
- Audit trail logging
- PII handling compliance

## Testing

### Unit Tests

```python
import unittest
from notifybot import is_valid_email, sanitize_filename

class TestNotifyBot(unittest.TestCase):
    def test_email_validation(self):
        self.assertTrue(is_valid_email("user@example.com"))
        self.assertFalse(is_valid_email("invalid-email"))
    
    def test_filename_sanitization(self):
        self.assertEqual(sanitize_filename("test file.pdf"), "test_file.pdf")
```

### Integration Tests

```python
# Test with sample data
send_email_from_folder("test_email", dry_run=True, batch_size=2)
```

## Monitoring & Maintenance

### Health Checks

- Monitor log file growth
- Track email delivery rates
- Alert on consecutive failures
- Validate configuration integrity

### Performance Metrics

- Emails sent per minute
- Batch processing time
- Retry rate analysis
- Attachment size distribution

## Troubleshooting

### Common Issues

1. **SMTP Connection Errors**
   - Check firewall settings
   - Verify SMTP server credentials
   - Test network connectivity

2. **Invalid Email Addresses**
   - Review email validation logs
   - Check source data quality
   - Validate email list format

3. **Large File Attachments**
   - Monitor attachment size warnings
   - Implement file compression
   - Use cloud storage links

4. **Performance Issues**
   - Adjust batch sizes
   - Optimize filtering queries
   - Monitor memory usage

### Debug Mode

Enable verbose logging for troubleshooting:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## Best Practices

### Configuration Management

1. **Environment Variables**: Store sensitive credentials in environment variables
2. **Configuration Files**: Use JSON/YAML for complex configurations
3. **Version Control**: Track configuration changes
4. **Backup Strategy**: Regular backups of recipient lists and templates

### Email Deliverability

1. **Sender Reputation**: Use authenticated SMTP servers
2. **Content Quality**: Avoid spam trigger words
3. **Unsubscribe Handling**: Implement unsubscribe mechanisms
4. **Bounce Handling**: Process delivery failures

### Scalability

1. **Database Integration**: Move from CSV to database for large datasets
2. **Queue System**: Implement message queuing for high volumes
3. **Microservices**: Split into smaller, focused services
4. **Cloud Deployment**: Use cloud services for scalability

## Contributing

### Development Setup

```bash
git clone <repository>
cd notifybot
pip install -r requirements.txt
python -m pytest tests/
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Add docstrings for all functions
- Maintain test coverage above 80%

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Changelog

### v2.0.0 (2025-07-07)
- Added advanced filtering with regex support
- Implemented batch processing with retry logic
- Enhanced logging with rotation
- Added attachment security checks
- Improved error handling

### v1.0.0 (2025-01-01)
- Initial release
- Basic email sending functionality
- CSV-based recipient management
- Simple attachment support
