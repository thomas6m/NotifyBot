# CLI Options

Here are the available command-line interface (CLI) options for the notifybot.py script:

## --base-folder (REQUIRED)

**Description:** Specifies the base directory containing email input files.

**Required files inside base folder:**
- `subject.txt` (email subject)
- `body.html` (email body)
- `from.txt` (email From address)
- `approver.txt` (approver emails for dry-run)

**Recipient source (at least one required for real email mode):**
- `to.txt` (List of recipient emails)
- `filter.txt` + `inventory.csv` (Filter-based recipient extraction)

## --dry-run (optional)

**Description:** Simulate sending emails without actually connecting to SMTP. Useful for testing.

## --batch-size (optional, default: 500)

**Description:** Defines the number of emails to send per batch.

## --delay (optional, default: 5.0 seconds)

**Description:** Specifies the delay (in seconds) between email batches.

## --force (optional)

**Description:** Skips the confirmation prompt. Useful for automation scenarios where you want to bypass manual checks and confirmation.

# Required Files in the Base Folder

For the NotifyBot to function properly, the following files must be present inside the base-folder:

## subject.txt (email subject)

**Description:** Contains the subject line of the email to be sent.

## body.html (email body)

**Description:** The HTML content of the email body.

## from.txt (email From address)

**Description:** Contains the "From" email address that will be used to send the email.

## approver.txt (approver emails for dry-run)

**Description:** If using the `--dry-run` option, this file lists the approvers who will be notified in the dry run.

## Recipient Source (one of the following):

### to.txt

**Description:** A list of recipient emails to whom the email should be sent. Must be present if not using `filter.txt` and `inventory.csv`.

### OR

### filter.txt + inventory.csv

**Description:** Use this combination for filtering recipients. The `filter.txt` file provides the criteria, while the `inventory.csv` file holds the list of valid recipients.

# Optional Files

## additional_to.txt (optional)

**Description:** If present, this file contains additional recipient emails that will be appended to `to.txt` after filtering and validation.

## filter.txt + inventory.csv (optional for advanced filtering)

**Description:** If you want to filter recipients based on certain conditions (such as filtering by groups or attributes), these files are necessary:

- **filter.txt:** Contains the filtering criteria (such as domains, groups, etc.).
- **inventory.csv:** A CSV file with a list of available recipients, possibly with additional attributes for filtering.

# Example CLI Usage

## Dry Run:

To simulate the process of sending emails without actually sending them, you can use the `--dry-run` option:

```bash
python notifybot.py --base-folder emails --dry-run
```

## Force Mode:

If you want to skip confirmation prompts for automation, you can add the `--force` flag:

```bash
python notifybot.py --base-folder emails --force
```

## With Batching and Delay:

Send emails in batches with a specific delay between batches:

```bash
python notifybot.py --base-folder emails --batch-size 300 --delay 10
```
