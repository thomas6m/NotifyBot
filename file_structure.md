# NotifyBot Directory Structure

```
/notifybot
│
├── /basefolder                
│   ├── subject.txt            # Email subject text file
│   ├── body.html              # HTML body of the email
│   ├── from.txt               # Sender (From) address
│   ├── approver.txt           # Approver emails (for dry-run mode)
│   ├── to.txt                 # List of recipient emails (required for real email mode)
│   ├── filter.txt             # Optional filter file for filtering recipients
│   ├── additional_to.txt      # Optional file for additional recipients
│   ├── inventory.csv          # Inventory CSV file for filtering (used with filter.txt)
│   ├── attachment             # Folder for attachments
│   │   ├── report1.pdf        # Example attachment (PDF)
│   │   ├── image1.jpg         # Example attachment (JPEG image)
│   │   ├── document.txt       # Example attachment (text document)
│   │   └── invoice.xlsx       # Example attachment (Excel spreadsheet)
│
├── /inventory                 
│   └── inventory.csv          
│
├── /logs                      
│   └── notifybot.log          
│
├── /scripts                   
│   └── notifybot.py           
│
├── requirements.txt           
└── README.md                  
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
