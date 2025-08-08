# 🚀 NotifyBot User Runbook

**NotifyBot**, our smart, scalable solution for email automation. Whether you're sending a handful of emails or thousands, NotifyBot makes it effortless, safe, and efficient. It supports both single and multi modes, with dry-run and signature capabilities.

- 📧 **Batch Email Sending**: Deliver emails in customizable batches with controlled delays
- 🖋️ **HTML Email Support**: Craft rich, styled messages (with attachments!)
- 🎯 **Recipient Filtering**: Easily target the right audience with CSV filters
- 🧪 **Dry Run Mode**: Test configurations safely without sending actual emails
- ✅ **Email Validation**: Automatically validate addresses to reduce bounces
- 📎 **Attachment Support**: Attach files up to 15MB each
- 🔁 **Deduplication**: Automatically remove duplicate recipients
- 📊 **Logging & Transparency**: Detailed logs with automatic log rotation
- ✍️ **Global Signature Support**: Automatically append signature to all emails
- 🖼️ **Image Embedding**: Embed images directly in emails to avoid blocking

*Stay in control. Stay efficient. That's the NotifyBot way.*

## ⚠️ Critical Disclaimer

📧 Always run NotifyBot in `--dry-run` mode first to verify recipients and content.  
❌ Do **not** use `--force` unless running in a fully automated script with prior approval.  
⚠️ Running live without a dry-run review may result in unintended mass emails.  
📂 The `<user-basefolder>` is the directory where you must maintain all required input files (e.g. `subject.txt`, `body.html`, `to.txt`).

## 💡 Tip

Always replace `<user-basefolder>` in the examples below with the name of your campaign folder inside `/notifybot/basefolder/`. Example: If your folder is `newsletter_august`, use:  
`/notifybot/venv/bin/python notifybot.py --base-folder newsletter_august --dry-run`

# NotifyBot Complete Runbook

