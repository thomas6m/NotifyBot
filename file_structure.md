# NotifyBot Directory Structure

```
/notifybot
│
├── /basefolder                # Base folder containing input files for emails
│   ├── subject.txt            # Email subject text file
│   ├── body.html              # HTML body of the email
│   ├── from.txt               # Sender (From) address
│   ├── approver.txt           # Approver emails (for dry-run mode)
│   ├── to.txt                 # List of recipient emails (required for real email mode)
│   ├── filter.txt             # Optional filter file for filtering recipients
│   ├── additional_to.txt      # Optional file for additional recipients
│   ├── inventory.csv          # Inventory CSV file for filtering (used with filter.txt)
│   └── attachment             # Folder for attachments (default subfolder for attachments)
│
├── /inventory                 # Folder for inventory files
│   └── inventory.csv          # CSV file containing email inventory (required for filtering)
│
├── /logs                      # Logs folder for storing execution logs
│   └── notifybot.log          # Log file for NotifyBot operations
│
├── /scripts                   # Folder for all scripts
│   └── notifybot.py           # Main Python script to run the NotifyBot
│
├── requirements.txt           # Python dependencies for the project (e.g., email_validator, etc.)
└── README.md                  # Documentation for the project

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
