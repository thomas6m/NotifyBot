# NotifyBot Analysis: Requirements and Logic

## File Structure Overview

```
/notifybot/
├── basefolder/
│   └── <your-folder>/          # Base folder specified by --base-folder
│       ├── subject.txt         # Email subject
│       ├── body.html          # Email body (HTML)
│       ├── from.txt           # Sender email
│       ├── approver.txt       # Approver emails (for dry-run)
│       ├── mode.txt           # Optional: "single" or "multi"
│       ├── to.txt             # Direct recipients (single mode)
│       ├── filter.txt         # Filter conditions
│       ├── field.txt          # Field names for substitution
│       ├── additional_to.txt  # Additional recipients
│       ├── cc.txt             # CC recipients
│       ├── bcc.txt            # BCC recipients
│       ├── field-inventory.csv # Local field inventory (optional)
│       ├── attachment/        # Folder with attachments
│       ├── images/            # Folder with images to embed
│   └── recipients/            # Auto-generated folder for recipient lists
├── inventory/
│   └── inventory.csv          # Global inventory database
├── signature.html             # Global email signature
└── logs/
    └── notifybot.log          # Application logs
```

## Single Mode Requirements

### Required Files
- `subject.txt` - Email subject line
- `body.html` - Email body content (HTML format)
- `from.txt` - Sender email address
- `approver.txt` - List of approver emails (for dry-run mode)

### Recipient Sources (At Least ONE Required)
- `to.txt` - Direct list of recipients
- `filter.txt` + global `inventory.csv` - Filtered recipients from database
- `additional_to.txt` - Additional recipients to merge
- `cc.txt` - CC recipients
- `bcc.txt` - BCC recipients

### Optional Files
- `mode.txt` - Force mode selection ("single" or "multi")
- `field.txt` - NOT used in single mode (ignored)
- `field-inventory.csv` - Local field inventory

### Optional Folders
- `attachment/` - Files to attach to emails
- `images/` - Images to embed in HTML body

## Multi Mode Requirements

### Required Files
- `subject.txt` - Email subject template
- `body.html` - Email body template (HTML format)
- `from.txt` - Sender email address
- `approver.txt` - List of approver emails (for dry-run mode)
- `filter.txt` - Filter conditions (each line creates separate email)
- Global `inventory.csv` - Database for filtering and field extraction

### Optional Files
- `field.txt` - Field names for template placeholder substitution
- `cc.txt` - CC recipients (added to each email)
- `bcc.txt` - BCC recipients (added to each email)
- `additional_to.txt` - Additional recipients (merged with each filter result)
- `mode.txt` - Force mode selection
- `field-inventory.csv` - Local field inventory (higher priority than global)

### Optional Folders
- `attachment/` - Files to attach to each email
- `images/` - Images to embed in HTML body

## Filter.txt Logic

### Single Mode Filter Behavior
- **Purpose**: Generate recipients for ONE email
- **Logic**: All filter lines are combined with OR logic
- **Result**: Single consolidated recipient list
- **File Creation**: Creates `to.txt` with merged results

### Multi Mode Filter Behavior
- **Purpose**: Generate MULTIPLE personalized emails
- **Logic**: Each filter line creates a separate email
- **Result**: Multiple email configurations, one per filter line
- **File Creation**: Creates individual recipient files in `recipients/` folder

### Filter Syntax
```
# Supported operators
department="sales"                    # Exact match
region!="europe"                      # Not equal
name=~".*Manager.*"                   # Regex match
email!~".*(test|demo).*"              # Regex not match
status=active*                        # Wildcard match

# Logic operators
department="sales",region="north"     # AND condition (comma-separated)
department="sales"                    # OR condition
department="marketing"                # (separate lines)

# Comments
# This is a comment line (ignored)
```

### Filter Examples
```
# Single Mode - All conditions create ONE recipient list
department="sales"
department="marketing"
region="north",status="active"

# Multi Mode - Each line creates SEPARATE email
department="sales"           # Email 1: All sales people
department="marketing"       # Email 2: All marketing people  
region="north",status="active"  # Email 3: Active north region people
```

