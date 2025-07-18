# NotifyBot Directory Structure

```
/notifybot/                    # Root directory for NotifyBot
    ├── logs/                  # Log folder for NotifyBot
    │   └── notifybot.log      # Main log file for NotifyBot (log rotation will create new files like notifybot_YYYYMMDD_HHMMSS.log)
    ├── scripts/               # Folder for all scripts
    │   └── notifybot.py       # The main script to send emails (NotifyBot)
    ├── basefolder/            # The base folder for user-specific email configurations
    │   └── emails/            # Example user-specific folder for email configurations
    │       ├── subject.txt    # Email subject (plain text)
    │       ├── body.html      # HTML content for the email body
    │       ├── from.txt       # Sender's email address (e.g., sender@example.com)
    │       ├── approver.txt   # Email addresses for approvers in dry-run mode (semicolon separated list)
    │       ├── to.txt         # Recipient list (semicolon separated list or one email per line)
    │       ├── filter.txt     # Filter criteria for recipient selection
    │       └── attachments/    # Folder for any attachments to be included in the email
    │           ├── file1.pdf  # Example attachment file
    │           └── image.png  # Example attachment file
    ├── inventory/             # Folder for the inventory.csv file
    │   └── inventory.csv     # Full list of potential recipients
```

## Directory Descriptions

### `/notifybot/`
Root directory containing all NotifyBot components and data.

### `/notifybot/logs/`
Contains all log files for the NotifyBot system:
- `notifybot.log` - Main log file (with log rotation creating timestamped files)

### `/notifybot/scripts/`
Contains executable scripts:
- `notifybot.py` - Main email sending script

### `/notifybot/basefolder/`
Base directory for email configurations. Each subdirectory represents a different email campaign or configuration set.

### `/notifybot/basefolder/emails/`
Example email configuration directory containing:
- `subject.txt` - Email subject line
- `body.html` - HTML email body content
- `from.txt` - Sender email address
- `approver.txt` - Approver email addresses (semicolon separated)
- `to.txt` - Recipient email addresses (semicolon separated or one per line)
- `filter.txt` - Recipient filtering criteria
- `attachments/` - Directory for email attachments

### `/notifybot/inventory/`
Contains recipient data:
- `inventory.csv` - Master list of all potential email recipients
