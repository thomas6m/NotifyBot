# NotifyBot Documentation

## Overview

NotifyBot is a Python-based automated email notification system designed to efficiently manage and send targeted email campaigns. The system processes recipient lists dynamically based on filters, supports batch email sending, and includes a dry-run mode for safe testing. It is ideal for organizations needing to send bulk emails that require pre-approval and controlled delivery.

## Key Features

### Dynamic Recipient Filtering
- Reads an inventory CSV and applies filters defined in a filter file to extract relevant recipient email addresses automatically
- Supports complex filtering conditions to target specific audience segments

### Flexible Email Composition
- Email components such as sender address, subject, and HTML body are read from separate files
- Allows easy updates without code changes
- Supports dynamic content management

### Batch Email Sending
- Sends emails in configurable batches (default 500 recipients per batch)
- Includes delays between batches to prevent server overload and avoid spam filtering
- Optimized for high-volume email campaigns

### Approver Review & Dry-Run Mode
- Supports a dry-run mode that prepares the recipient list and sends a draft email only to designated approvers
- Validates content and recipients before actual campaign delivery
- Prevents accidental mass email sending during testing

### Email Deduplication
- Automatically deduplicates email addresses to ensure recipients do not receive multiple emails
- Maintains clean recipient lists across multiple campaign runs

### Comprehensive Logging & Error Handling
- Detailed logging of all operations including file read/write errors, email send status, and validation checks
- Enables audit trails and troubleshooting capabilities
- Logs stored in `notifybot.log` with timestamps and function-level details

### Extensible Recipient Lists
- Supports additional recipient files (`additional_to.txt`, `cc.txt`, `bcc.txt`) for flexible campaign customization
- Allows for complex email routing scenarios

## How It Works

### 1. Preparation Phase
NotifyBot expects a base folder containing the following required files:

| File | Purpose |
|------|---------|
| `from.txt` | Sender email address |
| `subject.txt` | Email subject line |
| `body.html` | Email HTML body content |
| `approver.txt` | List of approvers for dry-run validation |
| `inventory.csv` | Recipient data source |
| `filter.txt` | Filter conditions for recipient selection |

### 2. Recipient Extraction
- Parses `inventory.csv` using filter conditions defined in `filter.txt`
- Generates a targeted list of email addresses based on the specified criteria
- Applies business logic to ensure accurate recipient selection

### 3. Recipient List Management
- Combines filtered recipients with any additional recipients from `additional_to.txt`
- Performs deduplication to eliminate duplicate email addresses
- Saves the final recipient list in `to.txt`

### 4. Dry-Run Mode Operation
When invoked with `--dry-run`, NotifyBot:
- Updates `to.txt` with filtered and additional recipients
- Sends a draft email only to the approvers listed in `approver.txt`
- Does not send bulk emails to actual recipients
- Allows for content and recipient validation before full deployment

### 5. Production Email Sending
In normal mode, NotifyBot:
- Loads final recipients from `to.txt` and optionally `cc.txt` and `bcc.txt`
- Sends emails in configurable batches to avoid server overload
- Logs send progress and outcomes for audit purposes
- Implements error handling for failed deliveries

## Usage

### Basic Command Structure
```bash
python notifybot.py /path/to/base_folder [--dry-run]
```

### Parameters
- `base_folder`: Path to the folder containing all required files
- `--dry-run` (optional): Sends draft email only to approvers, skips bulk sending

### Examples
```bash
# Run in dry-run mode for testing
python notifybot.py ./campaign_folder --dry-run

# Execute full email campaign
python notifybot.py ./campaign_folder
```

## File Structure Requirements

Your base folder must contain the following structure:

```
base_folder/
├── inventory.csv          # Required: Recipient data source
├── filter.txt            # Required: Filter conditions
├── from.txt              # Required: Sender email
├── subject.txt           # Required: Email subject
├── body.html             # Required: Email HTML body
├── approver.txt          # Required: Approver email list
├── to.txt                # Auto-created: Final recipient list
├── additional_to.txt     # Optional: Additional recipients
├── cc.txt                # Optional: CC recipients
└── bcc.txt               # Optional: BCC recipients
```

## Technical Implementation

### Core Components

#### 1. Imports and Setup
```python
import os, csv, re, time, logging, smtplib, sys
from email.message import EmailMessage
from pathlib import Path
from typing import List, Tuple, Dict
```

#### 2. Logging Configuration
- Logs all operations to `notifybot.log`
- Includes timestamps, log levels, function names, and line numbers
- Supports debugging and audit requirements

#### 3. Custom Exception Handling
```python
class MissingRequiredFilesError(Exception):
    """Custom exception for missing required files."""
    pass
```

#### 4. File Utilities
- `read_file()`: Reads single files (subject, body, etc.)
- `read_recipients()`: Processes recipient lists from text files
- `write_to_txt()`: Appends email addresses to files
- `deduplicate_file()`: Removes duplicates and blank lines

#### 5. Filtering Engine
- `parse_filter_file()`: Parses filter conditions from `filter.txt`
- `get_filtered_emailids()`: Extracts matching email IDs from inventory
- Supports complex filtering logic for targeted campaigns

#### 6. Email Sending
- Uses `smtplib.SMTP('localhost')` for email delivery
- Requires local mail server configuration
- Implements batch sending with configurable delays
- Comprehensive error handling and logging

## Operating Modes

### Dry-Run Mode (`--dry-run`)
- **Purpose**: Testing and validation
- **Process**: Prepares recipient lists and sends draft only to approvers
- **Output**: No bulk emails sent to actual recipients
- **Use Case**: Content validation and recipient verification

### Production Mode (default)
- **Purpose**: Full campaign execution
- **Process**: Sends emails in batches to all recipients
- **Output**: Bulk emails delivered to `to.txt` recipients with optional CC/BCC
- **Use Case**: Actual campaign delivery

## Benefits

### Operational Efficiency
- Automates complex email targeting based on dynamic data filters
- Reduces manual effort in campaign management
- Streamlines the email delivery process

### Campaign Accuracy
- Improves targeting precision through sophisticated filtering
- Pre-validates recipients and content before delivery
- Reduces delivery errors and improves engagement rates

### Risk Mitigation
- Prevents accidental mass emails during testing through dry-run mode
- Implements safeguards against common email campaign mistakes
- Provides audit trails for compliance and troubleshooting

### Maintenance Simplicity
- Separates email content from code logic
- Enables non-technical users to update content
- Supports version control for campaign assets

### Scalability
- Handles large recipient lists efficiently
- Configurable batch sizes for different server capacities
- Supports enterprise-level email campaigns

## Best Practices

### File Management
- Keep all campaign files in organized folders
- Use descriptive naming conventions for different campaigns
- Maintain version control for email content and filters

### Testing
- Always run dry-run mode before production campaigns
- Verify approver email addresses are current
- Test with small batches before full deployment

### Monitoring
- Regularly check `notifybot.log` for issues
- Monitor email delivery rates and errors
- Set up alerts for failed campaigns

### Security
- Secure email credentials and server access
- Limit access to campaign folders and sensitive data
- Follow email authentication best practices

## Troubleshooting

### Common Issues
- **Missing Files**: Ensure all required files exist in the base folder
- **Email Server**: Verify local SMTP server is running and configured
- **Permissions**: Check file and folder permissions
- **Filtering**: Validate filter syntax and inventory CSV format

### Log Analysis
- Check `notifybot.log` for detailed error messages
- Review function-level logging for specific issues
- Use timestamps to track campaign progress

---

*NotifyBot provides a robust, scalable solution for automated email campaigns with built-in safety features and comprehensive logging capabilities.*