## 📋 Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Prerequisites & Setup](#prerequisites--setup)
4. [File Structure & Organization](#file-structure--organization)
5. [Single Mode Operations](#single-mode-operations)
6. [Multi Mode Operations](#multi-mode-operations)
7. [Field Validation & Inventory System](#field-validation--inventory-system)
8. [Filter Syntax Guide](#filter-syntax-guide)
9. [Template Substitution](#template-substitution)
10. [Dry-Run vs Live Mode](#dry-run-vs-live-mode)
11. [Troubleshooting](#troubleshooting)
12. [Examples](#examples)

---

## 🎯 Overview

NotifyBot is a powerful email automation system that supports two distinct modes:

- **Single Mode**: Send one email to multiple recipients (broadcast style)
- **Multi Mode**: Send personalized emails based on filter conditions (targeted campaigns)

### Key Features
- ✅ Batch processing with configurable delays
- ✅ HTML email support with embedded images
- ✅ Template substitution with CSV data
- ✅ Attachment support (15MB limit)
- ✅ Dry-run mode for testing
- ✅ Priority-based field validation
- ✅ Email signature support
- ✅ CC/BCC support
- ✅ Comprehensive logging

---

## 🏗️ System Architecture

### Directory Structure
```
/notifybot/
├── basefolder/                    # Base folder for all email projects
│   └── <your-project>/            # Your email project folder
├── inventory/
│   └── inventory.csv              # Global inventory file
├── logs/
│   └── notifybot.log              # System logs
└── signature.html                 # Global email signature (optional)
```

### Project Folder Structure
```
/notifybot/basefolder/<your-project>/
├── subject.txt                    # Email subject [REQUIRED]
├── body.html                      # Email body HTML [REQUIRED]
├── from.txt                       # Sender email address [REQUIRED]
├── approver.txt                   # Approver emails for dry-run [REQUIRED]
├── to.txt                         # Direct recipients (single mode)
├── cc.txt                         # CC recipients (optional)
├── bcc.txt                        # BCC recipients (optional)
├── filter.txt                     # Filter conditions (multi mode / single mode filtering)
├── field.txt                      # Fields for template substitution (multi mode)
├── table-columns.txt              # Table column specification (optional)
├── additional_to.txt              # Additional recipients to merge
├── mode.txt                       # Force mode selection (single/multi)
├── field-inventory.csv            # Local field inventory (optional)
├── attachment/                    # Attachment folder (15MB limit)
│   └── *.pdf, *.docx, etc.
├── images/                        # Images for embedding in emails
│   └── *.png, *.jpg, etc.
└── recipients/                    # Generated recipient lists (auto-created)
```

---

## 🛠️ Prerequisites & Setup

### System Requirements
- Python 3.6+
- Sendmail installed and configured
- Required Python packages:
  - `email_validator`
  - Standard library packages (csv, logging, pathlib, etc.)

### Initial Setup
1. Create your project folder:
   ```bash
   mkdir -p /notifybot/basefolder/my-project
   cd /notifybot/basefolder/my-project
   ```

2. Set up global inventory (if using filters):
   ```bash
   # Create inventory directory
   mkdir -p /notifybot/inventory
   
   # Upload your inventory.csv to /notifybot/inventory/inventory.csv
   ```

3. (Optional) Set up global signature:
   ```bash
   # Create signature file
   echo '<p>Best regards,<br>Your Team</p>' > /notifybot/signature.html
   ```

---

## 📁 File Structure & Organization

### Required Files (All Modes)
| File | Description | Format | Example |
|------|-------------|---------|---------|
| `subject.txt` | Email subject line | Plain text | `Weekly Newsletter - January 2025` |
| `body.html` | Email body content | HTML | `<h1>Welcome!</h1><p>This is our newsletter...</p>` |
| `from.txt` | Sender email address | Email | `newsletter@company.com` |
| `approver.txt` | Approver emails for dry-run | Emails (semicolon-separated) | `manager@company.com;admin@company.com` |

### Mode-Specific Files

#### Single Mode
At least ONE of these recipient sources is required:
- `to.txt` - Direct recipient list
- `filter.txt` + inventory.csv - Filtered recipients
- `additional_to.txt` - Additional recipients
- `cc.txt` - CC recipients
- `bcc.txt` - BCC recipients

#### Multi Mode
Required additional files:
- `filter.txt` - Filter conditions (one per line)

### Optional Files
| File | Purpose | Format | Example |
|------|---------|---------|---------|
| `cc.txt` | CC recipients | Emails (semicolon-separated) | `manager@company.com;admin@company.com` |
| `bcc.txt` | BCC recipients | Emails (semicolon-separated) | `audit@company.com` |
| `field.txt` | Template substitution fields | Field names (one per line) | `name`<br>`department`<br>`location` |
| `table-columns.txt` | Table column specification | Field names (one per line) | `name`<br>`email`<br>`department` |
| `additional_to.txt` | Additional recipients to merge | Emails (semicolon-separated) | `extra@company.com` |
| `mode.txt` | Force mode selection | `single` or `multi` | `multi` |
| `field-inventory.csv` | Local field inventory | CSV format | Same as global inventory.csv |

### Optional Folders
| Folder | Purpose | Limits | Supported Formats |
|--------|---------|---------|-------------------|
| `attachment/` | Email attachments | 15MB total | PDF, DOCX, XLSX, TXT, images |
| `images/` | Embedded images | N/A | PNG, JPG, GIF, etc. |

---

## 📧 Single Mode Operations

### Purpose
Send one email to multiple recipients (broadcast style).

### Prechecks
```bash
# 1. Check required files
ls -la subject.txt body.html from.txt approver.txt

# 2. Check at least one recipient source exists
ls -la to.txt filter.txt additional_to.txt cc.txt bcc.txt

# 3. Validate email format
cat from.txt  # Should contain valid email
cat approver.txt  # Should contain valid emails
```

### Recipient Priority (Single Mode)
1. **Primary**: `to.txt` (if exists)
   - If `additional_to.txt` exists → merge with `to.txt`
2. **Fallback**: `filter.txt` + inventory.csv (if `to.txt` doesn't exist)
   - If `additional_to.txt` exists → merge with filtered results
   - Creates `to.txt` with merged results
3. **Last Resort**: `additional_to.txt` only
   - Creates `to.txt` from `additional_to.txt`

### Usage Examples
```bash
# Basic single mode (dry-run)
python notifybot.py --base-folder my-project --dry-run

# Live single mode with custom batch size
python notifybot.py --base-folder my-project --batch-size 200 --delay 10

# Force single mode (override mode.txt)
python notifybot.py --base-folder my-project --mode single --force
```

### Single Mode Workflow
1. **Validation**: Check required files and recipient sources
2. **Recipients**: Determine recipients using priority system
3. **Processing**: Send email in batches
4. **Logging**: Track success/failure rates

---

## 🎯 Multi Mode Operations

### Purpose
Send personalized emails based on filter conditions with template substitution.

### Prechecks
```bash
# 1. Check required files
ls -la subject.txt body.html from.txt approver.txt filter.txt

# 2. Check inventory file
ls -la /notifybot/inventory/inventory.csv

# 3. Validate filter syntax
cat filter.txt  # Should contain valid filter conditions

# 4. Check field substitution setup (optional)
ls -la field.txt  # If using template substitution
```

### Required Files (Multi Mode)
- All standard required files
- `filter.txt` - Filter conditions (one condition per line)
- `/notifybot/inventory/inventory.csv` - Global inventory

### Usage Examples
```bash
# Basic multi mode (dry-run)
python notifybot.py --base-folder my-campaign --dry-run --mode multi

# Live multi mode with template substitution
python notifybot.py --base-folder my-campaign --mode multi --delay 5

# Multi mode with custom batching
python notifybot.py --base-folder my-campaign --mode multi --batch-size 100
```

### Multi Mode Workflow
1. **Validation**: Check required files and inventory
2. **Filter Processing**: Process each filter condition separately
3. **Template Substitution**: Replace placeholders with CSV data
4. **Email Generation**: Create personalized emails
5. **Batch Sending**: Send each email with batching support
6. **Logging**: Track per-filter success rates

---

## 📊 Field Validation & Inventory System

### Priority-Based Validation Rules

#### Global Inventory
- **Location**: `/notifybot/inventory/inventory.csv`
- **Purpose**: Master data source for all field validation
- **Usage**: Always used for `filter.txt` validation

#### Local Field Inventory (Optional)
- **Location**: `/notifybot/basefolder/<project>/field-inventory.csv`
- **Purpose**: Project-specific field definitions
- **Priority**: Higher priority than global inventory for `field.txt`

### Validation Priority Matrix
| Field Source | Global Inventory | Local Field Inventory | Validation Rule |
|--------------|------------------|----------------------|-----------------|
| `filter.txt` | ✅ Always | ✅ If exists | Both must pass |
| `field.txt` | ✅ Fallback | ✅ Primary | Local takes priority |
| `table-columns.txt` | ✅ Fallback | ✅ Primary | Local takes priority |

### Dynamic Fields
These fields are generated at runtime and don't need CSV headers:
- `dynamic_table` - Backward compatibility table
- `table_rows` - Standard HTML table rows
- `csv_table_rows` - Pipe-separated table rows
- `simple_table_rows` - Simple HTML table (no styling)
- `styled_table_rows` - Table with alternating row colors
- `table_headers` - Table headers from CSV fields

### Field Validation Examples
```bash
# Check available fields in global inventory
head -1 /notifybot/inventory/inventory.csv

# Check local field inventory
head -1 field-inventory.csv  # if exists

# Test field validation
cat field.txt  # Ensure all fields exist in inventory
cat filter.txt  # Ensure all filter fields exist in inventory
```

---

## 🔍 Filter Syntax Guide

### Supported Operators
| Operator | Description | Example | Notes |
|----------|-------------|---------|-------|
| `=` | Exact match | `department="sales"` | Case-insensitive |
| `!=` | Not equal | `status!="inactive"` | Case-insensitive |
| `=~` | Regex match | `name=~".*Manager.*"` | Case-insensitive regex |
| `!~` | Regex not match | `email!~".*(test\|demo).*"` | Case-insensitive regex |
| `*` | Wildcard match | `location=north*` | Supports *, ?, [] |

### Logic Operators
- **AND**: Use comma separation within a line
- **OR**: Use separate lines

### Filter Examples
```bash
# Single condition
department="sales"

# AND condition (both must match)
department="sales",region="north"

# OR conditions (separate lines)
department="sales"
department="marketing"
region="europe"

# Regex examples
name=~".*Manager.*"
email=~".*@company\.com$"
phone!~"^555-"

# Wildcard examples
city=New*
country=U*A
status=active*

# Complex combinations
department="sales",region!="test"
status="active",email=~".*@company\.com$"
```

### Comments and Empty Lines
```bash
# This is a comment - ignored
department="sales"

# Empty lines are ignored

region="north"  # This sends to north region
```

---

## 🔄 Template Substitution

### How It Works
1. Define fields in `field.txt` (one per line)
2. Use `{fieldname}` placeholders in subject.txt and body.html
3. System extracts values from CSV rows matching filters
4. Replaces placeholders with actual values

### Field Definition
```bash
# field.txt example
name
department
location
email
phone
table_rows
```

### Template Examples

#### Subject Template
```
Welcome to {department} - {location} Office Update
```

#### Body Template
```html
<h1>Hello {name}!</h1>
<p>This update is specifically for the {department} team in {location}.</p>

<h2>Team Directory</h2>
<table border="1">
    <tr>
        {table_headers}
    </tr>
    {table_rows}
</table>

<p>Questions? Contact us at {email}</p>
```

### Value Processing
- **Single values**: `John Smith`
- **Comma-separated values**: Formatted as `Value1, Value2, and Value3`
- **Large lists**: `Value1, Value2, Value3, and 5 more`

### Dynamic Table Generation

#### Using table-columns.txt
```bash
# table-columns.txt
name
email
department
location
```

#### Available Table Fields
- `table_headers` - HTML table headers
- `table_rows` - Standard styled table rows
- `styled_table_rows` - Alternating row colors
- `simple_table_rows` - No styling
- `csv_table_rows` - Pipe-separated format

---

## 🧪 Dry-Run vs Live Mode

### Dry-Run Mode (`--dry-run`)
**Purpose**: Test emails safely before live deployment

**Behavior**:
- Sends emails ONLY to approvers listed in `approver.txt`
- Adds "DRAFT - " prefix to subject
- Includes draft information box in email body
- Shows original recipient counts in draft info
- Preserves original recipient data for reference
- No actual recipients receive emails

**Draft Info Box Includes**:
- Original recipient count
- Filter condition (multi mode)
- CC/BCC recipient counts
- Clear "DRAFT" labeling

### Live Mode (default)
**Purpose**: Send emails to actual recipients

**Behavior**:
- Sends to all specified recipients
- No subject prefix modification
- Normal email delivery
- Full batch processing with delays
- Complete logging and tracking

### Mode Selection Priority
1. CLI argument: `--dry-run` or `--mode`
2. `mode.txt` file content
3. Default: live mode

---

## 🔧 Command Line Interface

### Basic Syntax
```bash
python notifybot.py --base-folder <folder> [options]
```

### Required Arguments
- `--base-folder`: Project folder name (inside `/notifybot/basefolder/`)

### Optional Arguments
| Argument | Description | Default | Examples |
|----------|-------------|---------|----------|
| `--mode` | Force mode selection | Auto-detect | `--mode single`, `--mode multi` |
| `--dry-run` | Enable dry-run mode | Live mode | `--dry-run` |
| `--force` | Skip confirmation prompt | Interactive | `--force` |
| `--batch-size` | Emails per batch | 500 | `--batch-size 200` |
| `--delay` | Seconds between batches | 5.0 | `--delay 10` |

### Usage Examples
```bash
# Basic dry-run test
python notifybot.py --base-folder newsletter --dry-run

# Live single mode with custom settings
python notifybot.py --base-folder announcement --mode single --batch-size 300 --delay 8

# Force multi mode without confirmation
python notifybot.py --base-folder campaign --mode multi --force

# Large batch processing
python notifybot.py --base-folder bulk-email --batch-size 1000 --delay 2
```

---

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. Missing Required Files
**Error**: `Missing required files: subject.txt, body.html`
**Solution**: 
```bash
# Check required files exist
ls -la subject.txt body.html from.txt approver.txt
# Create missing files
touch subject.txt body.html from.txt approver.txt
```

#### 2. No Recipients Found
**Error**: `Single mode requires at least one recipient source`
**Solution**:
```bash
# Create at least one recipient source
echo "user@example.com" > to.txt
# OR create filter.txt and ensure inventory.csv exists
```

#### 3. Field Validation Errors
**Error**: `Field 'department' not found in inventory.csv`
**Solution**:
```bash
# Check available fields
head -1 /notifybot/inventory/inventory.csv
# Update field.txt or filter.txt with correct field names
```

#### 4. Invalid Email Formats
**Error**: `Invalid email format: user@invalid`
**Solution**:
```bash
# Validate email formats
grep -E '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$' to.txt
```

#### 5. Attachment Size Limit
**Error**: `Attachment size limit exceeded: 20MB > 15MB limit`
**Solution**:
```bash
# Check attachment sizes
du -sh attachment/*
# Remove or compress large files
```

#### 6. Sendmail Not Found
**Error**: `Sendmail not found at /usr/sbin/sendmail`
**Solution**:
```bash
# Install sendmail
sudo apt-get install sendmail
# OR check sendmail location
which sendmail
```

### Debug Steps
1. **Check Logs**: `tail -f /notifybot/logs/notifybot.log`
2. **Validate Files**: Ensure all required files exist and have content
3. **Test Dry-Run**: Always test with `--dry-run` first
4. **Check Permissions**: Ensure script has read access to all files
5. **Verify Inventory**: Check CSV headers and data format

---

## 📝 Examples

### Example 1: Simple Newsletter (Single Mode)

#### Setup
```bash
mkdir -p /notifybot/basefolder/newsletter
cd /notifybot/basefolder/newsletter
```

#### Files
```bash
# subject.txt
echo "Monthly Company Newsletter - January 2025" > subject.txt

# from.txt
echo "newsletter@company.com" > from.txt

# approver.txt
echo "manager@company.com;editor@company.com" > approver.txt

# to.txt
echo "all-staff@company.com;contractors@company.com" > to.txt

# body.html
cat << 'EOF' > body.html
<!DOCTYPE html>
<html>
<head>
    <title>Newsletter</title>
</head>
<body>
    <h1>Monthly Newsletter</h1>
    <p>Welcome to our monthly company update!</p>
    <h2>This Month's Highlights</h2>
    <ul>
        <li>New product launch</li>
        <li>Team achievements</li>
        <li>Upcoming events</li>
    </ul>
</body>
</html>
EOF
```

#### Execution
```bash
# Test first
python notifybot.py --base-folder newsletter --dry-run

# Send live
python notifybot.py --base-folder newsletter
```

### Example 2: Personalized Department Updates (Multi Mode)

#### Setup
```bash
mkdir -p /notifybot/basefolder/dept-updates
cd /notifybot/basefolder/dept-updates
```

#### Files
```bash
# subject.txt (template)
echo "Department Update for {department} - {location}" > subject.txt

# filter.txt (one email per department)
cat << 'EOF' > filter.txt
department="sales"
department="marketing" 
department="engineering"
department="hr"
EOF

# field.txt (for substitution)
cat << 'EOF' > field.txt
department
location
manager_name
team_size
table_rows
EOF

# body.html (template)
cat << 'EOF' > body.html
<!DOCTYPE html>
<html>
<body>
    <h1>Update for {department} Department</h1>
    <p>Hello {department} team in {location}!</p>
    
    <p><strong>Department Manager:</strong> {manager_name}</p>
    <p><strong>Team Size:</strong> {team_size} members</p>
    
    <h2>Team Directory</h2>
    <table border="1" cellpadding="5">
        {table_headers}
        {table_rows}
    </table>
    
    <p>Thank you for your continued dedication!</p>
</body>
</html>
EOF

# table-columns.txt (for table generation)
cat << 'EOF' > table-columns.txt
name
email
role
phone
EOF
```

#### Inventory Setup
```bash
# Create sample inventory at /notifybot/inventory/inventory.csv
cat << 'EOF' > /notifybot/inventory/inventory.csv
name,email,department,location,manager_name,team_size,role,phone
John Smith,john@company.com,sales,New York,Jane Doe,12,Manager,555-0101
Mary Johnson,mary@company.com,sales,New York,Jane Doe,12,Rep,555-0102
Bob Wilson,bob@company.com,marketing,Chicago,Tom Brown,8,Director,555-0201
Alice Davis,alice@company.com,marketing,Chicago,Tom Brown,8,Specialist,555-0202
EOF
```

#### Execution
```bash
# Test with dry-run
python notifybot.py --base-folder dept-updates --mode multi --dry-run

# Send live
python notifybot.py --base-folder dept-updates --mode multi --delay 10
```

### Example 3: Event Invitation with Attachments

#### Setup
```bash
mkdir -p /notifybot/basefolder/event-invite
cd /notifybot/basefolder/event-invite

# Create attachment folder
mkdir attachment
echo "Event agenda content..." > attachment/agenda.pdf
echo "Map and directions..." > attachment/directions.pdf
```

#### Files
```bash
# subject.txt
echo "You're Invited: Annual Company Retreat" > subject.txt

# body.html with embedded image
cat << 'EOF' > body.html
<!DOCTYPE html>
<html>
<body>
    <h1>Annual Company Retreat</h1>
    <img src="retreat-banner.jpg" alt="Retreat Banner" style="max-width: 100%;">
    
    <h2>Event Details</h2>
    <ul>
        <li><strong>Date:</strong> March 15-17, 2025</li>
        <li><strong>Location:</strong> Mountain Resort</li>
        <li><strong>Theme:</strong> Innovation & Team Building</li>
    </ul>
    
    <p>Please see attached documents for agenda and directions.</p>
    
    <h3>RSVP Required</h3>
    <p>Please confirm your attendance by March 1st.</p>
</body>
</html>
EOF

# Add image for embedding
mkdir images
echo "Create retreat-banner.jpg in images folder"

# filter.txt for targeted invitations
cat << 'EOF' > filter.txt
status="active"
department!="contractor"
location=~"(New York|Chicago|Boston)"
EOF
```

#### Execution
```bash
# Test invitation
python notifybot.py --base-folder event-invite --dry-run

# Send invitations
python notifybot.py --base-folder event-invite --batch-size 100
```

---

## 📊 Enhanced Logging

**UPDATED:** Logs are written to `/notifybot/logs/notifybot.log` in CSV format with expanded emoji categories for quick scanning.

```
ℹ️ Info, ⚠️ Warning, ❌ Error, ✅ Success, 📝 Draft, 🔧 Mode,
⏳ Processing, 💾 Backup, 📂 File, ✋ Confirmation, ✍️ Signature
```

📡 All logs are also forwarded in real-time to **Splunk** for auditing and long-term reference.

[📊 Open Splunk Dashboard](https://tinyurl/notifybot)

### Log Location
- **File**: `/notifybot/logs/notifybot.log`
- **Format**: CSV with timestamp, username, message
- **Level**: INFO and above

### Log Analysis
```bash
# View recent logs
tail -100 /notifybot/logs/notifybot.log

# Search for errors
grep "❌" /notifybot/logs/notifybot.log

# Count successful emails
grep "✅.*sent successfully" /notifybot/logs/notifybot.log | wc -l

# View specific project logs
grep "base-folder.*my-project" /notifybot/logs/notifybot.log
```

### Monitoring Success Rates
```bash
# Extract batch statistics
grep "batch processing complete" /notifybot/logs/notifybot.log

# Find failed operations
grep "failed" /notifybot/logs/notifybot.log | tail -20

# Monitor attachment issues
grep "attachment" /notifybot/logs/notifybot.log
```

---

## 🔒 Security & Best Practices

### Email Security
- Always validate email addresses
- Use BCC for large recipient lists to protect privacy
- Test with dry-run before live deployment
- Monitor sendmail logs for delivery issues

### File Security
- Keep sensitive data in inventory files secure
- Use proper file permissions (readable by notifybot only)
- Regular backup of project folders
- Clean up old recipient files periodically

### Performance Optimization
- Use appropriate batch sizes (default: 500)
- Add delays between batches to avoid overwhelming mail servers
- Monitor system resources during large campaigns
- Use local field-inventory.csv for better performance

### Best Practices Checklist
- ✅ Always run dry-run tests first
- ✅ Validate all email addresses before sending
- ✅ Keep attachment sizes under 15MB
- ✅ Use meaningful project folder names
- ✅ Document filter conditions clearly
- ✅ Regular log monitoring and cleanup
- ✅ Backup important project configurations
- ✅ Test template substitution thoroughly

---

This runbook provides comprehensive guidance for using NotifyBot effectively in both single and multi modes. Always start with dry-run testing and gradually scale up to full deployment.
