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

## 🏗️ File Structure & Locations

### Required Directory Structure:

```
/notifybot/
├── basefolder/                     # Your campaign folders go here
│   └── <user-basefolder>/         # Your specific campaign folder
│       ├── subject.txt             # Email subject (required)
│       ├── body.html               # Email body HTML (required)
│       ├── from.txt                # Sender email address (required)
│       ├── approver.txt            # Approvers for dry-run (required)
│       ├── mode.txt                # single or multi (optional)
│       ├── to.txt                  # Recipients for single mode (optional)
│       ├── cc.txt                  # CC recipients (optional)
│       ├── bcc.txt                 # BCC recipients (optional)
│       ├── filter.txt              # Filter conditions (for multi mode)
│       ├── field.txt               # Field names for substitution (multi mode)
│       ├── additional_to.txt       # Additional recipients to merge (optional)
│       ├── attachment/             # Folder for attachments (optional)
│       ├── images/                 # Folder for embedded images (optional)
│       └── recipients/             # Auto-generated recipient files
├── inventory/
│   └── inventory.csv               # Master recipient database
├── signature.html                  # Global signature file (optional)
└── logs/
    └── notifybot.log              # Application logs
```

## 🖼️ Image Embedding

**NEW:** Images are now automatically embedded in emails to prevent blocking by email clients.

- 📁 **Location:** Place images in `<user-basefolder>/images/`
- 🔗 **Usage:** Reference images in your HTML using relative paths: `<img src="logo.png">`
- ⚡ **Automatic:** Images are automatically converted to embedded attachments
- 🚫 **External URLs:** External image URLs are preserved but may be blocked by email clients
- 📏 **Supported formats:** All common image formats (PNG, JPG, GIF, etc.)

## 🔍 Enhanced Filter Logic

NotifyBot uses an enhanced PromQL-style filter engine with support for:

- `=` – Exact match (case-insensitive)
- `!=` – Not equal (case-insensitive)
- `=~` – Regex match (case-insensitive)
- `!~` – Regex not match (case-insensitive)
- `*`, `?`, `[seq]` – Wildcard (fnmatch-style)

Each line in `filter.txt` is treated as a separate **OR clause**.  
Within a line, comma-separated conditions are evaluated as **AND conditions**.

### 🧠 How the Matching Works

1. Each line from `filter.txt` is parsed into individual conditions.
2. Each row from `inventory.csv` is evaluated against these conditions.
3. If any line (OR block) passes (i.e., all conditions within it are true), the row is included.
4. Email addresses from the `email` field are split by semicolon and validated.
5. Duplicate and invalid addresses are filtered out automatically.

### 📌 Additional Notes

- If a condition omits the field name (e.g. `*@example.com`), it is matched against *all fields* in the row.
- Regex errors are logged and ignored gracefully.
- Missing keys in the row will be skipped with a warning.
- **NEW:** Enhanced syntax validation with detailed error messages
- **NEW:** Filter testing mode available for debugging

### ✅ Examples

```
# Match engineering employees in NA
department="engineering",region=~"USA|Canada"

# Exclude all interns and contractors
name!~".*(Intern|Contract).*"

# Wildcard fallback (any field containing the domain)
*@example.org

# Complex regex for multiple departments
department=~"(sales|marketing|support)"

# Exact match with wildcard value
status=active*
```

---

## 📤 Enhanced Recipient Priority

### 📧 Single Mode

**Sends one email to multiple recipients.** Used for announcements or bulk messages.

#### Recipient Priority:

1. **Dry Run Mode:** Sends only to `approver.txt`
2. **Live Mode:** Uses first available in this priority:
   - `to.txt` (if exists, merges with `additional_to.txt`)
   - `filter.txt + inventory.csv` (creates `to.txt`, merges with `additional_to.txt`)
   - `additional_to.txt` only (creates `to.txt`)
3. Additionally merges any recipients from:
   - `cc.txt`
   - `bcc.txt`

#### 📝 NEW Features:

- **Smart Merging:** `additional_to.txt` is automatically merged with filter results or `to.txt`
- **Auto-generation:** `to.txt` is created automatically from filter results for future reference
- **Enhanced Logging:** Detailed logs show merge operations and duplicate removal
- **Dry-run Protection:** Existing `to.txt` is preserved during dry-run mode

---

### 📬 Multi Mode

**Sends multiple personalized emails.** Used for targeted campaigns.

#### Recipient Logic:

1. Each line in `filter.txt` produces one email.
2. Recipients are derived by applying that filter to `inventory.csv`.
3. `additional_to.txt` (if present) is merged with **every** email's recipient list.
4. `cc.txt` and `bcc.txt` are applied globally to all emails.
5. In **dry-run**, all recipient lists are replaced with `approver.txt`.

#### 📝 NEW Features:

