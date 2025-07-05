# NotifyBot

![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

A Python-based automated email notification system for efficient bulk email campaigns with dynamic filtering, batch processing, and built-in safety features.

## 🚀 Features

- **Dynamic Recipient Filtering**: Filter recipients from CSV inventory based on custom conditions
- **Batch Email Sending**: Send emails in configurable batches with delays to prevent server overload
- **Dry-Run Mode**: Test campaigns by sending drafts to approvers only
- **Email Deduplication**: Automatically removes duplicate recipients
- **Comprehensive Logging**: Detailed audit trails for all operations
- **Flexible Configuration**: File-based configuration for easy content management
- **Multiple Recipient Types**: Support for TO, CC, and BCC recipients

## 📋 Requirements

- Python 3.7+
- Local SMTP server (e.g., Postfix, Sendmail)
- CSV inventory file with recipient data
- Required configuration files (see [File Structure](#file-structure))

## 🛠️ Installation

1. Clone or download the NotifyBot script:
```bash
wget https://your-repo/notifybot.py
# or
curl -O https://your-repo/notifybot.py
```

2. Ensure Python 3.7+ is installed:
```bash
python --version
```

3. Set up your local SMTP server (varies by OS):
   - **Linux**: Install and configure Postfix or Sendmail
   - **macOS**: Enable Postfix or install via Homebrew
   - **Windows**: Use IIS SMTP or third-party solutions

## 📁 File Structure

Create your campaign folder with the following structure:

```
your_campaign_folder/
├── inventory.csv          # Required: Recipient data
├── filter.txt            # Required: Filter conditions (CSV format)
├── from.txt              # Required: Sender email address
├── subject.txt           # Required: Email subject line
├── body.html             # Required: Email HTML content
├── approver.txt          # Required: Approver email addresses
├── additional_to.txt     # Optional: Additional recipients
├── cc.txt                # Optional: CC recipients
├── bcc.txt               # Optional: BCC recipients
└── to.txt                # Auto-generated: Final recipient list
```

### File Descriptions

| File | Purpose | Format | Example |
|------|---------|--------|---------|
| `inventory.csv` | Source data with recipient information | CSV with headers including 'emailids' | `name,department,emailids`<br>`John,IT,john@company.com;jane@company.com` |
| `filter.txt` | Filtering conditions | CSV format | `department,status`<br>`IT,active`<br>`HR,active` |
| `from.txt` | Sender email | Single line | `noreply@company.com` |
| `subject.txt` | Email subject | Single line | `Important System Update` |
| `body.html` | Email content | HTML format | `<h1>Hello</h1><p>Message content...</p>` |
| `approver.txt` | Approver emails | One per line | `manager@company.com`<br>`admin@company.com` |

## 🚀 Usage

### Basic Usage

```bash
# Run in dry-run mode (recommended for testing)
python notifybot.py /path/to/campaign_folder --dry-run

# Send actual emails
python notifybot.py /path/to/campaign_folder
```

### Command-Line Options

```bash
python notifybot.py <base_folder> [--dry-run]
```

**Parameters:**
- `base_folder`: Path to folder containing all required files
- `--dry-run`: Optional flag to send draft email only to approvers

### Examples

```bash
# Test your campaign
python notifybot.py ./monthly_newsletter --dry-run

# Execute the campaign
python notifybot.py ./monthly_newsletter

# Using absolute paths
python notifybot.py /home/user/campaigns/security_alert --dry-run
```

## 📊 How It Works

### 1. Preparation Phase
- Validates all required files exist
- Reads configuration from individual files
- Parses filter conditions and inventory data

### 2. Recipient Processing
- Applies filters to inventory.csv to extract matching recipients
- Combines with additional recipients from additional_to.txt
- Deduplicates email addresses and saves to to.txt

### 3. Email Sending
- **Dry-run**: Sends draft with "[DRAFT]" prefix to approvers only
- **Live**: Sends emails in batches (500 per batch) with 5-second delays
- Logs all operations for audit purposes

### 4. Filtering Logic
The system matches rows in inventory.csv where all filter conditions are met:
```csv
# filter.txt
department,status
IT,active
HR,active

# This will match inventory rows where:
# department = "IT" AND status = "active"
# OR department = "HR" AND status = "active"
```

## 📝 Configuration Examples

### Sample inventory.csv
```csv
name,department,status,emailids
John Doe,IT,active,john.doe@company.com
Jane Smith,HR,active,jane.smith@company.com;jane.personal@gmail.com
Bob Johnson,IT,inactive,bob.johnson@company.com
Alice Brown,Marketing,active,alice.brown@company.com
```

### Sample filter.txt
```csv
department,status
IT,active
HR,active
```

### Sample from.txt
```
notifications@company.com
```

### Sample subject.txt
```
Monthly Security Update - Action Required
```

### Sample body.html
```html
<!DOCTYPE html>
<html>
<head>
    <title>Security Update</title>
</head>
<body>
    <h1>Important Security Update</h1>
    <p>Dear Team,</p>
    <p>Please review the attached security guidelines...</p>
    <p>Best regards,<br>IT Security Team</p>
</body>
</html>
```

## 📋 Logging

NotifyBot creates a `notifybot.log` file with detailed information:

```
2024-01-15 10:30:45 - INFO - send_email_from_folder [line 125] - --- Start sending emails from ./campaign ---
2024-01-15 10:30:45 - INFO - get_filtered_emailids [line 89] - Found 25 matching recipients
2024-01-15 10:30:45 - INFO - send_email [line 108] - Sent to admin@company.com
2024-01-15 10:30:50 - INFO - send_email [line 108] - Sent to john@company.com, jane@company.com
```

## ⚠️ Important Notes

### Security Considerations
- Ensure your SMTP server is properly configured and secured
- Protect sensitive email lists and configuration files
- Use appropriate file permissions on campaign folders
- Consider using environment variables for sensitive data

### Best Practices
- Always test with `--dry-run` before sending to actual recipients
- Keep backup copies of your inventory and configuration files
- Monitor the log file for any errors or issues
- Test with small batches before large campaigns
- Verify email content and formatting before deployment

### Limitations
- Requires a local SMTP server for email delivery
- Email formatting is limited to HTML content
- No built-in email template system
- Batch size is fixed at 500 (can be modified in code)

## 🔧 Troubleshooting

### Common Issues

**"Missing required files" error:**
```bash
# Ensure all required files exist in your campaign folder
ls -la your_campaign_folder/
```

**SMTP connection errors:**
```bash
# Check if your SMTP server is running
sudo systemctl status postfix  # Linux
sudo systemctl status sendmail # Linux alternative
```

**No recipients found:**
- Verify your filter.txt conditions match data in inventory.csv
- Check that inventory.csv has an 'emailids' column
- Ensure email addresses are properly formatted

**Permission errors:**
```bash
# Fix file permissions
chmod 644 your_campaign_folder/*
chmod 755 your_campaign_folder/
```

### Debug Mode
For detailed debugging, check the `notifybot.log` file:
```bash
tail -f notifybot.log
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For issues and questions:
- Check the troubleshooting section
- Review the log file for error details
- Create an issue in the repository

## 📈 Changelog

### v1.0.0
- Initial release
- Basic email sending functionality
- Dry-run mode
- CSV filtering
- Batch processing
- Comprehensive logging

---

**⚡ Quick Start Checklist:**

- [ ] Python 3.7+ installed
- [ ] SMTP server configured
- [ ] Campaign folder created with required files
- [ ] Tested with `--dry-run` flag
- [ ] Verified email content and recipients
- [ ] Ready to send!

*Happy emailing! 📧*
