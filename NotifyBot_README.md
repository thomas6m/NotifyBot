# NotifyBot Project Documentation

## Overview
NotifyBot is a Python-based email automation tool designed to send bulk emails with filtering capabilities. It provides a draft approval workflow and supports batch processing to manage large recipient lists efficiently.

## Features
- **Filtered Email Recipients**: Automatically filter recipients from a CSV inventory based on specified conditions
- **Draft Approval Workflow**: Send draft emails to approvers before final distribution
- **Batch Processing**: Send emails in batches of 500 to avoid server overload
- **Deduplication**: Automatically remove duplicate email addresses
- **Comprehensive Logging**: Track all operations with detailed logs
- **Multiple Recipient Types**: Support for TO, CC, and BCC recipients

## Prerequisites
- Python 3.6 or higher
- Access to an SMTP server (configured for localhost)
- Required Python modules: `os`, `csv`, `re`, `time`, `logging`, `smtplib`, `sys`, `email`, `pathlib`, `typing`

## Project Structure

### Required Files
Each email campaign requires a dedicated folder containing these mandatory files:

```
campaign_folder/
├── from.txt          # Sender's email address
├── subject.txt       # Email subject line
├── body.html         # HTML email body content
├── approver.txt      # List of approver email addresses
├── inventory.csv     # Database of all potential recipients
└── filter.txt        # Filter conditions (CSV format)
```

### Optional Files
```
campaign_folder/
├── to.txt            # Primary recipients (auto-generated/manual)
├── cc.txt            # CC recipients
├── bcc.txt           # BCC recipients
└── additional_to.txt # Additional recipients to append
```

## Step-by-Step Setup Guide

### Step 1: Create Campaign Folder
```bash
mkdir my_campaign
cd my_campaign
```

### Step 2: Create Required Files

#### 2.1 Create `from.txt`
```
sender@company.com
```

#### 2.2 Create `subject.txt`
```
Important Company Update - Q4 2024
```

#### 2.3 Create `body.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>Email Content</title>
</head>
<body>
    <h1>Hello!</h1>
    <p>This is your email content in HTML format.</p>
    <p>Best regards,<br>Your Team</p>
</body>
</html>
```

#### 2.4 Create `approver.txt`
```
manager@company.com
supervisor@company.com
```

#### 2.5 Create `inventory.csv`
This file contains all potential recipients with their attributes:
```csv
name,department,role,emailids,location
John Doe,Engineering,Developer,john@company.com,New York
Jane Smith,Marketing,Manager,jane@company.com;jane.smith@company.com,California
Bob Johnson,Sales,Representative,bob@company.com,Texas
```

#### 2.6 Create `filter.txt`
Define filtering conditions in CSV format:
```csv
department,role
Engineering,Developer
Marketing,Manager
```

### Step 3: Create Optional Files (if needed)

#### 3.1 Create `cc.txt` (optional)
```
cc_recipient@company.com
```

#### 3.2 Create `bcc.txt` (optional)
```
bcc_recipient@company.com
```

#### 3.3 Create `additional_to.txt` (optional)
```
extra_recipient@company.com
special_recipient@company.com
```

## Usage Instructions

### Running NotifyBot
```bash
python notifybot.py /path/to/campaign_folder
```

### Workflow Process

#### Phase 1: Draft Approval
1. **Draft Email Generation**: NotifyBot reads your content and creates a draft email
2. **Send to Approvers**: Draft email (with "[DRAFT]" prefix) is sent to all addresses in `approver.txt`
3. **Approval Loop**: 
   - System prompts: "Has approval been received? (yes/no)"
   - If "no": You can edit `subject.txt` or `body.html`, then system resends draft
   - If "yes": Process continues to final sending
   - Invalid input: System prompts again

#### Phase 2: Recipient Processing
1. **Filter Application**: System applies conditions from `filter.txt` to `inventory.csv`
2. **Email Extraction**: Extracts matching email addresses (supports semicolon/comma separation)
3. **Deduplication**: Removes duplicates and emails already in `to.txt`
4. **File Updates**: Appends new emails to `to.txt` and processes `additional_to.txt`

#### Phase 3: Email Sending
1. **Batch Processing**: Sends emails in batches of 500 recipients
2. **Delay Management**: 5-second delay between batches
3. **Final Summary**: Reports total emails sent

## Configuration Details

### Filter File Format
The `filter.txt` file uses CSV format where:
- **First row**: Column headers (must match `inventory.csv` headers)
- **Subsequent rows**: Filter conditions (AND logic within each row)
- **Multiple rows**: OR logic between rows

Example:
```csv
department,location
Engineering,New York
Marketing,California
Sales,Texas
```
This filters for: (Engineering AND New York) OR (Marketing AND California) OR (Sales AND Texas)

### Email Address Handling
- Multiple emails per person: Use semicolon (`;`) or comma (`,`) separation
- Automatic deduplication prevents duplicate sends
- Case-sensitive email matching

### Logging
- **Log file**: `notifybot.log` (created in script directory)
- **Log level**: INFO
- **Format**: Timestamp, level, function name, line number, message
- **Tracked events**: File operations, email sends, errors, warnings

## Error Handling

### Common Errors and Solutions

#### Missing Required Files
**Error**: `MissingRequiredFilesError`  
**Solution**: Ensure all required files exist in the campaign folder

#### Empty Subject/Body
**Error**: System exits with error message  
**Solution**: Verify `subject.txt` and `body.html` contain content

#### SMTP Connection Issues
**Error**: Email sending fails  
**Solution**: Verify SMTP server is running on localhost

#### File Read Errors
**Error**: Logged as warnings/errors  
**Solution**: Check file permissions and encoding (UTF-8)

## Best Practices

### 1. File Management
- Use descriptive folder names for campaigns
- Keep backup copies of working configurations
- Test with small recipient lists first

### 2. Content Preparation
- Validate HTML in `body.html` before sending
- Keep subject lines concise and clear
- Include unsubscribe information in email body

### 3. Recipient Management
- Regularly update `inventory.csv` with current data
- Use specific filters to target appropriate audiences
- Monitor `notifybot.log` for delivery issues

### 4. Testing Workflow
- Start with approver-only testing
- Use a test folder with minimal recipients
- Verify email formatting across different clients

## Troubleshooting

### Logs Analysis
Check `notifybot.log` for:
- File reading errors
- Email sending failures
- Filter processing issues
- Recipient list problems

### Common Issues
1. **No emails sent**: Check if `to.txt` is populated after filtering
2. **Duplicate emails**: Verify deduplication is working
3. **SMTP errors**: Confirm local SMTP server configuration
4. **Filter not working**: Verify column names match between files

## Security Considerations
- Store sensitive email credentials securely
- Use appropriate file permissions for campaign folders
- Regularly review and clean up log files
- Consider encryption for sensitive recipient data

## Performance Notes
- Batch size: 500 emails per batch (adjustable in code)
- Delay: 5 seconds between batches
- Memory usage: Depends on recipient list size
- Processing time: Varies with inventory size and filter complexity