## Field.txt Logic

### Single Mode Field Behavior
- **Status**: IGNORED (field.txt is not processed in single mode)
- **Reason**: Single mode sends identical content to all recipients
- **Template Substitution**: Not supported

### Multi Mode Field Behavior
- **Purpose**: Define which fields to extract for template substitution
- **Source Priority**:
  1. Local `field-inventory.csv` (if exists)
  2. Global `inventory.csv` (fallback)
- **Extraction**: Extracts unique values from ALL rows matching each filter
- **Usage**: Replaces `{fieldname}` placeholders in subject and body templates

### Field.txt Example
```
department
region
country
status
```

### Template Substitution Example
**Subject Template**: `Monthly Report for {department} in {region}`
**Body Template**: `Dear {department} team in {region}...`

**Filter**: `department="sales",region="north"`
**Extracted Values**: `department="sales"`, `region="north,northeast"`
**Result**: 
- Subject: `Monthly Report for sales in north, northeast`
- Body: `Dear sales team in north, northeast...`

## Field Validation Priority System

### Priority Rules
1. **Global Inventory**: All `filter.txt` fields must exist in `/notifybot/inventory/inventory.csv`
2. **Local Override**: If `<base-folder>/field-inventory.csv` exists:
   - `filter.txt` fields must exist in BOTH global AND local inventories
   - `field.txt` fields must exist in local inventory (higher priority)
3. **Fallback**: If no local inventory, `field.txt` fields must exist in global inventory

### Validation Examples
```
# Global inventory has: name, email, department, region
# Local field-inventory has: department, region, country, status

filter.txt: department="sales"     # ✅ Valid (exists in both)
filter.txt: name=~"John.*"         # ❌ Invalid (missing from local)
field.txt: country                 # ✅ Valid (exists in local)
field.txt: email                   # ❌ Invalid (missing from local)
```

## Operational Modes

### Single Mode Operation
1. **Recipient Generation**: Consolidate all recipient sources
2. **Content**: Same subject/body for all recipients
3. **Delivery**: One email campaign with batching
4. **Result**: `to.txt` with merged recipients

### Multi Mode Operation
1. **Email Generation**: Create separate email config per filter line
2. **Content**: Personalized subject/body per filter using field substitution
3. **Delivery**: Multiple individual email campaigns
4. **Result**: Individual recipient files in `recipients/` folder

### Dry-Run Mode (Both Modes)
- **Recipients**: Only sends to approvers from `approver.txt`
- **Subject**: Adds "DRAFT - " prefix
- **Body**: Adds draft disclaimer with original recipient counts
- **Purpose**: Review and approval before live sending

## Key Differences Summary

| Aspect | Single Mode | Multi Mode |
|--------|-------------|------------|
| **Purpose** | One email to many | Many personalized emails |
| **filter.txt** | OR logic → single list | Each line → separate email |
| **field.txt** | Ignored | Used for template substitution |
| **Templates** | Static content | Dynamic with {field} placeholders |
| **Output** | One `to.txt` file | Multiple recipient files |
| **Validation** | Filter fields only | Both filter and field validation |
| **CC/BCC** | Added once | Added to each email |

## Best Practices

### Single Mode Best Practices
- Use when sending identical content to large groups
- Combine multiple recipient sources (to.txt, filter.txt, additional_to.txt)
- Leverage batching for large recipient lists
- Don't create field.txt (it's ignored)

### Multi Mode Best Practices
- Use when content needs personalization per group
- Keep filter conditions specific and non-overlapping
- Create field.txt with relevant fields for substitution
- Test with dry-run to verify personalization
- Consider local field-inventory.csv for custom field sets

### Common Patterns
- **Departmental Updates**: Multi mode with `department="X"` filters
- **Regional Campaigns**: Multi mode with `region="Y"` filters  
- **Mass Announcements**: Single mode with comprehensive recipient list
- **Personalized Reports**: Multi mode with field substitution for dynamic content
