# NotifyBot Email Sender - Runbook

## Overview

NotifyBot is a bulk email sender script with advanced features such as RFC-compliant email validation, attachment filtering, batch sending with delays, dry-run mode, recipient filtering based on CSV data, and comprehensive logging.

## Prerequisites

- Python 3.6 or newer installed
- SMTP server running on localhost or accessible (default SMTP server is localhost)
- Required Python package: `email-validator`

Install dependencies via:

```bash
pip install email-validator
```

## Files and Directory Structure

Your email campaign folder should contain:

### Required files:
- `from.txt` — Sender email address (single line)
- `subject.txt` — Email subject line
- `body.html` — HTML content of the email body
- `approver.txt` — List of approver emails (one per line)

### Optional files:
- `to.txt` — Primary recipient list (auto-generated if missing via filters)
- `cc.txt` — CC recipient list
- `bcc.txt` — BCC recipient list
- `additional_to.txt` — Additional recipients appended
- `inventory.csv` — CSV data for filtering recipients
- `filter.txt` — CSV defining filter conditions
- `attachments/` — Folder with files to attach

## Running NotifyBot

Run the script from the command line:

```bash
python notifybot.py /path/to/email/folder
```

### Command-line options:

- `--dry-run` - Sends the email only to approvers for testing
- `--batch-size INTEGER` - Number of recipients per batch (default: 500)
- `--delay INTEGER` - Seconds delay between batches (default: 5)
- `--attachments-folder PATH` - Use a custom folder for attachments
- `--max-attachment-size INTEGER` - Max size per attachment in MB (default: 10 MB)

### Example commands:

**Dry run:**
```bash
python notifybot.py --dry-run /path/to/campaign
```

**Send with smaller batches and longer delay:**
```bash
python notifybot.py --batch-size 100 --delay 10 /path/to/campaign
```

**Send with custom attachments folder:**
```bash
python notifybot.py --attachments-folder /custom/attachments /path/to/campaign
```

## Email Sending Workflow

1. **Validation**: Checks presence of required files and validates email addresses
2. **Filtering**: If `inventory.csv` and `filter.txt` exist, uses filters to generate `to.txt` if missing
3. **Recipient List**: Appends `additional_to.txt` emails and deduplicates the final recipient list
4. **Dry-run Mode**: Sends the draft email only to approvers
5. **Sending**: Sends emails in batches with specified batch size and delay
6. **Attachments**: Attachments filtered by max size limit
7. **Logging**: All operations are logged in `notifybot.log`

## Logs and Monitoring

- **Log file**: `notifybot.log` in the working directory
- **Logs include**:
  - File operations and validation errors
  - Invalid emails skipped
  - Sending results per batch
  - Attachment processing warnings/errors

Check this log file regularly for errors and summary information.

## Common Issues & Troubleshooting

| Issue | Message Example | Resolution |
|-------|----------------|------------|
| Missing required files | Error: Missing: from.txt, subject.txt | Ensure all required files are present in base folder |
| Invalid email addresses | Warning: Invalid email skipped: bad-email | Correct or remove invalid emails from files |
| SMTP connection failure | Failed to send to [...]: Connection refused | Verify SMTP server is running and accessible |
| Attachments too large | Skipping large-file.pdf: 15.2MB > limit | Reduce attachment size or increase max size option |
| No recipients | No recipients. | Check that to.txt is populated or filters are correctly applied |

## Best Practices

- Always start with `--dry-run` to validate content and recipients
- Use appropriate batch sizes and delay to avoid SMTP overload
- Validate email address lists before large campaigns
- Keep attachments small and relevant
- Monitor logs actively for errors and warnings
- Backup campaign folders before sending

## Maintenance & Contribution

- The script uses Python 3 standard libraries and `email-validator`
- Code follows PEP8 style and includes docstrings
- To contribute: fork repo → create feature branch → test changes → submit PR
- Review logs to detect regressions or runtime issues

## Support

- Check troubleshooting section and logs first
- Report detailed issues including logs, command used, and environment details
- Ensure your SMTP server configuration is correct and running