- **Template Substitution:** Use `field.txt` to define fields for placeholder replacement
- **Recipient Files:** Individual recipient files are saved for each filter in `recipients/` folder
- **Comprehensive Summary:** Detailed summary files with statistics and breakdowns
- **Enhanced Logging:** Per-filter logging with field value extraction

## 📋 Template Substitution (Multi Mode)

**NEW:** Multi mode now supports template substitution using field values extracted from filters.

### Setup:

1. Create `field.txt` with field names (one per line)
2. Use placeholders in `subject.txt` and `body.html`
3. Filter conditions will extract values for substitution

### Example field.txt:

```
department
region
status
```

### Example subject.txt:

```
Monthly Report for {department} - {region}
```

### Example filter.txt:

```
department="sales",region="north"
department="marketing",region="south"
```

This will generate two emails with subjects:

- "Monthly Report for sales - north"
- "Monthly Report for marketing - south"

## 📁 Enhanced Recipients Management

**NEW:** NotifyBot now automatically saves recipient information for reference and auditing.

### Single Mode:

- Creates `to.txt` from filter results if it doesn't exist
- Merges `additional_to.txt` with existing recipients
- Detailed logging of merge operations

### Multi Mode:

- Creates `recipients/` subfolder
- Individual files for each filter: `filter_001_department_sales.txt`
- Separate files for CC and BCC recipients
- Comprehensive summary file: `multi_mode_summary.txt`
- Consolidated unique recipients file: `all_unique_recipients.txt`

## 🧪 Enhanced Dry-Run Mode

**UPDATED:** Dry-run mode now provides more detailed information and better recipient file management.

### New Features:

- **Detailed Draft Info:** Draft emails include comprehensive recipient breakdown
- **Filter Information:** Multi-mode drafts show which filter generated the email
- **Recipient File Generation:** Creates recipient files even in dry-run mode for review
- **Preservation Mode:** Existing `to.txt` files are not overwritten during dry-run
- **Enhanced Statistics:** More detailed logging of what would happen in live mode

**Always run dry-run first to prevent unintended mass emails.**

## 📊 Enhanced Logging

**UPDATED:** Logs are written to `/notifybot/logs/notifybot.log` in CSV format with expanded emoji categories for quick scanning.

```
ℹ️ Info, ⚠️ Warning, ❌ Error, ✅ Success, 📝 Draft, 🔧 Mode,
⏳ Processing, 💾 Backup, 📂 File, ✋ Confirmation, ✍️ Signature
```

📡 All logs are also forwarded in real-time to **Splunk** for auditing and long-term reference.

[📊 Open Splunk Dashboard](https://tinyurl/notifybot)

## 📎 Attachments & 🖼️ Images

- 📎 **Attachments:** Files in `attachment/` are sent as attachments (up to 15MB each)
- 🖼️ **Embedded Images:** Images in `images/` are automatically embedded in HTML emails to prevent blocking
- 🔗 **Image References:** Use relative paths in HTML: `<img src="logo.png">`
- ⚠️ **External Images:** External URLs are preserved but may be blocked by email clients

## 🎯 Command Line Examples

### Basic Dry-Run (Always start here):

```bash
/notifybot/venv/bin/python notifybot.py --base-folder newsletter_august --dry-run
```

### Single Mode (Live):

```bash
/notifybot/venv/bin/python notifybot.py --base-folder newsletter_august --mode single --batch-size 500 --delay 5.0
```

### Multi Mode (Live):

```bash
/notifybot/venv/bin/python notifybot.py --base-folder newsletter_august --mode multi --delay 2.0
```

### ⚠️ Automated Script (with force - Use with extreme caution):

```bash
/notifybot/venv/bin/python notifybot.py --base-folder newsletter_august --mode single --force
```

## ✅ Approval Process

**UPDATED:** Before sending email in live mode, `approver.txt` ensures dry-run copies are reviewed and approved with enhanced draft information.

### Draft Email Features:

- 📋 **Recipient Breakdown:** Shows original TO, CC, BCC counts
- 🎯 **Filter Information:** Multi-mode shows which filter generated the email
- 📊 **Statistics:** Total recipient counts and campaign scope
- 🔍 **Review Files:** Generated recipient files for detailed review

## 🚀 Best Practices & Tips

### 🎯 Getting Started:

1. Always start with `--dry-run` to test your configuration
2. Review generated recipient files in the `recipients/` folder
3. Check the Splunk dashboard for detailed logs
4. Use small batch sizes for large campaigns to avoid overwhelming the mail server

### 📧 Email Best Practices:

- Embed images instead of linking to external URLs
- Test filter logic with a small subset first
- Use meaningful campaign folder names

### 🔧 Advanced Features:

- Use template substitution in multi-mode for personalized campaigns
- Leverage `additional_to.txt` for adding VIPs to all campaigns
- Use regex filters for complex recipient selection
- Monitor logs in real-time via Splunk dashboard
