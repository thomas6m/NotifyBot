# 🚀 NotifyBot Runbook

Automated Email Batch Sender · Runbook & Reference Guide · sendmail

## Contents

- [Overview](#overview)
- [Usage](#usage) · [Root Directory](#root-directory)
- [Input Files](#input-files)
- [Modes & Recipients](#modes--recipients)
- [Exclusion List](#exclusion-list)
- [Filters & Placeholders](#filters--placeholders)
- [Dry-Run & Approval](#dry-run--approval)
- [Resume & Duplicate Protection](#resume--duplicate-protection)
- [Logging & Output](#logging--output)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

### 🚀 NotifyBot User Runbook

**NotifyBot**, our smart, scalable solution for email automation. Whether you're sending a handful of emails or thousands, NotifyBot makes it effortless, safe, and efficient. It supports both single and multi modes, with dry-run and signature capabilities.

- 📧 **Batch Email Sending:** Deliver emails in customizable batches with controlled delays
- 🖋️ **HTML Email Support:** Craft rich, styled messages (with attachments!)
- 🎯 **Recipient Filtering:** Easily target the right audience with CSV filters
- 🧪 **Dry Run Mode:** Test configurations safely without sending actual emails
- ✅ **Email Validation:** Automatically validate addresses to reduce bounces
- 📎 **Attachment Support:** Attach files up to 15MB each
- 🔁 **Deduplication:** Automatically remove duplicate recipients
- 📊 **Logging & Transparency:** Detailed logs with automatic log rotation

*Stay in control. Stay efficient. That’s the NotifyBot way.*

`notifybot.py` · `Python 3 · sendmail` · `<root> = --root or current directory`

`notifybot.py` sends HTML emails in controlled batches through the local `sendmail`. It supports **single mode** (one email to a whole list) and **multi mode** (one personalised email per filter line), with dry-run approval, a strictly enforced exclusion list and safe resume after failures.

> [!CAUTION]
> **Critical:** always run with `--dry-run` first and get the DRAFT approved. Do **not** use `--force` unless running an approved automated job. Running live without a dry-run review may result in unintended mass emails.

### How a Run Works

1.  **Resolve Root & Validate Inputs** — The root is `--root` if given, otherwise the current directory; it must contain `basefolder/`. `--base-folder` must be inside `<root>/basefolder`. Required files are checked, `inventory.csv` is checked for broken rows, filter/field names are validated against the inventory headers, and `exclude.txt` is checked — any problem stops the run before anything is sent.
2.  **Build Recipient Lists** — TO from `to.txt` or `filter.txt` + `inventory.csv`, merged with `additional_to.txt`; CC/BCC from `cc.txt` / `bcc.txt`. Addresses are validated and de-duplicated (case-insensitive).
3.  **Apply Exclusions** — Every address in `exclude.txt` is removed from TO, CC, BCC and approvers.
4.  **Summary & Confirmation** — Counts, batch size, delay and resume status are shown. You must type `yes` to proceed (skipped only with `--force`).
5.  **Send in Batches** — Recipients already in `sent.log` are skipped. Each batch is re-checked against `exclude.txt` immediately before sendmail is called, then sent with `--delay` seconds between batches.
6.  **Record & Report** — Delivered addresses are appended to `sent.log` (live only). A summary of successful/failed batches is logged to `<root>/logs/notifybot.log`.

### What's New

> [!TIP]
> - **`exclude.txt`** — listed addresses never receive the email (TO, CC, BCC or approvers). See [Exclusion List](#exclusion-list).
> - **Resume** — re-running the same command sends only to recipients not yet delivered (`sent.log`). New `--ignore-sent-log`.
> - **Helper options** — `--test-filter` and `--analyze-inventory` (never send email).
> - **Anchored regex** — `=~` / `!~` must match the whole value: `country=~"UK"` no longer matches "Ukraine".
> - **Comma-separated addresses** accepted in recipient files, as well as `;` and one per line.
> - **Safety checks** — base folder confinement, `--batch-size` ≥ 1, `--delay` ≥ 0, and dry-run stops if there is no valid approver.
> - **Attachment names** in any language (e.g. `報告.pdf`) are preserved.
> - **Root directory is no longer fixed** — it is `--root`, or the directory you run from, and must contain `basefolder/`. `/notifybot` is no longer assumed. See [Root Directory](#root-directory).
> - **Inventory check** — a broken `inventory.csv` (e.g. a stray `"` that merges rows) now stops the run and names the line, instead of silently sending to a partial list.
> - **CC/BCC receive each email once** — tracked in `sent.log` like TO, instead of one copy per batch and per retry. See [Resume & Duplicates](#resume--duplicate-protection).
> - **CC/BCC lists in the duplicate check** — changing `cc.txt` or `bcc.txt` makes it a new message (sent to everyone again).
> - **Attachments in the duplicate check** — adding, removing, renaming or editing an attachment makes it a new message.
> - **No CSV cell-size limit** — the old `field larger than field limit (131072)` error no longer occurs for genuinely large cells.

## Usage

```bash
# From the root directory
cd <root>
/notifybot/venv/bin/python notifybot.py --base-folder <user-basefolder> [OPTIONS]

# Or from anywhere, naming the root explicitly
/notifybot/venv/bin/python notifybot.py --root <root> --base-folder <user-basefolder> [OPTIONS]
```

> [!NOTE]
> **Tip:** replace `<user-basefolder>` with your campaign folder name inside `<root>/basefolder/` — e.g. `--base-folder newsletter_august`. Pass the name only, not a full path.

### Command-Line Options

| Option                      | Default           | Description                                                                                                                                                                   |
|-----------------------------|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--root` (NEW)              | current directory | NotifyBot root directory. **Takes priority** over the current directory. Must contain `basefolder/`, otherwise the run fails (no fallback).                                   |
| `--base-folder`             | —                 | Campaign folder inside `<root>/basefolder` **(required, except with `--analyze-inventory`)**. Absolute paths, `..` and symlinks leading outside are rejected.                 |
| `--mode`                    | `single`          | `single` or `multi`. Overrides `mode.txt`.                                                                                                                                    |
| `--dry-run`                 | off               | Send only to approvers, with **DRAFT** subject prefix and a recipient-count banner.                                                                                           |
| `--batch-size`              | `500`             | TO recipients per email/batch, minimum 1. Applies to both modes.                                                                                                              |
| `--delay`                   | `5.0`             | Seconds between batches and between multi-mode filters, minimum 0.                                                                                                            |
| `--force`                   | off               | Skip the confirmation prompt. **Approved automation only.**                                                                                                                   |
| `--ignore-sent-log` (NEW)   | off               | Don't skip addresses already in `sent.log` — resends an identical email to everyone. Deliveries are still recorded. See [Resume & Duplicates](#resume--duplicate-protection). |
| `--test-filter` (NEW)       | off               | Show which inventory rows `filter.txt` matches and the addresses found. **Sends nothing.**                                                                                    |
| `--analyze-inventory` (NEW) | off               | List `inventory.csv` columns and sample values. **Sends nothing**; no base folder needed.                                                                                     |
| `--help`                    | —                 | Show help (including current inventory fields) and exit.                                                                                                                      |

### Common Invocations

The examples below are run from the root directory. Add `--root <root>` to run them from anywhere.

```bash
# Dry-run (always first)
/notifybot/venv/bin/python notifybot.py --base-folder <user-basefolder> --dry-run

# Live, single mode (default)
/notifybot/venv/bin/python notifybot.py --base-folder <user-basefolder>

# Live, multi mode with custom batch size and delay
/notifybot/venv/bin/python notifybot.py --base-folder <user-basefolder> --mode multi --batch-size 500 --delay 5.0

# Preview filter matches (sends nothing)
/notifybot/venv/bin/python notifybot.py --base-folder <user-basefolder> --test-filter

# Inspect inventory fields and values (sends nothing)
/notifybot/venv/bin/python notifybot.py --analyze-inventory

# Approved full resend of an identical email
/notifybot/venv/bin/python notifybot.py --base-folder <user-basefolder> --ignore-sent-log

# Same dry-run, from any directory
/notifybot/venv/bin/python notifybot.py --root /notifybot --base-folder <user-basefolder> --dry-run
```

### Root Directory

The root directory is **not fixed in the script**. It is chosen in this order:

| Priority | Source                                                        | Example             |
|----------|---------------------------------------------------------------|---------------------|
| 1        | `--root <dir>` on the command line                            | `--root /notifybot` |
| 2        | The current working directory (where you run the script from) | `cd /notifybot`     |

Everything else is resolved under the root: `<root>/basefolder/`, `<root>/inventory/inventory.csv`, `<root>/logs/notifybot.log` and `<root>/signature.html`. Each run logs which root it used, e.g. `NotifyBot root: /notifybot (from --root)`.

> [!CAUTION]
> **The root must contain `basefolder/`**, otherwise the run stops immediately (exit code 2) and creates nothing. If `--root` is given but invalid, the run fails — it does **not** fall back to the current directory. The `NOTIFYBOT_ROOT` environment variable is not used.

> [!WARNING]
> **Scheduled jobs (cron):** jobs usually start in the user's home directory, not the NotifyBot folder. Always set the root explicitly:
>
> ```bash
> 0 9 * * 1  cd /notifybot && /notifybot/venv/bin/python notifybot.py --base-folder weekly --force
> # or
> 0 9 * * 1  /notifybot/venv/bin/python /notifybot/notifybot.py --root /notifybot --base-folder weekly --force
> ```

## Input Files

### File Reference

| File                      | Location            | Purpose                                                                                                                   |
|---------------------------|---------------------|---------------------------------------------------------------------------------------------------------------------------|
| `subject.txt`             | base folder         | Subject line; `{field}` placeholders allowed in multi mode. *(required)*                                                |
| `body.html`               | base folder         | HTML body; `{field}` placeholders allowed in multi mode. *(required)*                                                   |
| `from.txt`                | base folder         | Sender address, e.g. `ops@example.com`. *(required)*                                                                    |
| `approver.txt`            | base folder         | Recipients of dry-run DRAFTs. *(required)*                                                                              |
| `to.txt`                  | base folder         | Direct TO list. Takes priority over `filter.txt` in single mode.                                                          |
| `filter.txt`              | base folder         | Filter conditions on `inventory.csv`. Required in multi mode.                                                             |
| `additional_to.txt`       | base folder         | Extra TO recipients, merged with the main source (added to every multi-mode email).                                       |
| `cc.txt` / `bcc.txt`      | base folder         | CC / BCC. Each address receives each email **once** — with the first batch that succeeds (and once per multi-mode email). |
| `exclude.txt` (NEW)       | base folder         | Addresses that must never receive the email.                                                                              |
| `field.txt`               | base folder         | Multi mode: inventory field names (one per line) used for `{field}` placeholders.                                         |
| `field-inventory.csv`     | base folder         | Optional local inventory used for placeholder values instead of the global one.                                           |
| `mode.txt`                | base folder         | `single` or `multi`; overridden by `--mode`.                                                                              |
| `attachment/` · `images/` | base folder         | Files to attach · images to embed in the body.                                                                            |
| `signature.html`          | `<root>/`           | Global signature appended to every email, all campaigns.                                                                  |
| `inventory.csv`           | `<root>/inventory/` | Global inventory for filters; must contain an `email` column.                                                             |

> [!NOTE]
> **Recipient file format** (`to.txt`, `cc.txt`, `bcc.txt`, `additional_to.txt`, `approver.txt`): one address per line, or several separated by `;` or `,`. Invalid addresses — including any starting with `-` — are skipped with a warning.

### Inventory Checks

Before any recipients are built from `inventory.csv` (or `field-inventory.csv` in multi mode), the whole file is checked:

| Problem                                                                                           | Result                                                                                        |
|---------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| A cell containing a line break — usually a stray `"` that merges the following rows into one cell | **Run stops**, naming the line and column to fix. Nothing is sent and no `to.txt` is created. |
| File not UTF-8, empty, or unreadable                                                              | **Run stops.** Re-save as "CSV UTF-8".                                                        |
| A row with more/fewer columns than the header                                                     | Warning with line numbers; extra cells are ignored.                                           |
| A very large cell (e.g. a long notes column)                                                      | Allowed — there is no cell-size limit.                                                        |
| Any read error while filtering or filling placeholders                                            | **Run stops** — it never continues with a partially-read inventory.                           |

### Directory Structure

```text
<root>/                            (--root, or the directory you run from)
  ├── basefolder/                  (required - marks a valid root)
  │   └── <user-basefolder>/
  │       ├── subject.txt
  │       ├── body.html
  │       ├── from.txt
  │       ├── approver.txt
  │       ├── to.txt               (optional)
  │       ├── filter.txt           (optional in single, required in multi)
  │       ├── additional_to.txt    (optional)
  │       ├── cc.txt / bcc.txt     (optional)
  │       ├── exclude.txt          (optional)
  │       ├── field.txt            (optional, multi)
  │       ├── field-inventory.csv  (optional, multi)
  │       ├── mode.txt             (optional)
  │       ├── attachment/          (optional)
  │       ├── images/              (optional)
  │       ├── sent.log             (auto — live runs)
  │       └── recipients/          (auto — multi mode)
  ├── signature.html               (optional, global)
  ├── inventory/
  │   └── inventory.csv
  └── logs/
      └── notifybot.log
```

## Modes & Recipients

#### Single Mode (default)

One email to the whole list, split into batches of `--batch-size`.

- **Required:** `subject.txt`, `body.html`, `from.txt`, `approver.txt`
- **At least one source:** `to.txt`, `filter.txt` + inventory, `additional_to.txt`, `cc.txt` or `bcc.txt`
- **Optional:** `exclude.txt`, `attachment/`, `images/`, `mode.txt`

#### Multi Mode

One personalised email **per line of `filter.txt`**, each to the rows that line matches.

- **Required:** the four files above + `filter.txt` + global `inventory.csv`
- **Optional:** `field.txt`, `field-inventory.csv`, `additional_to.txt`, `cc.txt`, `bcc.txt`, `exclude.txt`, `attachment/`, `images/`
- Writes a `recipients/` folder with each filter's list and a summary.

### Recipient Priority — Single Mode

| Step | Source                         | Behaviour                                                             |
|------|--------------------------------|-----------------------------------------------------------------------|
| 1    | `to.txt`                       | If present, always the primary TO list.                               |
| 2    | `filter.txt` + `inventory.csv` | Used only if `to.txt` is absent. The result is **saved as `to.txt`**. |
| 3    | `additional_to.txt`            | Merged with the source above, or used alone.                          |
| 4    | `cc.txt` / `bcc.txt`           | Sent once, with the first successful batch; don't affect TO.          |
| 5    | `exclude.txt`                  | Removes listed addresses from TO, CC and BCC.                         |

> [!CAUTION]
> **Stale `to.txt`:** when `filter.txt` is used, the result is saved as `to.txt` — **even during a dry-run**. From then on `to.txt` wins and later edits to `filter.txt` are ignored. After changing `filter.txt`, **delete `to.txt`** and dry-run again before going live.

### Recipient Priority — Multi Mode

| Step | Source                         | Behaviour                                                                        |
|------|--------------------------------|----------------------------------------------------------------------------------|
| 1    | `filter.txt` + `inventory.csv` | Each line = one email; recipients are the matched rows' `email` values.          |
| 2    | `field.txt`                    | Placeholder values from matched rows (`field-inventory.csv` if present).         |
| 3    | `additional_to.txt`            | Added to **every** email.                                                        |
| 4    | `cc.txt` / `bcc.txt`           | Added once to every personalised email.                                          |
| 5    | `exclude.txt`                  | Removes listed addresses; a filter whose recipients are all excluded is skipped. |

> [!NOTE]
> **CC/BCC receive each email once** (NEW) — they go with the **first batch that succeeds**, are recorded in `sent.log`, and are not included in later batches or re-runs. Example: 1,200 TO recipients with `--batch-size 500` = 3 batches; CC/BCC are in batch 1 only. If batch 1 fails they move to batch 2. In multi mode each filter's email is a different message, so CC/BCC get one copy per filter.

> [!WARNING]
> **Cc header:** because CC travels with one batch only, only that batch's recipients see the `Cc:` line; recipients in later batches do not. BCC is never shown in headers.

> [!NOTE]
> If no recipient source is found, the run stops with an error in both dry-run and live mode. Multi mode also stops if `filter.txt` / `inventory.csv` is missing or a field name doesn't exist in the inventory headers.

## Exclusion List

Any address in `exclude.txt` will **never** receive the email — not as TO, CC, BCC, nor as a dry-run approver — whichever file it came from.

### Format

```text
# Opted out - ticket 4521
john@example.com
"Tan, John" <john.tan@example.com>
Carol <carol@example.com>; dave@example.com, erin@example.com
```

- One address per line, or separated by `;` or `,`. `Name <address>` is accepted.
- Lines starting with `#` are comments.
- Matching is case-insensitive.

### Enforcement

| Layer                | What Happens                                                                                                                                                                                                   |
|----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Strict file check    | If any line can't be read as an address, the run **stops before sending anything** and names the line.                                                                                                         |
| List filtering       | Excluded addresses are removed from TO, CC, BCC and approvers while lists are built.                                                                                                                           |
| Final pre-send check | `exclude.txt` is re-read immediately before every batch. If any excluded address is present, the whole batch is **BLOCKED** — nothing is sent for it. This also catches edits made while a run is in progress. |
| Approvers            | An excluded approver is skipped; if every approver is excluded, the dry-run stops.                                                                                                                             |
| `to.txt`             | Not modified — exclusions apply at send time, so removing someone from `exclude.txt` restores them.                                                                                                            |

> [!WARNING]
> If every TO recipient is excluded but CC/BCC remain, the email still goes to CC/BCC (a warning is logged). If nobody remains, the run stops.

> [!CAUTION]
> **Aliases are not detected.** Excluding `john@example.com` does not block `john+hr@example.com` or `j.tan@example.com`. List every address the person uses.

## Filters & Placeholders

### Filter Syntax (`filter.txt`)

| Operator      | Meaning                                      | Example                             |
|---------------|----------------------------------------------|-------------------------------------|
| `=`           | Exact match (case-insensitive)               | `department="sales"`                |
| `!=`          | Not equal (case-insensitive)                 | `region!="europe"`                  |
| `=~`          | Regex match — must match the **whole** value | `country=~"USA\|Canada"`             |
| `!~`          | Regex not match — whole value                | `email!~".*(test\|demo).*"`          |
| `*` `?` `[ ]` | Wildcards with `=`                           | `status=active*`                    |
| `,`           | AND — all conditions on the line             | `department="sales",region="north"` |
| New line      | OR — and a separate email in multi mode      | —                                   |
| `#`           | Comment line                                 | `# Sales only`                      |

### Sample filter.txt

```text
# Sales in North America OR Marketing globally
department="sales",country=~"USA|Canada|Mexico"
department="marketing"

# Everyone except contractors (contains-match needs .*)
name!~".*(Contract|Temp|Intern).*"
```

> [!WARNING]
> **Anchored regex:** `country=~"UK"` matches `UK` but not `Ukraine`; use `.*UK.*` for "contains".  
> **No commas in values:** commas always split conditions, so `"Washington, DC"` or regex counts like `{2,5}` are not supported.  
> **Field names** must exist in the `inventory.csv` headers or the run stops — check with `--analyze-inventory`, preview with `--test-filter`.

### Placeholders (Multi Mode)

List field names in `field.txt` and use them as `{field}` in `subject.txt` / `body.html`. Each email gets values from the rows its filter line matched.

```text
# field.txt
department
region

# subject.txt
Maintenance notice for {department} ({region})
```

| Values Found | Rendered As                                    |
|--------------|------------------------------------------------|
| 1            | `sales`                                        |
| 2            | `sales and hr`                                 |
| 3 – 5        | `a, b, and c`                                  |
| More than 5  | First 3 + `and N more`                         |
| None         | Left as-is (e.g. `{region}`) — check the DRAFT |

## Dry-Run & Approval

With `--dry-run`, NotifyBot sends only to `approver.txt` (minus any in `exclude.txt`). The subject gets a **DRAFT** prefix and the body starts with a banner showing the real TO / CC / BCC counts after exclusions (and the filter used, in multi mode).

> [!NOTE]
> A dry-run never reads or writes `sent.log`, but it **may create `to.txt`** — see the stale `to.txt` warning in [Modes & Recipients](#modes--recipients).

### Approval Flow

1.  **Run Dry-Run** — Approvers receive the DRAFT with the real recipient counts.
2.  **Review & Approve** — Approvers check content, subject, attachments and counts, and confirm by reply.
3.  **Run Live** — Run the same command without `--dry-run`. Don't change subject, body or recipient files between approval and the live run.

## Resume & Duplicate Protection

In every live run, each address that successfully receives the email is written to `<root>/basefolder/<user-basefolder>/sent.log`, tied to the exact message it received. On the next live run of an identical message, everyone already in `sent.log` is skipped.

This makes retries safe: if batch 7 of 12 fails, fix the cause and **re-run the same command** — only batches 7–12 go out, and the people in batches 1–6 do not get a second copy. The confirmation summary shows how many recipients will be skipped.

### sent.log Format

```text
# timestamp            message-fingerprint   address
2026-09-27T21:31:57    acd697cb26c38534      a1@example.com
2026-09-27T21:31:57    acd697cb26c38534      a2@example.com
```

### How a Duplicate Is Detected

An email is treated as a duplicate only when **both** checks match an earlier live run of the same campaign folder.

1.  **Same message — the fingerprint matches** — Each message gets a fingerprint: a SHA-256 hash of six values, shortened to 16 characters (e.g. `acd697cb26c38534`). The comparison is exact, character by character — only leading/trailing spaces and blank lines in each file are ignored.
2.  **Same person — the TO, CC or BCC address is already recorded** — For a matching fingerprint, each TO, CC and BCC address is compared with the addresses in `sent.log` (upper/lower case ignored: `John@Example.com` = `john@example.com`). Recorded addresses are skipped; everyone else is sent to. An address is recorded only after sendmail accepts its batch — failed or BLOCKED batches are never recorded, so those people are retried.

#### What goes into the fingerprint

| \#  | Value                  | Source                                                                                                                                                                                           |
|-----|------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1   | Sender                 | `from.txt`                                                                                                                                                                                       |
| 2   | Subject                | `subject.txt` — in multi mode, after `{field}` placeholders are filled in                                                                                                                        |
| 3   | Body                   | `body.html` **plus** `signature.html` — in multi mode, after placeholders are filled in                                                                                                          |
| 4   | Filter line            | Multi mode only: the `filter.txt` line the email belongs to (blank in single mode)                                                                                                               |
| 5   | Attachments (NEW)      | Every file in `attachment/`: its **name** and a **SHA-256 checksum of its contents**, in name order. Only included when attachments exist.                                                       |
| 6   | CC and BCC lists (NEW) | Every valid address in `cc.txt` and `bcc.txt` — lowercased, de-duplicated and sorted, with CC and BCC kept separate. Taken **before** `exclude.txt` is applied. Only included when CC/BCC exist. |

#### CC and BCC tracking

TO, CC and BCC addresses are all recorded, so every address receives a given message **at most once** — across batches and across re-runs.

| Situation                                                          | What CC/BCC receive                                             |
|--------------------------------------------------------------------|-----------------------------------------------------------------|
| Normal run, several batches                                        | One copy, with the first batch that succeeds                    |
| First batch fails                                                  | Moved to the next batch; still one copy                         |
| All batches fail                                                   | Nothing yet — sent with the first batch of the re-run           |
| Re-run after a partial failure                                     | Nothing — they already have it; only undelivered TO are retried |
| Address added to / removed from `cc.txt` or `bcc.txt`, then re-run | New message — **everyone** (TO, CC and BCC) gets it again       |
| `--ignore-sent-log`                                                | One copy again, with the first successful batch                 |

> [!WARNING]
> **Upgrading mid-campaign:** campaigns that have attachments or CC/BCC get a **new fingerprint** with this version, so a retry started with the new script treats them as a new message and sends to everyone. Finish any in-progress retry with the old script before upgrading. Campaigns with no attachments and no CC/BCC keep the same fingerprint; if their older `sent.log` exists it is used as normal.

> [!WARNING]
> Any change to these — one word, a fixed typo, an extra space inside the body, an edited signature, an attachment added, removed, renamed or edited, or a CC/BCC address added, removed or moved between CC and BCC — makes it a **new message**, and it goes to **everyone** (TO, CC and BCC).

> [!CAUTION]
> **Changing cc.txt or bcc.txt resends to all TO recipients.** Adding a single CC address after a campaign has gone out sends the whole email again to every TO recipient, not just the new CC. Finalise the CC/BCC lists before the live run.

> [!NOTE]
> **CC/BCC fingerprint rules:** the order of addresses, upper/lower case, duplicates and invalid lines don't matter — only the set of valid addresses. Adding someone to `exclude.txt` does **not** change the fingerprint (they are simply not sent to). Changing the lists back to an earlier version matches that earlier message, so people who already received it are skipped.

> [!NOTE]
> The attachment check reads file **contents**, not timestamps: copying or touching a file without changing its bytes is still the same message. SHA-256 is used rather than `cksum` (CRC32), which can miss changes. Campaigns without attachments have exactly the same fingerprint as before this check was added, so existing `sent.log` files remain valid.

#### What is NOT checked

| Not part of the check                         | What that means                                                                                                      |
|-----------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| Embedded image files (`images/`)              | Replacing `logo.png` with a new file of the same name does not make a new message.                                   |
| Recipient lists, batch size, delay, date/time | Changing these doesn't reset anything. The same message a week later is still skipped for people who already got it. |
| Other campaign folders                        | `sent.log` belongs to one base folder. The same email sent from a different folder is not treated as a duplicate.    |

#### Examples

| Change since the last run                                   | Result                                                             |
|-------------------------------------------------------------|--------------------------------------------------------------------|
| Nothing — same command re-run                               | Already-delivered people skipped                                   |
| One word changed in `body.html`                             | New message — everyone gets it                                     |
| `signature.html` updated                                    | New message — everyone gets it (signature is part of the body)     |
| Attachment replaced with a new version (same file name)     | New message — everyone gets it                                     |
| Attachment added, removed or renamed                        | New message — everyone gets it                                     |
| Attachment copied/touched, contents unchanged               | Same message — already-delivered people skipped                    |
| 50 addresses added to `to.txt`                              | Same message — only the 50 new people get it                       |
| 1 address added to `cc.txt` or `bcc.txt`                    | New message — everyone gets it (TO, CC and BCC)                    |
| `cc.txt` re-ordered, or upper/lower case changed            | Same message — already-delivered people skipped                    |
| CC address added to `exclude.txt`                           | Same message — nobody re-sent; the excluded address is not sent to |
| Multi mode: a `{department}` value changed in the inventory | That filter's email is a new message — its recipients get it       |
| sendmail hangs                                              | Killed after 60 s; batch marked failed and retried on re-run       |
| `sent.log` deleted                                          | History cleared — the next run sends to everyone                   |

### The `--ignore-sent-log` Option

`--ignore-sent-log` switches off duplicate protection for one run: the email goes to the full recipient list, even people who already received this identical message.

- Delivered addresses are **still recorded** in `sent.log`, so the history stays complete.
- `exclude.txt` **still applies** — excluded people are always blocked.
- It has no effect on dry-runs, which never use `sent.log`.

#### Example — 5,000 recipients, all delivered successfully

| Command                            | Result                                                                                    |
|------------------------------------|-------------------------------------------------------------------------------------------|
| Same command again                 | `All TO recipients already received this email - nothing left to send` — nothing goes out |
| Same command + `--ignore-sent-log` | All 5,000 receive it a second time                                                        |

#### ✅ Use it when

- You deliberately want to resend the **identical** email, and it's approved.
- You changed **only an embedded image** in `images/` (not part of the fingerprint) and want everyone to get the new version.

#### ❌ Don't use it when

- **Retrying after a failure** — re-run the plain command so only undelivered people are sent to. Adding the option would give everyone who already got it a duplicate.
- **Sending a changed email** — an edited subject, body, attachment or CC/BCC list (e.g. "Reminder: …", or a new version of the report) is already a new message and goes to everyone.

> [!NOTE]
> Deleting `sent.log` has the same effect as `--ignore-sent-log`, but loses the delivery history. Prefer the option.

## Logging & Output

Logs are written to `<root>/logs/notifybot.log` in CSV format `timestamp_ms,username,message`, with emojis for quick scanning:

ℹ️ Info · ⚠️ Warning · ❌ Error · ✅ Success · 📝 Draft · 🔧 Mode · ⏳ Processing · ✋ Confirmation · 📂 File · 💾 Backup · ✍️ Signature

> [!WARNING]
> The log records full recipient addresses (including excluded and BLOCKED ones) for auditing — treat it as confidential.

All logs are also forwarded in real time to **Splunk** for auditing and long-term reference: [📊 Open Splunk Dashboard](https://tinyurl/notifybot)

### Generated Files

| File                                   | When                                            | Contents                             |
|----------------------------------------|-------------------------------------------------|--------------------------------------|
| `to.txt`                               | Single mode, filter or `additional_to.txt` only | Resolved TO list (before exclusions) |
| `sent.log`                             | Live runs                                       | Delivered addresses per message      |
| `recipients/filter_NNN_*.txt`          | Multi mode                                      | Recipients of each filter line       |
| `recipients/multi_mode_summary.txt`    | Multi mode                                      | Per-filter counts and grand total    |
| `recipients/all_unique_recipients.txt` | Multi mode                                      | Every unique TO address              |

### Attachments & Images

- Every file in `attachment/` is attached to every email; file names in any language are kept.
- Images referenced in `body.html` (e.g. `<img src="logo.png">`) are embedded when the file exists in `images/`. External `http(s)` images stay as links and may be blocked by mail clients.
- No size limit is enforced by NotifyBot; the mail server's message-size limit applies.

## Troubleshooting

| Message                                                                                                                 | Action                                                                                                                                     |
|-------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| `'...' (from current working directory) is not a NotifyBot root: it has no basefolder/ directory`                       | You ran the script from the wrong directory. `cd` to the root first, or add `--root <dir>`. Nothing was created or sent.                   |
| `NotifyBot root '...' (from --root) does not exist or is not a directory` / `... (from --root) is not a NotifyBot root` | Check the `--root` path; it must be a directory containing `basefolder/`.                                                                  |
| `Invalid base folder ... must be a directory inside '<root>/basefolder'`                                                | Pass the folder name only (e.g. `newsletter_august`), not a path or `..`. Check you are using the right root.                              |
| `inventory.csv has N cell(s) containing line breaks ... Fix the quote at: line X`                                       | Open `inventory.csv` at that line and remove or close the stray `"`. Nothing was sent.                                                     |
| `row(s) have a different number of columns than the header` (warning)                                                   | Check the listed lines for stray commas. The run continues; extra cells are ignored.                                                       |
| `field larger than field limit (131072)`                                                                                | Only seen with older versions of the script — upgrade. If a partial send happened, delete the `to.txt` it created before re-running.       |
| `exclude.txt has N entry that could not be read as an email address`                                                    | Fix or remove the named line(s). Nothing was sent.                                                                                         |
| `BLOCKED: batch contained ... listed in exclude.txt`                                                                    | An excluded address reached the send stage (e.g. `exclude.txt` edited mid-run). Nothing was sent for that batch — re-run the same command. |
| `No valid approver emails found` / `Every approver is listed in exclude.txt`                                            | Add at least one valid, non-excluded address to `approver.txt`.                                                                            |
| `No recipients left after applying exclude.txt`                                                                         | Everyone is excluded — check the recipient files and `exclude.txt`.                                                                        |
| `Field validation failed` / `Field '...' not found`                                                                     | Names in `filter.txt` / `field.txt` must match inventory headers exactly. Run `--analyze-inventory`.                                       |
| `All TO recipients already received this email`                                                                         | Delivered on an earlier run (`sent.log`). Use `--ignore-sent-log` only for an approved resend.                                             |
| `Sendmail failed with return code ...` / `Sendmail timeout`                                                             | Check the mail server, then re-run the same command to retry only failed batches.                                                          |
| `argument --batch-size: must be at least 1`                                                                             | Use batch size ≥ 1 and delay ≥ 0.                                                                                                          |

### Filter Matches Unexpected Rows

```bash
# Preview matches and extracted addresses
/notifybot/venv/bin/python notifybot.py --base-folder <user-basefolder> --test-filter

# See available fields and sample values
/notifybot/venv/bin/python notifybot.py --analyze-inventory

# After editing filter.txt, remove the stale list before dry-run
rm <root>/basefolder/<user-basefolder>/to.txt
```

### Check What Was Delivered

```bash
# Delivered addresses for a campaign
cut -f3 <root>/basefolder/<user-basefolder>/sent.log | sort -u

# Errors and blocked batches in the main log
grep -E "❌|BLOCKED" <root>/logs/notifybot.log | tail -20

# Which root did recent runs use?
grep "NotifyBot root" <root>/logs/notifybot.log | tail -5
```

## Best Practices

- [ ] **Know your root** — run from the root directory or pass `--root`; in cron jobs always use `cd <root> &&` or `--root`. Check the `NotifyBot root:` line at the start of each run.
- [ ] **Always dry-run first** — get the DRAFT approved and confirm the TO / CC / BCC counts in the banner before any live run.
- [ ] **Maintain exclude.txt** — add opt-outs with a `#` comment (who / why / ticket), and list every alias the person uses.
- [ ] **Test filters before sending** — use `--test-filter`; remember regex must match the whole value.
- [ ] **Delete stale to.txt** — after changing `filter.txt`, remove `to.txt` and dry-run again.
- [ ] **Don't change content between approval and live** — subject, body, attachments and recipient files should be exactly what approvers saw.
- [ ] **Retry with the same command** — after a failure, re-run unchanged so `sent.log` skips delivered recipients. Use `--ignore-sent-log` only for an approved full resend.
- [ ] **Finalise CC/BCC before going live** — any later change to `cc.txt` / `bcc.txt` resends the whole email to every recipient. Use `exclude.txt` to drop someone without triggering a resend.
- [ ] **Remember the Cc header** — CC/BCC receive each email once, with the first successful batch, so only that batch shows the `Cc:` line. If every recipient must see who was copied, use a `--batch-size` large enough for a single batch.
- [ ] **Avoid --force for manual runs** — the confirmation prompt is your last chance to catch a wrong count.
- [ ] **Keep inventory.csv clean** — save it as "CSV UTF-8" and run `--analyze-inventory` after editing; it checks the file for stray quotes without sending anything.
- [ ] **Protect the logs** — `notifybot.log` and `sent.log` contain recipient addresses; restrict access accordingly.

---

*End of Runbook — notifybot.py · Automated Email Batch Sender*
