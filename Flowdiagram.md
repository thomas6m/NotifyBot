# NotifyBot Logic Flow Diagram

## Overview
NotifyBot is a Python-based email automation tool that sends bulk emails with filtering capabilities, batch processing, and comprehensive logging.

## Main Program Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            START NOTIFYBOT                             │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      PARSE COMMAND LINE ARGUMENTS                      │
│  • base_folder (required)                                              │
│  • --dry-run (optional)                                                │
│  • --batch-size (default: 500)                                         │
│  • --delay (default: 5 seconds)                                        │
│  • --log-level (default: INFO)                                         │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         CONFIGURE LOGGING                              │
│  • File handler (notifybot.log) - no colors                            │
│  • Console handler - with ANSI colors                                  │
│  • Set log level as specified                                          │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CALL send_email_from_folder()                       │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
```

## Core Function: send_email_from_folder()

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INITIALIZE BASE PATH                           │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CHECK REQUIRED FILES EXIST                          │
│  Required files:                                                        │
│  • from.txt        (sender email)                                      │
│  • subject.txt     (email subject)                                     │
│  • body.html       (email body content)                                │
│  • approver.txt    (approver email list)                               │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      MISSING FILES?                                     │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                 ┌────────────┴────────────┐
                 │                         │
                YES                       NO
                 │                         │
                 ▼                         ▼
┌─────────────────────────────┐   ┌─────────────────────────────────────────┐
│     LOG ERROR & EXIT        │   │         READ REQUIRED FILES            │
│  • Print missing files      │   │  • from.txt → from_email                │
│  • Exit with code 1         │   │  • subject.txt → subject                │
└─────────────────────────────┘   │  • body.html → body_html                │
                                  │  • approver.txt → approvers             │
                                  └─────────────────┬───────────────────────┘
                                                    │
                                                    ▼
                                  ┌─────────────────────────────────────────┐
                                  │        VALIDATE CONTENT                 │
                                  │  • Check if subject is empty            │
                                  │  • Check if body_html is empty          │
                                  │  • Check if approvers list is empty     │
                                  └─────────────────┬───────────────────────┘
                                                    │
                                                    ▼
                                  ┌─────────────────────────────────────────┐
                                  │       CONTENT VALIDATION                │
                                  └─────────────────┬───────────────────────┘
                                                    │
                                       ┌────────────┴────────────┐
                                       │                         │
                                  INVALID                     VALID
                                       │                         │
                                       ▼                         ▼
                            ┌─────────────────────────┐   ┌─────────────────────────────────────────┐
                            │     LOG ERROR & EXIT    │   │         PREPARE TO.TXT                  │
                            │  • Print error message  │   │  • Call prepare_to_txt()                │
                            │  • Exit with code 1     │   │  • Get attachments                      │
                            └─────────────────────────┘   └─────────────────┬───────────────────────┘
                                                                            │
                                                                            ▼
                                                          ┌─────────────────────────────────────────┐
                                                          │           DRY RUN MODE?                 │
                                                          └─────────────────┬───────────────────────┘
                                                                            │
                                                               ┌────────────┴────────────┐
                                                               │                         │
                                                              YES                       NO
                                                               │                         │
                                                               ▼                         ▼
                                                    ┌─────────────────────────┐   ┌─────────────────────────────────────────┐
                                                    │    SEND DRAFT EMAIL     │   │         SEND ACTUAL EMAILS              │
                                                    │  • Send to approvers    │   │  • Read recipient lists                 │
                                                    │  • Subject: [DRAFT] +   │   │  • Send in batches                      │
                                                    │    original subject     │   │  • Apply delays between batches        │
                                                    │  • Include attachments  │   │  • Log progress                         │
                                                    │  • Log and exit         │   └─────────────────┬───────────────────────┘
                                                    └─────────────────────────┘                     │
                                                                                                      ▼
                                                                                    ┌─────────────────────────────────────────┐
                                                                                    │        FINAL SUMMARY                    │
                                                                                    │  • Print total sent                     │
                                                                                    │  • Log completion                       │
                                                                                    └─────────────────────────────────────────┘
```

## Sub-process: prepare_to_txt()

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PREPARE TO.TXT                                 │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    GET FILTERED EMAIL IDS                              │
│  • Call get_filtered_emailids()                                        │
│  • Parse inventory.csv and filter.txt                                  │
│  • Apply filtering conditions                                          │
│  • Extract valid email addresses                                       │
│  • Remove duplicates with existing to.txt                              │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      NEW EMAILS FOUND?                                 │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                 ┌────────────┴────────────┐
                 │                         │
                YES                       NO
                 │                         │
                 ▼                         ▼
┌─────────────────────────────┐   ┌─────────────────────────────────────────┐
│    APPEND TO TO.TXT         │   │         SKIP APPEND                    │
│  • Write new emails         │   │  • Log no new emails                   │
│  • Log count added          │   └─────────────────┬───────────────────────┘
└─────────────────────────────┘                     │
                              │                     │
                              └─────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    READ ADDITIONAL_TO.TXT                              │
│  • Check if additional_to.txt exists                                   │
│  • Read additional email addresses                                     │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  ADDITIONAL EMAILS FOUND?                              │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                 ┌────────────┴────────────┐
                 │                         │
                YES                       NO
                 │                         │
                 ▼                         ▼
