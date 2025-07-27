# NotifyBot: Single vs Multi Mode Analysis

## Overview
NotifyBot is an automated email batch sender that supports two distinct modes: **Single Mode** and **Multi Mode**. It uses filtering, logging, and dry-run capabilities for safe email campaigns.

## Core Directory Structure
```
/notifybot/
├── basefolder/           # Contains all email campaigns
│   └── [campaign-name]/  # Your specific campaign folder
├── inventory/
│   └── inventory.csv     # Master data source for filtering
└── logs/
    └── notifybot.log     # All operations logged here
```

## Mode Determination
The script determines which mode to use in this priority order:
1. **CLI Override**: `--mode single` or `--mode multi`
2. **mode.txt file**: Contains either "single" or "multi"
3. **Default**: Falls back to "single" mode if nothing specified

## Single Mode Operation

### Purpose
Sends **one email** to **multiple recipients** (traditional bulk email approach).

### Required Files
```
campaign-folder/
├── subject.txt          # Email subject line
├── body.html           # Email body content
├── from.txt            # Sender email address
├── approver.txt        # Approver emails for dry-run mode
└── mode.txt            # Contains "single" (optional if using CLI)
```

### Recipient Source Files (At least one required for live mode)
```
├── to.txt              # Direct list of recipients
├── filter.txt          # Filter conditions + inventory.csv
├── additional_to.txt   # Additional emails (merged with others)
├── cc.txt              # CC recipients (optional)
└── bcc.txt             # BCC recipients (optional)
```

### Single Mode Logic Flow
1. **Recipient Resolution Priority**:
   - **Priority 1**: Use `to.txt` if exists
   - **Priority 2**: Apply `filter.txt` logic on `inventory.csv` if `to.txt` doesn't exist
   - **Priority 3**: Use only `additional_to.txt` if nothing else available

2. **Merging Logic**:
   - If `to.txt` exists AND `additional_to.txt` exists → merge both
   - If filter results exist AND `additional_to.txt` exists → merge both
   - Always deduplicate merged results

3. **File Generation**:
   - If using filter logic, creates `to.txt` with results for future reference
   - Maintains recipient lists for audit purposes

### Single Mode Example
```bash
# Dry run to test filters and see recipient count
python notifybot.py --base-folder my-campaign --dry-run

# Live send with batching
python notifybot.py --base-folder my-campaign --batch-size 500 --delay 5.0
```

## Multi Mode Operation

### Purpose
Sends **multiple individual emails** with **personalized content** based on filter conditions (mail merge approach).

### Required Files
```
campaign-folder/
├── subject.txt          # Subject template with placeholders
├── body.html           # Body template with placeholders  
├── from.txt            # Sender email address
├── approver.txt        # Approver emails for dry-run
├── mode.txt            # Contains "multi"
├── filter.txt          # One filter condition per line
└── field.txt           # Field names for placeholder substitution (optional)
```

### Multi Mode Logic Flow
1. **Individual Email Generation**:
   - Each line in `filter.txt` creates a **separate email**
   - Each email gets **personalized subject and body**
   - Each email has its own recipient list based on that filter

2. **Field Substitution**:
   - `field.txt` defines which fields to extract from filter conditions
   - Placeholders like `{name}`, `{department}` in templates get replaced
   - Values come from the filter condition parsing

3. **CC/BCC Handling**:
   - CC/BCC recipients are added to **every individual email**
   - If 5 filter lines exist, CC recipients get 5 separate emails

### Multi Mode Example
**filter.txt**:
```
department=sales,region=north
department=marketing,region=south  
role=manager,status=active
```

**field.txt**:
```
department
region
role
```

**subject.txt**:
```
Monthly Report for {department} - {region}
```

This creates **3 separate emails** with personalized subjects:
- "Monthly Report for sales - north"
- "Monthly Report for marketing - south"  
- "Monthly Report for manager - active"

## Filter Logic (Both Modes)

### Filter Syntax
The filter system supports advanced pattern matching with wildcards:

```
# Exact matching
department=sales,status=active

# Wildcard matching
department=sales*              # Starts with "sales"
email=*@company.com           # Ends with "@company.com"
role=*manager*                # Contains "manager"
name=john?                    # "john" + any single character

# Character sets
department=[sm]*              # Starts with 's' or 'm'
status=[!pending]*            # Doesn't start with "pending"
```

### Filter Logic Rules
1. **Each line = OR condition** (any line match includes the record)
2. **Within line = AND condition** (all conditions must match)
3. **Case-insensitive matching**
4. **Wildcard support**: `*` (any sequence), `?` (single char), `[seq]` (character sets)

### Filter Examples
```
# Example filter.txt
department=sales,status=active          # Sales AND Active
department=marketing,region=west*       # Marketing AND West*
role=*manager*                          # Contains "manager" anywhere
email=*@company.com                     # Email ends with @company.com

# Logic: (Sales AND Active) OR (Marketing AND West*) OR (*manager*) OR (*@company.com)
```

## Inventory.csv Structure
The master data file that filters are applied against:
```csv
email,department,region,status,role,name
john@company.com,sales,north,active,manager,John Doe
jane@company.com,marketing,south,pending,analyst,Jane Smith
```

## Dry-Run vs Live Mode

### Dry-Run Mode (`--dry-run`)
- **Single Mode**: Sends to approvers with recipient count info
- **Multi Mode**: Sends to approvers for each filter condition
- **Subject**: Prefixed with "DRAFT - "
- **Body**: Includes draft banner with original recipient counts
- **Purpose**: Review and approval before live sending

### Live Mode
- **Single Mode**: Sends to actual recipients in batches
- **Multi Mode**: Sends individual personalized emails
- **Batching**: Configurable batch size and delays
- **CC/BCC**: Included in every batch/email

## Key Differences Summary

| Aspect | Single Mode | Multi Mode |
|--------|-------------|------------|
| **Email Count** | 1 email to many recipients | Many emails (1 per filter line) |
| **Personalization** | Same content for all | Personalized per filter |
| **Recipients** | Bulk list (to.txt or filter results) | Individual filter-based lists |
| **CC/BCC Behavior** | Added to batches | Added to every individual email |
| **Use Case** | Newsletters, announcements | Reports, personalized campaigns |
| **Filter Usage** | All conditions → single recipient list | Each line → separate email |

## Best Practices

### Single Mode
- Use for bulk communications (newsletters, announcements)
- Test with `--dry-run` first to validate recipient lists
- Use appropriate batch sizes to avoid overwhelming mail servers
- Merge additional recipients using `additional_to.txt`

### Multi Mode  
- Use for personalized communications (reports, individual notifications)
- Define clear field names in `field.txt` for substitution
- Test filter conditions thoroughly with dry-run
- Be mindful that CC/BCC get multiple emails (one per filter line)

### General
- Always run dry-run first to validate configuration
- Monitor logs at `/notifybot/logs/notifybot.log`
- Use meaningful campaign folder names
- Keep inventory.csv updated and properly formatted

###############################################