┌─────────────────────────────┐   ┌─────────────────────────────────────────┐
│    APPEND TO TO.TXT         │   │         SKIP APPEND                    │
│  • Write additional emails  │   │  • Continue to next step               │
│  • Log count added          │   └─────────────────┬───────────────────────┘
└─────────────────────────────┘                     │
                              │                     │
                              └─────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      DEDUPLICATE TO.TXT                                │
│  • Remove duplicate email addresses                                    │
│  • Keep only valid email formats                                       │
│  • Rewrite to.txt with clean list                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Sub-process: get_filtered_emailids()

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      GET FILTERED EMAIL IDS                            │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CHECK FILES EXIST                                   │
│  • inventory.csv (data source)                                         │
│  • filter.txt (filter conditions)                                      │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      FILES EXIST?                                      │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                 ┌────────────┴────────────┐
                 │                         │
                NO                        YES
                 │                         │
                 ▼                         ▼
┌─────────────────────────────┐   ┌─────────────────────────────────────────┐
│    RETURN EMPTY LIST        │   │         PARSE FILTER FILE               │
│  • Log warning              │   │  • Read CSV format                      │
│  • Return []                │   │  • Extract keys (header row)            │
└─────────────────────────────┘   │  • Extract conditions (data rows)       │
                                  └─────────────────┬───────────────────────┘
                                                    │
                                                    ▼
                                  ┌─────────────────────────────────────────┐
                                  │       PROCESS INVENTORY FILE            │
                                  │  • Read CSV with DictReader             │
                                  │  • For each row in inventory:           │
                                  │    - Check against all conditions      │
                                  │    - If match found:                    │
                                  │      • Extract emailids field          │
                                  │      • Split by semicolon/comma        │
                                  │      • Validate email format           │
                                  │      • Add to result set               │
                                  └─────────────────┬───────────────────────┘
                                                    │
                                                    ▼
                                  ┌─────────────────────────────────────────┐
                                  │        REMOVE EXISTING EMAILS           │
                                  │  • Read existing to.txt                 │
                                  │  • Remove already processed emails      │
                                  │  • Return new emails only               │
                                  └─────────────────────────────────────────┘
```

## Sub-process: Batch Email Sending

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BATCH EMAIL SENDING                            │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    READ RECIPIENT LISTS                                │
│  • to.txt (primary recipients)                                         │
│  • cc.txt (carbon copy recipients)                                     │
│  • bcc.txt (blind carbon copy recipients)                              │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    RECIPIENTS EXIST?                                   │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                 ┌────────────┴────────────┐
                 │                         │
                NO                        YES
                 │                         │
                 ▼                         ▼
┌─────────────────────────────┐   ┌─────────────────────────────────────────┐
│       LOG & RETURN          │   │         PROCESS IN BATCHES              │
│  • Log no recipients        │   │  • Split to.txt into batch_size chunks  │
│  • Return without sending   │   │  • For each batch:                      │
└─────────────────────────────┘   │    - Call send_email()                  │
                                  │    - Log batch number                   │
                                  │    - Wait delay seconds (if not last)  │
                                  │    - Update total sent counter         │
                                  └─────────────────┬───────────────────────┘
                                                    │
                                                    ▼
                                  ┌─────────────────────────────────────────┐
                                  │          FINAL SUMMARY                  │
                                  │  • Print "Emails sent successfully"     │
                                  │  • Print total sent count               │
                                  │  • Log summary                          │
                                  └─────────────────────────────────────────┘
```

## Sub-process: send_email()

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SEND EMAIL                                   │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CREATE EMAIL MESSAGE                                │
│  • Set Subject, From, To headers                                       │
│  • Add CC if provided                                                  │
│  • Add HTML body                                                       │
│  • Attach files if provided                                            │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    COMBINE ALL RECIPIENTS                               │
│  • to + cc + bcc (deduplicated)                                        │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      SEND VIA SMTP                                     │
│  • Connect to localhost SMTP server                                    │
│  • Send message to all recipients                                      │
│  • Log success/failure                                                 │
│  • Print status to console                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

## File Structure Requirements

```
base_folder/
├── from.txt              (Required) - Sender email address
├── subject.txt           (Required) - Email subject line
├── body.html             (Required) - Email body content in HTML
├── approver.txt          (Required) - Approver email addresses
├── to.txt                (Generated) - Primary recipients
├── cc.txt                (Optional) - CC recipients
├── bcc.txt               (Optional) - BCC recipients
├── additional_to.txt     (Optional) - Additional recipients to add
├── inventory.csv         (Optional) - Data source for filtering
├── filter.txt            (Optional) - Filter conditions (CSV format)
├── attachment/           (Optional) - Directory for email attachments
│   ├── file1.pdf
│   └── file2.docx
└── notifybot.log         (Generated) - Log file
```

## Key Features

1. **Email Validation**: All email addresses are validated using regex pattern
2. **Deduplication**: Automatic removal of duplicate email addresses
3. **Batch Processing**: Configurable batch size and delay between batches
4. **Dry Run Mode**: Send draft to approvers only for testing
5. **Attachment Support**: Automatic detection and attachment of files
6. **Comprehensive Logging**: File and console logging with colored output
7. **Error Handling**: Graceful handling of missing files and SMTP errors
8. **Filtering System**: CSV-based filtering for dynamic recipient selection

## Exit Conditions

- **Success**: All emails sent successfully
- **Missing Required Files**: Exit code 1
- **Empty Subject/Body**: Exit code 1
- **Empty Approver List**: Return without sending
- **No Recipients**: Return without sending
- **SMTP Errors**: Log error but continue with next batch
