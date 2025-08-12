#!/usr/bin/env python3
"""
NotifyBot - Advanced Email Campaign Management System
===================================================

A sophisticated email automation tool supporting both single and multi-mode campaigns 
with template personalization, batch processing, image embedding, and comprehensive 
recipient management through CSV-based filtering with priority-based field validation.

OVERVIEW:
---------
NotifyBot operates in two primary modes:

1. SINGLE MODE: One email campaign to all matching recipients
2. MULTI MODE: Multiple personalized emails based on filter conditions

The system supports dry-run testing, batch processing, HTML email with embedded images,
file attachments, CC/BCC recipients, global signature management, and extensive logging.

DIRECTORY STRUCTURE:
-------------------
/notifybot/                          # Root directory (NOTIFYBOT_ROOT)
├── basefolder/                      # Base folder for all campaigns (BASEFOLDER_PATH)
│   └── <campaign-name>/             # Individual campaign folder
│       ├── subject.txt              # Email subject line
│       ├── body.html                # Email body (HTML format)
│       ├── from.txt                 # Sender email address
│       ├── approver.txt             # Approver emails for dry-run mode
│       ├── to.txt                   # Direct recipient list (optional/auto-generated)
│       ├── cc.txt                   # CC recipients (optional)
│       ├── bcc.txt                  # BCC recipients (optional)
│       ├── additional_to.txt        # Additional TO recipients (optional)
│       ├── filter.txt               # Filter conditions (required for multi-mode)
│       ├── field.txt                # Field names for template substitution (optional)
│       ├── mode.txt                 # Mode specification: 'single' or 'multi' (optional)
│       ├── table-columns.txt        # Column specification for dynamic tables (conditional)
│       ├── field-inventory.csv      # Local field inventory (optional, takes priority)
│       ├── attachment/              # Folder for file attachments (optional)
│       │   └── *.* (files)          # Attachment files (15MB total limit)
│       ├── images/                  # Folder for email images (optional)
│       │   └── *.{jpg,png,gif}      # Image files for embedding
│       └── recipients/              # Auto-generated recipient backups
├── inventory/
│   ├── inventory.csv                # Global recipient database
│   └── test-inventory.csv           # Test recipient database
├── signature.html                   # Global email signature (optional)
└── logs/
    └── notifybot.log                # Comprehensive execution logs

OPERATING MODES:
---------------

SINGLE MODE:
- Sends ONE email to all matching recipients
- Recipients determined by: to.txt, filter.txt, additional_to.txt, cc.txt, bcc.txt
- Template personalization using field substitution: {fieldname}
- Batch processing for large recipient lists
- Automatic recipient merging and deduplication
- Example: Company-wide announcement

MULTI MODE:  
- Sends MULTIPLE personalized emails based on filter conditions
- Each filter condition generates a separate email
- Recipients filtered from inventory.csv per condition
- Template personalization per email using CSV data
- Dynamic table generation with customizable styling
- Field values extracted from matched CSV rows
- Example: Department-specific notifications with personalized content

PRIORITY-BASED FIELD VALIDATION SYSTEM:
---------------------------------------

The system implements a sophisticated priority-based validation approach:

1. FILTER VALIDATION (filter.txt):
   Priority Order:
   a) Local field-inventory.csv (if exists) - HIGHEST PRIORITY
   b) Global inventory.csv (test-inventory.csv in test mode) - FALLBACK
   
   - All filter field names must exist in the prioritized inventory
   - Ensures filter conditions reference valid database columns
   - Prevents runtime filtering failures

2. FIELD VALIDATION (field.txt):
   Priority Order: 
   a) Local field-inventory.csv (if exists) - HIGHEST PRIORITY
   b) Global inventory.csv (test-inventory.csv in test mode) - FALLBACK
   
   - Used for template substitution and dynamic table generation
   - Dynamic table fields require table-columns.txt validation
   - Field values extracted from the prioritized inventory source

3. TABLE VALIDATION (table-columns.txt):
   - Required when dynamic table fields are requested
   - All column names validated against prioritized inventory
   - Ensures dynamic table generation has valid data sources

4. TEST MODE INVENTORY SELECTION:
   - --test flag: Uses test-inventory.csv instead of inventory.csv
   - --test-inventory PATH: Uses custom test inventory file
   - Validation respects test mode inventory selection

FILTER SYNTAX:
--------------

Supports advanced PromQL-style filtering with multiple operators:

OPERATORS:
  =     Exact match (case-insensitive): department=Engineering  
  !=    Not equal: status!=inactive
  =~    Regex match: name=~"^John.*"
  !~    Regex not match
  *,?,[] Wildcard patterns: department=*Sales*

LOGIC:
  AND: department=Engineering,status=active    # Same line, comma-separated
  OR:  department=Engineering                  # Different lines
       department=Sales

EXAMPLES:
  # Department-based filtering
  department=Engineering
  
  # Exclude test accounts  
  email!~".*(test|demo|staging).*"
  
  # Multiple conditions (AND)
  department=Sales,status=active,region!=asia
  
  # Complex regex patterns
  title=~".*(Manager|Director|VP).*"
  
  # Comments and empty lines ignored
  # This is a comment
  department=Marketing
  
  status=active

TEMPLATE SUBSTITUTION & DYNAMIC TABLES:
--------------------------------------

Field values from inventory CSV can be substituted into templates:

BASIC SUBSTITUTION:
  Template: "Hello {name}, welcome to {department}!"
  Result:   "Hello John Smith, welcome to Engineering!"

DYNAMIC TABLE FIELDS:
  {dynamic_table}      # Complete HTML table with styling
  {table_rows}         # Standard table rows 
  {styled_table_rows}  # Striped table rows with alternating backgrounds
  {simple_table_rows}  # Minimal table rows without styling
  {csv_table_rows}     # Pipe-separated text format
  {table_headers}      # Styled table headers only

MULTI-VALUE FORMATTING:
  Single:   {skills} → "Python"
  Pair:     {skills} → "Python and Java" 
  Multiple: {skills} → "Python, Java, and JavaScript"
  Many:     {skills} → "Python, Java, JavaScript, and 12 more"

TABLE GENERATION PROCESS:
  1. table-columns.txt specifies which fields to include
  2. Matched CSV rows provide the data
  3. HTML table generated with proper escaping
  4. Multiple styling options available
  5. Field validation ensures all columns exist

RECIPIENT SOURCES & MERGING:
---------------------------

SINGLE MODE (requires at least ONE source):
  - to.txt: Direct email list (semicolon-separated)
  - filter.txt + inventory.csv: Filtered recipients  
  - additional_to.txt: Additional recipients (merged with primary source)
  - cc.txt: CC recipients (added to all emails)
  - bcc.txt: BCC recipients (added to all emails)

MULTI MODE (required sources):
  - filter.txt: Multiple filter conditions (one email per line)
  - inventory.csv: Source database for filtering
  - additional_to.txt: Added to each filtered recipient list
  - cc.txt, bcc.txt: Added to each individual email

RECIPIENT PROCESSING LOGIC:
  1. Primary recipients determined (to.txt OR filter results)
  2. additional_to.txt merged with primary recipients
  3. Automatic deduplication (case-insensitive)
  4. CC/BCC added to each email batch
  5. Final recipient lists saved for audit

ATTACHMENT & IMAGE SYSTEMS:
---------------------------

ATTACHMENT HANDLING:
  - Any file type supported
  - Total size limit: 15MB per campaign (configurable)
  - Automatic MIME type detection
  - Safe filename sanitization
  - Pre-send size validation with detailed reporting

IMAGE EMBEDDING:
  - Automatic HTML img tag processing
  - Inline image embedding using cid: references
  - Supported formats: JPEG, PNG, GIF, WebP, etc.
  - External URL preservation with warnings
  - Base64 encoding for email compatibility

EMBEDDING PROCESS:
  1. Images placed in images/ folder
  2. HTML references: <img src="logo.png" alt="Logo">
  3. System creates cid: references automatically
  4. Images embedded in multipart/related structure
  5. Fallback handling for missing images

GLOBAL SIGNATURE MANAGEMENT:
---------------------------

SIGNATURE FEATURES:
  - Global signature file: /notifybot/signature.html
  - Automatically appended to all email bodies
  - HTML format with full styling support
  - Optional - system works without signature
  - Combined seamlessly with email body content

SIGNATURE PROCESSING:
  1. Check for /notifybot/signature.html
  2. Load and validate HTML content
  3. Combine with email body using separator
  4. Apply to all emails in campaign
  5. Log signature usage for audit

BATCH PROCESSING & DELIVERY:
----------------------------

BATCH CONFIGURATION:
  - Default batch size: 500 recipients per batch
  - Configurable delay: 5.0 seconds between batches
  - Separate batching for single and multi modes
  - CC/BCC included in each batch

BATCH BENEFITS:
  - Reduces mail server load
  - Improves delivery reliability
  - Prevents rate limiting
  - Enables progress tracking
  - Allows partial recovery from failures

MULTI-MODE BATCHING:
  - Each filter condition processed separately  
  - Batching applied within each filter's recipients
  - CC/BCC recipients duplicated per filter (by design)
  - Delays between filters and between batches

DRY-RUN TESTING SYSTEM:
----------------------

DRY-RUN FEATURES:
  - Sends DRAFT emails to approvers only (from approver.txt)
  - Subject automatically prefixed with "DRAFT -"
  - Detailed recipient count information embedded
  - Original recipient data preserved and saved
  - All attachments and formatting preserved
  - Filter information included for multi-mode

DRY-RUN WORKFLOW:
  1. Run with --dry-run flag
  2. Original recipients calculated and saved
  3. Approvers receive test email with metadata
  4. Review content, formatting, attachments, recipient counts
  5. Run without --dry-run for live campaign

DRY-RUN RECIPIENT HANDLING:
  - Original recipients saved to files for reference
  - Approver emails replace actual recipients for sending
  - Multi-mode: Each filter email sent to all approvers
  - Original counts displayed in draft email content

COMPREHENSIVE LOGGING SYSTEM:
----------------------------

LOG FORMAT: Structured CSV with emoji indicators
LOG LOCATION: /notifybot/logs/notifybot.log
LOG LEVELS: info, warning, error, success, processing, backup, file, etc.

CSV LOG STRUCTURE:
  timestamp_ms, username, emoji_message
  
EMOJI INDICATORS:
  ℹ️  Info messages
  ⚠️  Warnings  
  ❌ Errors
  ✅ Success
  ⏳ Processing
  💾 Backup operations
  📂 File operations
  ✋ Confirmations
  📝 Draft operations
  🔧 Mode information
  ✍️  Signature operations

LOGGED OPERATIONS:
  - Campaign initialization and validation
  - Recipient loading and processing
  - Filter application and matches
  - Template substitution results
  - Batch processing progress
  - Email delivery status
  - Error conditions with stack traces
  - File operations and backups

VALIDATION & ERROR PREVENTION:
-----------------------------

COMPREHENSIVE PRE-CHECKS:
  ✓ Required file existence validation
  ✓ Email address syntax validation (RFC-compliant)
  ✓ Priority-based field name validation
  ✓ Filter syntax validation with field checking
  ✓ Attachment size limit enforcement (15MB)
  ✓ Image file accessibility verification
  ✓ Template placeholder validation
  ✓ Recipient source verification
  ✓ Dynamic table configuration validation
  ✓ Inventory file format validation

VALIDATION ERROR HANDLING:
  - Early validation prevents runtime failures
  - Detailed error messages with file references
  - Field availability reporting per inventory source
  - Filter syntax help with examples
  - Actionable guidance for common issues
  - Graceful handling of missing optional files

FIELD VALIDATION PRIORITIES:
  - Filter validation uses prioritized inventory selection
  - Field validation respects local vs global inventory
  - Table column validation against chosen inventory
  - Clear reporting of which inventory source is used

TEST MODE SUPPORT:
-----------------

TEST MODE FEATURES:
  --test: Use test-inventory.csv instead of inventory.csv
  --test-inventory PATH: Use custom test inventory file
  
TEST MODE BEHAVIOR:
  - All validation uses test inventory instead of production
  - Field validation respects test inventory selection
  - Filter conditions validated against test data
  - Template substitution uses test inventory data
  - Logging clearly indicates test mode operation

CUSTOM TEST INVENTORY:
  - Supports any CSV file path with --test-inventory
  - Full validation of custom file format and accessibility
  - UTF-8 encoding requirement enforced
  - Non-empty content validation
  - Integration with priority-based field validation

RECIPIENT BACKUP & AUDIT:
-------------------------

BACKUP FEATURES:
  - Automatic recipient list backup before sending
  - Multi-mode individual filter recipient files
  - Consolidated unique recipient lists
  - CC/BCC recipient preservation
  - Field values saved as JSON for multi-mode
  - Comprehensive summary reports

BACKUP STRUCTURE (recipients/ folder):
  - filter_001_<condition>_recipients.txt
  - filter_001_<condition>_fields.json
  - cc_recipients.txt, bcc_recipients.txt
  - all_unique_recipients.txt
  - multi_mode_summary.txt
  - all_field_values.json

AUDIT CAPABILITIES:
  - Complete recipient tracking
  - Field substitution value recording
  - Filter match statistics
  - Batch processing results
  - Delivery success/failure tracking
  - Time-stamped operation logs

COMMAND LINE INTERFACE:
----------------------

REQUIRED ARGUMENTS:
  --base-folder FOLDER_NAME    Campaign folder in /notifybot/basefolder/

OPTIONAL ARGUMENTS:
  --mode {single,multi}        Override mode.txt file setting
  --dry-run                    Send drafts to approvers only (SAFE MODE)
  --force                      Skip confirmation prompts
  --batch-size N               Recipients per batch (default: 500)
  --delay SECONDS              Delay between batches (default: 5.0)
  --test                       Use test-inventory.csv instead of inventory.csv
  --test-inventory PATH        Custom test inventory file path

MODE DETERMINATION PRIORITY:
  1. CLI --mode argument (highest priority)
  2. mode.txt file in campaign folder
  3. Default to 'single' mode

USAGE EXAMPLES:
  # Dry-run test with default test inventory
  ./notifybot.py --base-folder newsletter --dry-run --test
  
  # Live single-mode with custom test data
  ./notifybot.py --base-folder announcement --mode single --test-inventory /path/to/test.csv --test
  
  # Multi-mode with custom batching, no confirmation
  ./notifybot.py --base-folder personalized --mode multi --batch-size 100 --delay 10 --force
  
  # Production run with dry-run first
  ./notifybot.py --base-folder campaign --dry-run    # Test first
  ./notifybot.py --base-folder campaign              # Live run

SECURITY & SAFETY FEATURES:
---------------------------

EMAIL SECURITY:
  - RFC-compliant email address validation
  - Sendmail injection prevention
  - Proper MIME header encoding
  - Safe filename sanitization for attachments

FILE SYSTEM SECURITY:
  - Enforced base folder restrictions (/notifybot/basefolder/)
  - Path traversal attack prevention
  - UTF-8 encoding enforcement
  - File size limit enforcement

DATA PROTECTION:
  - No external network access required
  - Local file system operations only
  - Comprehensive audit logging
  - Recipient data encryption in logs (CSV escaping)
  - Safe handling of special characters in email content

SENDMAIL INTEGRATION:
  - Multiple sendmail path detection
  - Proper recipient envelope handling
  - CC/BCC header vs envelope distinction
  - Timeout protection (60 seconds)
  - Error code interpretation

PERFORMANCE & SCALABILITY:
--------------------------

EFFICIENT PROCESSING:
  - Streaming CSV processing for large inventories
  - Memory-efficient batch processing
  - Optimized regex compilation and caching
  - Minimal redundant file I/O operations
  - Progress reporting for long-running operations

SCALABILITY FEATURES:
  - Handles thousands of recipients efficiently
  - Configurable memory usage via batch sizing
  - Resource usage monitoring and reporting
  - Graceful handling of large attachment sets
  - Optimized deduplication algorithms

MEMORY MANAGEMENT:
  - Row-by-row CSV processing
  - Batch-based recipient processing  
  - Efficient image encoding
  - Proper file handle cleanup
  - Memory-conscious template substitution

ERROR HANDLING & RECOVERY:
--------------------------

GRACEFUL ERROR HANDLING:
  - Continue processing on non-critical errors
  - Detailed error context and suggestions
  - Partial success tracking and reporting
  - Recovery guidance for common issues
  - Stack trace logging for debugging

COMMON ERROR SCENARIOS:
  - Missing required files → File checklist provided
  - Invalid email addresses → Skip with warning, continue
  - Filter syntax errors → Syntax help with examples
  - Network/sendmail failures → Retry suggestions
  - Attachment size exceeded → Clear size guidance
  - Invalid inventory format → Format requirements shown

RECOVERY FEATURES:
  - Batch processing allows partial recovery
  - Recipient backup enables re-runs
  - Detailed logs support troubleshooting
  - Test mode prevents production issues
  - Force mode bypasses prompts for automation

INTEGRATION & AUTOMATION:
-------------------------

AUTOMATION SUPPORT:
  - Command-line interface for scripting
  - Exit codes for automation logic
  - Force mode for unattended operation
  - Structured logging for monitoring integration
  - CSV-based configuration for external tools

EXTERNAL INTEGRATION:
  - Standard sendmail compatibility
  - RFC-compliant email message format
  - CSV inventory format widely supported
  - File-based configuration (no database required)
  - Standard Unix exit codes

MONITORING INTEGRATION:
  - Structured CSV log format
  - Clear success/failure indicators
  - Performance metrics logging
  - Recipient count tracking
  - Detailed error classification

ADVANCED FEATURES:
-----------------

TEMPLATE SYSTEM:
  - HTML template support with CSS
  - Field substitution with smart formatting
  - Dynamic table generation with styling options
  - Multi-value field handling
  - Template validation and error reporting

RECIPIENT MANAGEMENT:
  - Case-insensitive deduplication
  - Multiple source merging
  - Priority-based source selection
  - Automatic backup and audit trail
  - Comprehensive recipient reporting

FILTER SYSTEM:
  - PromQL-style syntax
  - Multiple operator support
  - Regular expression validation
  - Field existence checking
  - Performance-optimized matching

MULTI-MODE SOPHISTICATION:
  - Per-filter personalization
  - Individual field value extraction
  - Dynamic table generation per email
  - Comprehensive audit trail per filter
  - Batch processing within filters

MAINTENANCE & OPERATIONS:
------------------------

ROUTINE OPERATIONS:
  - Log rotation (handled externally)
  - Recipient list maintenance
  - Inventory file updates
  - Signature management
  - Attachment cleanup

DEBUGGING CAPABILITIES:
  - Verbose logging with context
  - Template substitution tracking
  - Filter match statistics
  - Batch processing diagnostics
  - Field validation detailed reporting

OPERATIONAL MONITORING:
  - Campaign success/failure tracking
  - Recipient delivery statistics
  - Performance metrics
  - Resource usage monitoring
  - Error pattern analysis

SYSTEM REQUIREMENTS:
-------------------

SOFTWARE REQUIREMENTS:
  - Python 3.7+ (tested with 3.8+)
  - sendmail
  - email-validator Python package
  - Standard Python libraries (pathlib, csv, re, subprocess, etc.)

SYSTEM REQUIREMENTS:
  - Unix-like operating system (Linux, macOS)
  - File system with UTF-8 support
  - Network access for email delivery
  - Sufficient disk space for logs and backups

RESOURCE RECOMMENDATIONS:
  - RAM: 512MB minimum, 2GB+ for large campaigns
  - Disk: 100MB per campaign (logs, backups, attachments)
  - CPU: Minimal requirements, I/O bound operation

EXIT CODES:
-----------
  0:   Success - campaign completed successfully
  1:   Error - validation failure, missing files, or execution error
  130: User interruption (Ctrl+C)

AUTHOR: NotifyBot Development Team
VERSION: 3.2.0
UPDATED: AUG 2025

CHANGELOG:
  v3.2.0: Priority-based field validation system
  v3.1.0: Test mode support with custom inventories
  v3.0.0: Multi-mode support with dynamic tables
  v2.0.0: Single-mode with batch processing
  v1.0.0: Initial release
"""
import base64
import mimetypes
from email.mime.image import MIMEImage
from typing import List, Tuple, Dict, Set  
import re  
import argparse
import csv
import logging
import shutil
import sys
import time
import traceback
import os
import json
import fnmatch
import io
from datetime import datetime
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
import subprocess
from email_validator import validate_email, EmailNotValidError

# Path configurations
NOTIFYBOT_ROOT = Path("/notifybot")  # Root directory
BASEFOLDER_PATH = NOTIFYBOT_ROOT / "basefolder"  # Enforced base folder location
LOG_FILENAME = NOTIFYBOT_ROOT / "logs" / "notifybot.log"  # Log file location



def validate_custom_test_inventory_path(custom_test_path: str) -> Path:
    """
    Validate that the custom test inventory path exists and is accessible.
    Returns the validated Path object.
    FIXED: Remove log_and_print call that happens before logging is set up.
    """
    if not custom_test_path:
        raise ValueError("Custom test inventory path cannot be empty")
    
    test_inventory_path = Path(custom_test_path)
    
    # Check if file exists
    if not test_inventory_path.exists():
        raise ValueError(f"Custom test inventory file not found: {custom_test_path}")
    
    # Check if it's a file (not a directory)
    if not test_inventory_path.is_file():
        raise ValueError(f"Custom test inventory path is not a file: {custom_test_path}")
    
    # Check if it's readable
    if not os.access(test_inventory_path, os.R_OK):
        raise ValueError(f"Custom test inventory file is not readable: {custom_test_path}")
    
    # Basic CSV validation - check if it has headers
    try:
        with open(test_inventory_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            first_row = next(reader, None)
            if not first_row:
                raise ValueError(f"Custom test inventory file is empty: {custom_test_path}")
            if len(first_row) < 1:
                raise ValueError(f"Custom test inventory file has no columns: {custom_test_path}")
    except UnicodeDecodeError:
        raise ValueError(f"Custom test inventory file has invalid encoding (must be UTF-8): {custom_test_path}")
    except Exception as exc:
        raise ValueError(f"Error reading custom test inventory file {custom_test_path}: {exc}")
    
    # FIXED: Removed log_and_print call since logging isn't set up yet
    # The validation success will be logged later when logging is available
    return test_inventory_path



def get_inventory_path(test_mode: bool = False, custom_test_path: str = None) -> Path:
    """Get inventory path based on test mode and optional custom path."""
    if test_mode:
        if custom_test_path:
            # FIXED: Validate custom path before using it
            return validate_custom_test_inventory_path(custom_test_path)
        else:
            # Use default test inventory location
            default_test_path = NOTIFYBOT_ROOT / "inventory" / "test-inventory.csv"
            if not default_test_path.exists():
                raise ValueError(f"Default test inventory file not found: {default_test_path}")
            return default_test_path
    else:
        # FIXED: When NOT in test mode, ignore custom_test_path completely
        default_inventory = NOTIFYBOT_ROOT / "inventory" / "inventory.csv"
        if not default_inventory.exists():
            raise ValueError(f"Default inventory file not found: {default_inventory}")
        return default_inventory



def validate_fields_with_priority(base_folder: Path, mode: str = "single", test_mode: bool = False, custom_test_path: str = None) -> Tuple[bool, List[str]]:
    """
    Validate fields in filter.txt and field.txt against inventory headers.
    """
    errors = []
    inventory_path = get_inventory_path(test_mode, custom_test_path)

    DYNAMIC_FIELDS = {
        'dynamic_table',
        'table_rows',
        'csv_table_rows',
        'simple_table_rows',
        'styled_table_rows',
        'table_headers',
    }

    # Load local inventory headers if present (PRIORITY CHECK)
    local_field_inventory_path = base_folder / "field-inventory.csv"
    has_local_field_inventory = local_field_inventory_path.is_file()
    local_available_fields = set()
    
    if has_local_field_inventory:
        try:
            with open(local_field_inventory_path, mode="r", newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                local_available_fields = set(field.strip() for field in (reader.fieldnames or []))
            if not local_available_fields:
                errors.append("No headers found in local field-inventory.csv")
                return False, errors
            log_and_print("info", f"Local field-inventory.csv fields: {', '.join(sorted(local_available_fields))}")
        except Exception as exc:
            errors.append(f"Error reading local field-inventory.csv headers: {exc}")
            return False, errors

    # Load global inventory headers
    if not inventory_path.exists():
        errors.append(f"Inventory file not found: {inventory_path}")
        return False, errors

    # Determine inventory source name
    if test_mode and custom_test_path:
        inventory_source = f"custom test inventory ({Path(custom_test_path).name})"
    elif test_mode:
        inventory_source = "test-inventory.csv"
    else:
        inventory_source = "inventory.csv"

    try:
        with open(inventory_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            global_available_fields = set(field.strip() for field in (reader.fieldnames or []))
        if not global_available_fields:
            errors.append(f"No headers found in {inventory_source}")
            return False, errors
        
        log_and_print("info", f"Using {inventory_source} fields for validation: {', '.join(sorted(global_available_fields))}")
        
    except Exception as exc:
        errors.append(f"Error reading {inventory_source} headers: {exc}")
        return False, errors

    # FIXED: Determine which inventory to use for filter validation (PRIORITIZE LOCAL)
    if has_local_field_inventory:
        filter_validation_fields = local_available_fields
        filter_validation_source = "local field-inventory.csv"
        log_and_print("info", "Using local field-inventory.csv for filter.txt validation (priority)")
    else:
        filter_validation_fields = global_available_fields
        filter_validation_source = inventory_source
        log_and_print("info", f"Using {inventory_source} for filter.txt validation (no local inventory)")

    # Validate filter.txt fields against the prioritized inventory
    filter_file = base_folder / "filter.txt"
    if filter_file.is_file():
        try:
            filter_content = read_file(filter_file)
            filter_lines = [line.strip() for line in filter_content.splitlines() if line.strip() and not line.startswith('#')]
            for line_num, filter_line in enumerate(filter_lines, 1):
                conditions = [c.strip() for c in filter_line.split(',')]
                for condition in conditions:
                    if not condition:
                        continue
                    field_name = None
                    for op in ['=~', '!~', '!=', '=']:
                        if op in condition:
                            field_name = condition.split(op)[0].strip()
                            break
                    # Use the prioritized fields for validation
                    if field_name and field_name not in filter_validation_fields:
                        errors.append(f"filter.txt line {line_num}: Field '{field_name}' not found in {filter_validation_source}")
        except Exception as exc:
            errors.append(f"Error validating filter.txt: {exc}")

    # Validate field.txt fields (keep existing logic)
    field_file = base_folder / "field.txt"
    if field_file.is_file():
        try:
            field_content = read_file(field_file)
            field_names = [line.strip() for line in field_content.splitlines() if line.strip()]
            normalized_fields = {f.replace('-', '_') for f in field_names}

            # Strict dynamic table pre-check
            if normalized_fields & DYNAMIC_FIELDS:
                table_columns_file = base_folder / "table-columns.txt"
                if not table_columns_file.is_file():
                    errors.append("Dynamic table field requested but table-columns.txt is missing")
                    return False, errors

                cols_content = read_file(table_columns_file).splitlines()
                table_fields = [line.strip() for line in cols_content if line.strip()]
                if not table_fields:
                    errors.append("table-columns.txt exists but is empty")
                    return False, errors

                # Validate table columns against chosen inventory (prioritize local, but use correct test inventory when in test mode)
                if has_local_field_inventory:
                    available_fields = local_available_fields
                    validation_source = "local field-inventory.csv"
                else:
                    available_fields = global_available_fields
                    validation_source = inventory_source
                    
                invalid_cols = [col for col in table_fields if col not in available_fields]
                if invalid_cols:
                    errors.append(f"Fields in table-columns.txt not found in {validation_source}: {', '.join(invalid_cols)}")
                    return False, errors

                log_and_print("info", f"table-columns.txt validation passed with columns: {', '.join(table_fields)}")
        except Exception as exc:
            errors.append(f"Error validating field.txt: {exc}")

    return len(errors) == 0, errors



def check_attachment_size_limit(base_folder: Path, max_size_mb: int = 15) -> None:
    """
    """
    attachment_folder = base_folder / "attachment"
    
    if not attachment_folder.exists():
        # No attachment folder, nothing to check
        return
    
    total_size_bytes = 0
    file_count = 0
    
    try:
        for file_path in attachment_folder.iterdir():
            if file_path.is_file():
                file_size = file_path.stat().st_size
                total_size_bytes += file_size
                file_count += 1
                log_and_print("info", f"Attachment: {file_path.name} ({file_size / (1024*1024):.2f} MB)")
        
        if file_count == 0:
            log_and_print("info", "Attachment folder exists but contains no files")
            return
        
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        log_and_print("info", f"Total attachment size: {total_size_mb:.2f} MB ({file_count} files)")
        
        if total_size_mb > max_size_mb:
            raise MissingRequiredFilesError(
                f"Attachment size limit exceeded: {total_size_mb:.2f} MB > {max_size_mb} MB limit. "
                f"Please reduce the total size of files in the attachment folder."
            )
        else:
            log_and_print("success", f"Attachment size check passed: {total_size_mb:.2f} MB / {max_size_mb} MB limit")
    
    except OSError as exc:
        log_and_print("error", f"Error checking attachment sizes: {exc}")
        raise MissingRequiredFilesError(f"Cannot verify attachment sizes: {exc}")


def check_required_files(base: Path, required: List[str], dry_run: bool = True, mode: str = "single", test_mode: bool = False, custom_test_path: str = None) -> None:
    """Updated check_required_files function to use the new priority-based validation."""
    inventory_path = get_inventory_path(test_mode, custom_test_path)
    
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        raise MissingRequiredFilesError(f"Missing required files: {', '.join(missing)}")
    
    # Multi mode requires filter.txt
    if mode == "multi":
        if not (base / "filter.txt").is_file():
            raise MissingRequiredFilesError("Multi mode requires filter.txt")
        if not inventory_path.is_file():
            inventory_type = "test-inventory.csv" if test_mode else "inventory.csv"
            raise MissingRequiredFilesError(f"Multi mode requires {inventory_type} at {inventory_path}")
    
    # Single mode requires at least one recipient source (ALWAYS - dry-run or live)
    if mode == "single":
        has_to = (base / "to.txt").is_file()
        has_filters = (base / "filter.txt").is_file() and inventory_path.is_file()
        has_additional = (base / "additional_to.txt").is_file()
        has_cc = (base / "cc.txt").is_file()
        has_bcc = (base / "bcc.txt").is_file()
        
        if not (has_to or has_filters or has_additional or has_cc or has_bcc):
            raise MissingRequiredFilesError(
                "Single mode requires at least one recipient source: 'to.txt', 'filter.txt + inventory.csv', 'additional_to.txt', 'cc.txt', or 'bcc.txt'."
            )
        
        # Log which recipient source(s) were found
        sources_found = []
        if has_to:
            sources_found.append("to.txt")
        if has_filters:
            sources_found.append("filter.txt + inventory.csv")
        if has_additional:
            sources_found.append("additional_to.txt")
        if has_cc:
            sources_found.append("cc.txt")
        if has_bcc:
            sources_found.append("bcc.txt")
        
        log_and_print("info", f"Single mode recipient sources found: {', '.join(sources_found)}")
    
    # Enhanced field validation with priority-based checking
    needs_inventory = (
        mode == "multi" or 
        (mode == "single" and not (base / "to.txt").is_file() and (base / "filter.txt").is_file())
    )
    
    if needs_inventory:
        log_and_print("info", "Validating field names with priority-based inventory checking...")
        is_valid, validation_errors = validate_fields_with_priority(base, mode, test_mode)
        
        if not is_valid:
            log_and_print("error", "Field validation failed:")
            for error in validation_errors:
                log_and_print("error", f"  {error}")
            raise MissingRequiredFilesError(
                f"Field validation failed. {len(validation_errors)} error(s) found. "
                "Please check that all field names exist in the appropriate inventory files."
            )
        else:
            log_and_print("success", "Field validation passed - all field names are valid")
    
    # NEW: Check attachment size limit
    check_attachment_size_limit(base)




class MissingRequiredFilesError(Exception):
    """Exception raised when required input files are missing."""

def validate_base_folder(base_folder: str) -> Path:
    """Ensure that the base folder is a valid relative path inside /notifybot/basefolder"""
    base_folder_path = BASEFOLDER_PATH / base_folder
    
    # Ensure the base folder is inside /notifybot/basefolder
    if not base_folder_path.is_dir():
        raise ValueError(f"Invalid base folder: {base_folder}. It must be a directory inside '/notifybot/basefolder'.")

    # Return the validated path
    return base_folder_path

def csv_log_entry(message: str) -> str:
    """Generate log entry in CSV format with proper escaping."""
    timestamp_epoch = time.time_ns() // 1_000_000  # Nanoseconds to milliseconds
    try:
        username = os.getlogin()  # Get the username of the executor
    except OSError:
        # Fallback for environments where getlogin() fails
        username = os.getenv('USER', os.getenv('USERNAME', 'unknown'))
    
    # Use csv.writer to properly escape the message field
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([timestamp_epoch, username, message])
    csv_line = output.getvalue().strip()  # Remove trailing newline
    output.close()
    
    return csv_line

def setup_logging() -> None:
    """Configure logging to INFO+ level in LOG_FILENAME with structured CSV format."""
    # Ensure log directory exists
    LOG_FILENAME.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        filename=LOG_FILENAME,
        level=logging.INFO,
        format='%(message)s',
        filemode='a'
    )
    
    def log_and_print(level: str, message: str) -> None:
        """Log and color-print a message at INFO/WARNING/ERROR levels in CSV format."""
        # Emoji mappings for log levels
        emoji_mapping = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
            "processing": "⏳",
            "backup": "💾",
            "file": "📂",
            "confirmation": "✋",
            "draft": "📝",
            "mode": "🔧",
            "signature": "✍️"
        }

        # Get emoji for level
        emoji = emoji_mapping.get(level.lower(), "")
        csv_log = csv_log_entry(f"{emoji} {message}")
        log_func = getattr(logging, level.lower(), logging.info)
        log_func(csv_log)
        print(f"{csv_log}")  # Print to the console as well

    globals()['log_and_print'] = log_and_print

def determine_mode(base_folder: Path, cli_mode: str = None) -> str:
    """
    Determine operating mode with priority: CLI > mode.txt > default (single)
    """
    # Priority 1: CLI override
    if cli_mode and cli_mode.lower() in ['single', 'multi']:
        mode = cli_mode.lower()
        log_and_print("mode", f"Mode determined by CLI argument: {mode}")
        return mode
    
    # Priority 2: mode.txt file
    mode_file = base_folder / "mode.txt"
    if mode_file.is_file():
        try:
            mode_content = mode_file.read_text(encoding="utf-8").strip().lower()
            if mode_content in ['single', 'multi']:
                log_and_print("mode", f"Mode determined by mode.txt: {mode_content}")
                return mode_content
            else:
                log_and_print("warning", f"Invalid mode in mode.txt: {mode_content}. Using default 'single'")
        except Exception as exc:
            log_and_print("warning", f"Error reading mode.txt: {exc}. Using default 'single'")
    
    # Priority 3: Default
    log_and_print("mode", "Mode defaulted to: single")
    return "single"

def read_signature() -> str:
    """
    """
    # Changed to use global signature location
    signature_file = NOTIFYBOT_ROOT / "signature.html"  # /notifybot/signature.html
    
    if not signature_file.is_file():
        log_and_print("info", "No signature.html found at /notifybot/signature.html, emails will be sent without signature")
        return ""
    
    try:
        signature_content = signature_file.read_text(encoding="utf-8").strip()
        if signature_content:
            log_and_print("signature", f"Loaded signature from /notifybot/signature.html ({len(signature_content)} characters)")
            return signature_content
        else:
            log_and_print("warning", "/notifybot/signature.html is empty")
            return ""
    except Exception as exc:
        log_and_print("error", f"Failed to read /notifybot/signature.html: {exc}")
        return ""

def combine_body_and_signature(body_html: str, signature_html: str) -> str:
    """
    """
    if not signature_html:
        return body_html
    
    # Add signature separator and signature
    signature_separator = "\n<br><br>\n"  # Add some spacing before signature
    combined_html = body_html + signature_separator + signature_html
    
    log_and_print("signature", "Combined body and signature successfully")
    return combined_html

def find_sendmail_path() -> str:
    """Find sendmail executable path."""
    common_paths = [
        '/usr/sbin/sendmail',
        '/usr/bin/sendmail',
        '/sbin/sendmail',
        '/usr/lib/sendmail'
    ]
    
    for path in common_paths:
        if Path(path).exists():
            return path
    
    # Try to find in PATH
    try:
        result = subprocess.run(['which', 'sendmail'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    log_and_print("warning", "Sendmail not found in common locations")
    return '/usr/sbin/sendmail'  # Default fallback

def is_valid_email(email: str) -> bool:
    """Check email syntax using email_validator with sendmail compatibility."""
    try:
        validate_email(email.strip(), check_deliverability=False)
        
        # Additional checks for sendmail compatibility
        email = email.strip()
        if len(email) > 320:  # RFC 5321 limit
            log_and_print("warning", f"Email too long (>320 chars): {email}")
            return False
        
        # Check for characters that might cause issues with sendmail
        problematic_chars = ['|', '`', '$', '\\']
        if any(char in email for char in problematic_chars):
            log_and_print("warning", f"Email contains potentially problematic characters: {email}")
            return False
        
        return True
    except EmailNotValidError as exc:
        log_and_print("error", f"Invalid email format: {email}. Error: {exc}")
        return False      
        
        
        

def read_file(path: Path) -> str:
    """Read text file content and strip, or log an error."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        log_and_print("error", f"Failed to read {path}: {exc}")
        return ""

def extract_emails(raw: str, delimiters: str = ";") -> List[str]:
    """Split and trim emails from a raw string by delimiters."""
    if not raw:
        return []
    return [e.strip() for e in re.split(f"[{re.escape(delimiters)}]", raw) if e.strip()]

def read_recipients(path: Path, delimiters: str = ";") -> List[str]:
    """Read and validate emails from a file (semicolon-separated)."""
    valid = []
    if not path.is_file():
        log_and_print("warning", f"{path.name} missing, skipping.")
        return valid
    
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            for email in extract_emails(line.strip(), delimiters):
                if is_valid_email(email):
                    valid.append(email)
                else:
                    log_and_print("warning", f"Invalid email skipped: {email}")
    except Exception as exc:
        log_and_print("error", f"Error processing recipients in {path}: {exc}")
    return valid

def deduplicate_emails(emails: List[str]) -> List[str]:
    """Deduplicate email addresses (case-insensitive) while preserving order."""
    seen = set()
    unique_emails = []
    for email in emails:
        email_lower = email.lower()
        if email_lower not in seen:
            seen.add(email_lower)
            unique_emails.append(email)
    return unique_emails

def write_recipients_to_file(path: Path, recipients: List[str]) -> None:
    """Write recipients list to a file, one per line, with deduplication."""
    try:
        # Deduplicate recipients
        unique_recipients = deduplicate_emails(recipients)
        
        with path.open('w', encoding='utf-8') as f:
            for email in unique_recipients:
                f.write(f"{email}\n")
        
        if len(recipients) != len(unique_recipients):
            duplicates_removed = len(recipients) - len(unique_recipients)
            log_and_print("info", f"Removed {duplicates_removed} duplicate email(s)")
        
        log_and_print("file", f"Written {len(unique_recipients)} unique recipients to {path.name}")
    except Exception as exc:
        log_and_print("error", f"Error writing recipients to {path}: {exc}")

def merge_recipients(base_recipients: List[str], additional_recipients: List[str]) -> List[str]:
    """Merge two lists of recipients, removing duplicates while preserving order."""
    # Combine all recipients and deduplicate
    all_recipients = base_recipients + additional_recipients
    return deduplicate_emails(all_recipients)


def sanitize_filename(filename: str) -> str:
    """Sanitize the filename to prevent issues with special characters."""
    return re.sub(r"[^\w\s.-]", "", filename)

def add_attachments(msg: MIMEMultipart, attachment_folder: Path) -> None:
    """Add all files from attachment folder to the email message."""
    if not attachment_folder or not attachment_folder.exists():
        return
        
    try:
        for file_path in attachment_folder.iterdir():
            if file_path.is_file():
                # Get MIME type
                ctype, encoding = mimetypes.guess_type(str(file_path))
                if ctype is None or encoding is not None:
                    ctype = 'application/octet-stream'
                
                maintype, subtype = ctype.split('/', 1)
                
                with open(file_path, 'rb') as fp:
                    attachment = MIMEBase(maintype, subtype)
                    attachment.set_payload(fp.read())
                    encoders.encode_base64(attachment)
                    attachment.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{sanitize_filename(file_path.name)}"'
                    )
                    msg.attach(attachment)
                
                log_and_print("info", f"Attached file: {file_path.name}")
                
    except Exception as exc:
        log_and_print("error", f"Error adding attachments: {exc}")

def create_email_message(recipients: List[str], subject: str, body_html: str, 
                        from_address: str, attachment_folder: Path = None,
                        base_folder: Path = None, cc_recipients: List[str] = None,
                        bcc_recipients: List[str] = None) -> MIMEMultipart:
    """Create a properly formatted email message with embedded images and attachments."""
    cc_recipients = cc_recipients or []
    bcc_recipients = bcc_recipients or []
    
    # Embed images if base_folder is provided
    embedded_images = []
    if base_folder:
        body_html, embedded_images = embed_images_in_html(body_html, base_folder)
    
    # Create multipart message
    if embedded_images:
        msg = MIMEMultipart('related')  # Use 'related' when we have embedded images
    else:
        msg = MIMEMultipart('mixed')    # Use 'mixed' for attachments only
    
    msg['From'] = from_address
    msg['To'] = ', '.join(recipients)
    if cc_recipients:
        msg['Cc'] = ', '.join(cc_recipients)
        log_and_print("info", f"CC: {len(cc_recipients)} recipient(s)")
       
    # Note: BCC headers are intentionally NOT added to prevent recipients from seeing BCC list
    if bcc_recipients:
        log_and_print("info", f"BCC: {len(bcc_recipients)} recipient(s)")
       
    msg['Subject'] = subject
    
    # Create multipart alternative for HTML content if we have embedded images
    if embedded_images:
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)
        
        # Add HTML body to alternative
        html_part = MIMEText(body_html, 'html', 'utf-8')
        msg_alternative.attach(html_part)
        
        # Add embedded images to main message
        for img in embedded_images:
            msg.attach(img)
    else:
        # No embedded images, add HTML directly
        html_part = MIMEText(body_html, 'html', 'utf-8')
        msg.attach(html_part)
    
    # Add attachments if folder exists
    if attachment_folder:
        add_attachments(msg, attachment_folder)
    
    return msg


def matches_filter_conditions(row: Dict, filters: List[str]) -> bool:
    """
    """
    if not filters:
        return True  # No filters means include all
    
    def matches_exact(text: str, pattern: str) -> bool:
        """Exact string match (case-insensitive)."""
        return str(text).lower() == pattern.lower()
    
    def matches_not_equal(text: str, pattern: str) -> bool:
        """Not equal match (case-insensitive)."""
        return str(text).lower() != pattern.lower()
    
    def matches_regex(text: str, pattern: str) -> bool:
        """Regex match (case-insensitive)."""
        try:
            return bool(re.search(pattern, str(text), re.IGNORECASE))
        except re.error as e:
            print(f"Invalid regex pattern '{pattern}': {e}")
            return False
    
    def matches_regex_not(text: str, pattern: str) -> bool:
        """Regex not match (case-insensitive)."""
        try:
            return not bool(re.search(pattern, str(text), re.IGNORECASE))
        except re.error as e:
            print(f"Invalid regex pattern '{pattern}': {e}")
            return False
    
    def matches_wildcard(text: str, pattern: str) -> bool:
        """Wildcard match using fnmatch (case-insensitive)."""
        return fnmatch.fnmatch(str(text).lower(), pattern.lower())
    
    def parse_condition(condition: str) -> tuple:
        """
        """
        condition = condition.strip()
        
        # Check for regex operators first (longer patterns)
        if '=~' in condition:
            key, value = condition.split('=~', 1)
            return key.strip(), '=~', value.strip().strip('"\'')
        elif '!~' in condition:
            key, value = condition.split('!~', 1)
            return key.strip(), '!~', value.strip().strip('"\'')
        elif '!=' in condition:
            key, value = condition.split('!=', 1)
            return key.strip(), '!=', value.strip().strip('"\'')
        elif '=' in condition:
            key, value = condition.split('=', 1)
            value = value.strip().strip('"\'')
            # Check if value contains wildcards
            if '*' in value or '?' in value or '[' in value:
                return key.strip(), '*', value
            else:
                return key.strip(), '=', value
        else:
            # Simple wildcard search in all values (backward compatibility)
            return None, '*', condition
    
    def evaluate_condition(key: str, operator: str, value: str, row: Dict) -> bool:
        """Evaluate a single condition against a row."""
        if key is None:
            # Simple wildcard search in all values (backward compatibility)
            for row_value in row.values():
                if matches_wildcard(row_value, value):
                    return True
            return False
        
        if key not in row:
            return False  # Key doesn't exist in row
        
        row_value = row[key]
        
        if operator == '=':
            return matches_exact(row_value, value)
        elif operator == '!=':
            return matches_not_equal(row_value, value)
        elif operator == '=~':
            return matches_regex(row_value, value)
        elif operator == '!~':
            return matches_regex_not(row_value, value)
        elif operator == '*':
            return matches_wildcard(row_value, value)
        else:
            return False
    
    # Process each line as a separate OR condition
    for filter_line in filters:
        filter_line = filter_line.strip()
        
        # Skip empty lines and comments
        if not filter_line or filter_line.startswith('#'):
            continue
        
        # Split the line into individual AND conditions
        and_conditions = [condition.strip() for condition in filter_line.split(',')]
        
        # Check if ALL conditions in this line match (AND logic)
        line_matches = True
        for condition in and_conditions:
            if not condition:
                continue
            
            try:
                key, operator, value = parse_condition(condition)
                if not evaluate_condition(key, operator, value, row):
                    line_matches = False
                    break  # This AND condition failed
            except Exception as e:
                print(f"Error parsing condition '{condition}': {e}")
                line_matches = False
                break
        
        # If this line matched completely (all AND conditions), return True (OR logic)
        if line_matches:
            return True
    
    # None of the OR conditions matched
    return False

def validate_filter_syntax(filters: List[str], available_fields: Set[str] = None) -> Tuple[bool, List[str]]:
    """
    """
    errors = []
    
    for i, filter_line in enumerate(filters, 1):
        filter_line = filter_line.strip()
        
        # Skip comments and empty lines
        if not filter_line or filter_line.startswith('#'):
            continue
        
        # Split into AND conditions
        and_conditions = [condition.strip() for condition in filter_line.split(',')]
        
        for condition in and_conditions:
            if not condition:
                continue
            
            # Check for valid operators
            valid_operators = ['=~', '!~', '!=', '=']
            has_valid_operator = False
            field_name = None
            
            for op in valid_operators:
                if op in condition:
                    has_valid_operator = True
                    parts = condition.split(op, 1)
                    if len(parts) != 2:
                        errors.append(f"Line {i}: Invalid condition syntax '{condition}'")
                        break
                    
                    field_name, value = parts[0].strip(), parts[1].strip()
                    
                    if not field_name:
                        errors.append(f"Line {i}: Empty field name in '{condition}'")
                    
                    if not value:
                        errors.append(f"Line {i}: Empty value in '{condition}'")
                    
                    # NEW: Check if field exists in available fields
                    if available_fields and field_name and field_name not in available_fields:
                        errors.append(f"Line {i}: Field '{field_name}' not found in inventory.csv headers")
                    
                    # Validate regex patterns for regex operators
                    if op in ['=~', '!~']:
                        value_clean = value.strip('"\'')
                        try:
                            re.compile(value_clean)
                        except re.error as e:
                            errors.append(f"Line {i}: Invalid regex pattern '{value_clean}': {e}")
                    
                    break
            
            if not has_valid_operator:
                # Check if it's a simple wildcard pattern (backward compatibility)
                if not ('*' in condition or '?' in condition or '[' in condition):
                    errors.append(f"Line {i}: No valid operator found in '{condition}'. Use =, !=, =~, !~, or wildcards (*,?,[])")
    
    return len(errors) == 0, errors

   

def apply_filter_logic(filters: List[str], inventory_path: Path) -> List[str]:
    """
    Apply filter logic - this function signature doesn't change since it accepts inventory_path as parameter.
    The calling functions will pass the correct path based on test_mode.
    """
    filtered_recipients = []
    
    if not inventory_path.exists():
        log_and_print("error", f"Inventory file not found: {inventory_path}")
        return filtered_recipients
    
    # Read available fields from inventory
    try:
        with open(inventory_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            available_fields = set(reader.fieldnames or [])
    except Exception as exc:
        log_and_print("error", f"Error reading inventory headers: {exc}")
        return filtered_recipients
    
    # Validate filter syntax WITH field name checking
    is_valid, errors = validate_filter_syntax(filters, available_fields)
    if not is_valid:
        log_and_print("error", "Filter syntax/field validation failed:")
        for error in errors:
            log_and_print("error", f"  {error}")
        print_filter_syntax_help()  # This function needs to be defined
        log_and_print("info", f"Available fields in inventory.csv: {', '.join(sorted(available_fields))}")
        return filtered_recipients
    
    # Count total non-comment filter lines for logging
    active_filters = [f.strip() for f in filters if f.strip() and not f.strip().startswith('#')]
    if not active_filters:
        log_and_print("warning", "No active filter conditions found (only comments/empty lines)")
        return filtered_recipients
    
    log_and_print("info", f"Applying {len(active_filters)} filter condition(s) with PromQL-style syntax")
    
    # Log filter conditions for debugging
    for i, filter_line in enumerate(active_filters, 1):
        log_and_print("info", f"Filter {i}: {filter_line}")
    
    try:
        matched_rows = 0
        total_rows = 0
        
        with open(inventory_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                total_rows += 1
                
                if matches_filter_conditions(row, filters):
                    matched_rows += 1
                    
                    if 'email' in row:
                        # Extract and validate each email from semicolon-separated string
                        email_string = row['email']
                        individual_emails = extract_emails(email_string, ";")
                        
                        for email in individual_emails:
                            if is_valid_email(email):
                                filtered_recipients.append(email)
                            else:
                                log_and_print("warning", f"Invalid email skipped: {email}")
                        
                        if not individual_emails:
                            log_and_print("warning", f"Row has empty email field: {row}")
                    else:
                        log_and_print("warning", f"Row missing email column: {row}")
        
        # Deduplicate filtered recipients
        original_count = len(filtered_recipients)
        filtered_recipients = deduplicate_emails(filtered_recipients)
        
        if original_count != len(filtered_recipients):
            log_and_print("info", f"Removed {original_count - len(filtered_recipients)} duplicate emails from filter results")
        
        # Enhanced logging with statistics
        log_and_print("info", f"Filter processing complete:")
        log_and_print("info", f"  - Total rows in inventory: {total_rows}")
        log_and_print("info", f"  - Rows matching filters: {matched_rows}")
        log_and_print("info", f"  - Unique email recipients: {len(filtered_recipients)}")
        
        if matched_rows > 0:
            match_percentage = (matched_rows / total_rows) * 100
            log_and_print("info", f"  - Match rate: {match_percentage:.1f}%")
        
    except Exception as exc:
        log_and_print("error", f"Error applying filter logic: {exc}")
        log_and_print("error", f"Make sure inventory.csv has proper headers and format")
    
    return filtered_recipients






        
        
        
        
def substitute_placeholders(template: str, field_values: Dict[str, str]) -> str:
    """
    Substitute placeholders in template with field values.
    Fixed version that properly handles empty values.
    """
    result = template
    substitutions_made = 0
    
    for field, value in field_values.items():
        placeholder = f"{{{field}}}"
        
        if placeholder in result:
            # Clean up comma-separated values for better readability
            if value and ',' in value:
                # For comma-separated values, format them nicely
                values = [v.strip() for v in value.split(',') if v.strip()]
                if len(values) == 1:
                    clean_value = values[0]
                elif len(values) == 2:
                    clean_value = f"{values[0]} and {values[1]}"
                elif len(values) <= 5:
                    # For small lists, show all with proper formatting
                    clean_value = f"{', '.join(values[:-1])}, and {values[-1]}"
                else:
                    # For large lists, show first few and add "and X more"
                    remaining = len(values) - 3
                    clean_value = f"{', '.join(values[:3])}, and {remaining} more"
            else:
                # FIXED: Use the value as-is (including empty string or HTML table content)
                clean_value = value
            
            # Perform the substitution
            result = result.replace(placeholder, clean_value)
            substitutions_made += 1
    
    # Log substitution details if any were made
    if substitutions_made > 0:
        log_and_print("info", f"Template substitution: {substitutions_made} placeholder(s) replaced")
    
    return result



def get_recipients_for_single_mode(base_folder: Path, dry_run: bool, test_mode: bool = False, custom_test_path: str = None) -> Tuple[List[str], List[str], List[str], int, int, int]:
    """Get recipients for single mode with test mode support."""
    inventory_path = get_inventory_path(test_mode, custom_test_path)  # UPDATED CALL
    cc_emails = read_recipients(base_folder / "cc.txt")
    bcc_emails = read_recipients(base_folder / "bcc.txt")
    
    if cc_emails:
        log_and_print("info", f"Loaded {len(cc_emails)} CC recipients from cc.txt")
    if bcc_emails:
        log_and_print("info", f"Loaded {len(bcc_emails)} BCC recipients from bcc.txt")
    
    if dry_run:
        # In dry-run mode, we only send to approvers
        approver_emails = read_recipients(base_folder / "approver.txt")
        final_recipients = deduplicate_emails(approver_emails)
        final_cc_recipients = []
        final_bcc_recipients = []
        
        # Count what would be the original recipients for display purposes
        original_recipients = []
        to_file_path = base_folder / "to.txt"
        additional_to_file_path = base_folder / "additional_to.txt"
        filter_file_path = base_folder / "filter.txt"

        if to_file_path.is_file():
            # Show disclaimer about existing to.txt
            print()
            print(f"\033[1m\033[91m{'=' * 80}\033[0m")
            print(f"\033[1m\033[91m                            ⚠️  IMPORTANT DISCLAIMER ⚠️\033[0m")
            print(f"\033[1m\033[91m{'=' * 80}\033[0m")
            print()
            print(f"\033[1m\033[93m⚠️  DISCLAIMER: Existing to.txt found - dry-run will NOT overwrite it\033[0m")
            print(f"\033[1m\033[94m💡 To see fresh filter results, delete to.txt and run dry-run again\033[0m")
            print(f"\033[1mCurrent to.txt contains {len(read_recipients(to_file_path))} recipients (preserving existing list)\033[0m")
            print()
            print(f"\033[1m\033[91m{'=' * 80}\033[0m")
            print()
            
            log_and_print("info", "⚠️  DISCLAIMER: Existing to.txt found - dry-run will NOT overwrite it")
            log_and_print("info", "💡 To see fresh filter results, delete to.txt and run dry-run again")
            log_and_print("info", f"Current to.txt contains {len(read_recipients(to_file_path))} recipients (preserving existing list)")
            
        # Calculate original TO recipients with proper logging
        if to_file_path.is_file():
            original_recipients = read_recipients(to_file_path)
            log_and_print("info", f"DRY-RUN: Loaded {len(original_recipients)} recipients from existing to.txt")
            
            if additional_to_file_path.is_file():
                additional_recipients = read_recipients(additional_to_file_path)
                if additional_recipients:
                    original_count = len(original_recipients)
                    original_recipients = merge_recipients(original_recipients, additional_recipients)
                    added_count = len(original_recipients) - original_count
                    log_and_print("info", f"DRY-RUN: Would merge {len(additional_recipients)} additional recipients from additional_to.txt")
                    if added_count > 0:
                        log_and_print("info", f"DRY-RUN: Would add {added_count} new recipients (total would be {len(original_recipients)})")
                    else:
                        log_and_print("info", f"DRY-RUN: No new recipients to add (all {len(additional_recipients)} already exist)")
                        
        elif filter_file_path.is_file() and inventory_path.is_file(): 
            filters = read_file(filter_file_path).splitlines()
            recipients = apply_filter_logic(filters, inventory_path)
            original_recipients = deduplicate_emails(recipients)
            log_and_print("info", f"DRY-RUN: Filter logic would generate {len(original_recipients)} recipients")
                    
            if additional_to_file_path.is_file():
                additional_recipients = read_recipients(additional_to_file_path)
                if additional_recipients:
                    original_count = len(original_recipients)
                    original_recipients = merge_recipients(original_recipients, additional_recipients)
                    added_count = len(original_recipients) - original_count
                    log_and_print("info", f"DRY-RUN: Would merge {len(additional_recipients)} additional recipients from additional_to.txt")
                    if added_count > 0:
                        log_and_print("info", f"DRY-RUN: Would add {added_count} new recipients (total would be {len(original_recipients)})")
                    else:
                        log_and_print("info", f"DRY-RUN: No new recipients to add (all {len(additional_recipients)} already exist)")
                        
            if original_recipients and not to_file_path.is_file():
                write_recipients_to_file(to_file_path, original_recipients)
                log_and_print("info", f"DRY-RUN: Would create to.txt with {len(original_recipients)} merged recipients")
                
        elif additional_to_file_path.is_file():
            original_recipients = read_recipients(additional_to_file_path)
            log_and_print("info", f"DRY-RUN: Would use {len(original_recipients)} recipients from additional_to.txt only")
            if original_recipients and not to_file_path.is_file():
                write_recipients_to_file(to_file_path, original_recipients)
                log_and_print("info", f"DRY-RUN: Would create to.txt from additional_to.txt with {len(original_recipients)} recipients")

        original_recipients_count = len(deduplicate_emails(original_recipients))
        original_cc_count = len(deduplicate_emails(cc_emails))
        original_bcc_count = len(deduplicate_emails(bcc_emails))
        
        total_original = original_recipients_count + original_cc_count + original_bcc_count
        log_and_print("draft", f"DRY-RUN MODE: Will send to {len(final_recipients)} approvers instead of {total_original} actual recipients")
        
    else:
        # Live mode - determine actual recipients with enhanced logging
        final_cc_recipients = deduplicate_emails(cc_emails)
        final_bcc_recipients = deduplicate_emails(bcc_emails)
        original_cc_count = len(final_cc_recipients)
        original_bcc_count = len(final_bcc_recipients)
        recipients = []
        to_file_path = base_folder / "to.txt"
        additional_to_file_path = base_folder / "additional_to.txt"
        filter_file_path = base_folder / "filter.txt"
        
        # Priority 1: Use to.txt if it exists
        if to_file_path.is_file():
            recipients = read_recipients(to_file_path)
            log_and_print("info", f"Loaded {len(recipients)} recipients from to.txt")
            
            # Also check for additional_to.txt and merge if it exists
            if additional_to_file_path.is_file():
                additional_recipients = read_recipients(additional_to_file_path)
                if additional_recipients:
                    original_count = len(recipients)
                    recipients = merge_recipients(recipients, additional_recipients)
                    added_count = len(recipients) - original_count
                    
                    log_and_print("info", f"Found additional_to.txt with {len(additional_recipients)} recipients")
                    if added_count > 0:
                        log_and_print("info", f"Added {added_count} new recipients from additional_to.txt")
                        log_and_print("info", f"Total recipients after merge: {len(recipients)} (was {original_count})")
                    else:
                        log_and_print("info", f"No new recipients added - all {len(additional_recipients)} from additional_to.txt already exist in to.txt")
                        log_and_print("info", f"Total recipients remain: {len(recipients)}")
                else:
                    log_and_print("info", f"Found empty additional_to.txt - no recipients to merge")
        
        # Priority 2: Use filter logic if to.txt doesn't exist
        elif filter_file_path.is_file() and inventory_path.is_file():
            filters = read_file(filter_file_path).splitlines()
            recipients = apply_filter_logic(filters, inventory_path)
            log_and_print("info", f"Filter logic generated {len(recipients)} recipients")
            
            # Check for additional_to.txt and merge with filtered results
            if additional_to_file_path.is_file():
                additional_recipients = read_recipients(additional_to_file_path)
                if additional_recipients:
                    original_count = len(recipients)
                    recipients = merge_recipients(recipients, additional_recipients)
                    added_count = len(recipients) - original_count
                    
                    log_and_print("info", f"Found additional_to.txt with {len(additional_recipients)} recipients")
                    if added_count > 0:
                        log_and_print("info", f"Added {added_count} new recipients from additional_to.txt")
                        log_and_print("info", f"Total recipients after merge: {len(recipients)} (filter: {original_count} + additional: {added_count})")
                    else:
                        log_and_print("info", f"No new recipients added - all {len(additional_recipients)} from additional_to.txt already matched by filters")
                        log_and_print("info", f"Total recipients remain: {len(recipients)}")
                else:
                    log_and_print("info", f"Found empty additional_to.txt - no recipients to merge with filter results")
            
            # Write the merged results to to.txt for future reference
            if recipients:
                write_recipients_to_file(to_file_path, recipients)
                if additional_to_file_path.is_file() and read_recipients(additional_to_file_path):
                    log_and_print("file", f"Created to.txt with {len(recipients)} merged recipients (filter + additional)")
                else:
                    log_and_print("file", f"Created to.txt with {len(recipients)} filter recipients")
        
        # Priority 3: Use only additional_to.txt if nothing else is available
        elif additional_to_file_path.is_file():
            recipients = read_recipients(additional_to_file_path)
            if recipients:
                log_and_print("info", f"No to.txt or filter.txt found - using {len(recipients)} recipients from additional_to.txt only")
                
                # Create to.txt from additional_to.txt
                write_recipients_to_file(to_file_path, recipients)
                log_and_print("file", f"Created to.txt from additional_to.txt with {len(recipients)} recipients")
            else:
                log_and_print("warning", f"Found additional_to.txt but it contains no valid recipients")
        
        else:
            if not (cc_emails or bcc_emails):
                log_and_print("error", "No valid recipient source found (no TO, CC, or BCC recipients)")
                sys.exit(1)
            else:
                log_and_print("info", "No TO recipients found, but CC/BCC recipients available")
                recipients = []
        
        final_recipients = deduplicate_emails(recipients)
        original_recipients_count = len(final_recipients)
    
    return (final_recipients, final_cc_recipients, final_bcc_recipients, 
            original_recipients_count, original_cc_count, original_bcc_count)
   
def extract_field_values_from_matched_rows(filter_line: str, field_names: List[str], inventory_path: Path, base_folder: Path, mode: str = "single") -> Dict[str, str]:
    """
    Extract field values from inventory for the matched rows.
    FIXED: Improved dynamic table generation logic.
    """
    field_values = {field: "" for field in field_names}

    DYNAMIC_FIELDS = {
        'dynamic_table',
        'table_rows',
        'csv_table_rows',
        'simple_table_rows',
        'styled_table_rows',
        'table_headers',
    }

    local_inventory = base_folder / "field-inventory.csv"
    actual_inventory = local_inventory if local_inventory.exists() else inventory_path
    inventory_source = "local field-inventory.csv" if local_inventory.exists() else "global inventory.csv"

    if not actual_inventory.exists():
        log_and_print("error", f"Inventory file not found: {actual_inventory}")
        return field_values

    try:
        with open(actual_inventory, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = [h.strip() for h in (reader.fieldnames or [])]
            matched_rows = []

            # FIXED: Collect all matched rows first
            for row in reader:
                cleaned_row = {k.strip(): v.strip() for k, v in row.items() if k}
                if matches_filter_conditions(cleaned_row, [filter_line]):
                    matched_rows.append(cleaned_row)

        if not matched_rows:
            log_and_print("warning", f"No rows matched filter: {filter_line}")
            return field_values

        log_and_print("info", f"Filter '{filter_line}' matched {len(matched_rows)} rows")

        # Fill non-table fields
        for field in field_names:
            if field in headers and field not in DYNAMIC_FIELDS:
                values = set()
                for row in matched_rows:
                    val = row.get(field, "").strip()
                    if val:
                        values.update([v.strip() for v in val.split(",") if v.strip()])
                field_values[field] = ",".join(sorted(values))

        # FIXED: Dynamic table processing with better debugging
        has_dynamic_table_fields = any(f in DYNAMIC_FIELDS for f in field_names)
        if has_dynamic_table_fields:
            log_and_print("info", f"Dynamic table fields requested: {[f for f in field_names if f in DYNAMIC_FIELDS]}")
            
            table_columns_file = base_folder / "table-columns.txt"
            if not table_columns_file.is_file():
                error_msg = "CRITICAL ERROR: Dynamic table field requested but table-columns.txt is missing"
                log_and_print("error", error_msg)
                raise MissingRequiredFilesError(error_msg)

            cols_content = read_file(table_columns_file).splitlines()
            table_fields = [line.strip() for line in cols_content if line.strip()]
            if not table_fields:
                error_msg = "CRITICAL ERROR: table-columns.txt exists but is empty"
                log_and_print("error", error_msg)
                raise MissingRequiredFilesError(error_msg)

            invalid_table_fields = [col for col in table_fields if col not in headers]
            if invalid_table_fields:
                error_msg = f"CRITICAL ERROR: Fields in table-columns.txt not found in {inventory_source}: {', '.join(invalid_table_fields)}"
                log_and_print("error", error_msg)
                raise MissingRequiredFilesError(error_msg)

            log_and_print("info", f"Using table-columns.txt for dynamic table: {', '.join(table_fields)}")
            log_and_print("info", f"Will generate table with {len(matched_rows)} rows and {len(table_fields)} columns")

            def escape(val):
                return str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            def generate_table_rows(style: str = "default") -> str:
                if not matched_rows:
                    log_and_print("warning", f"No matched rows to generate table content")
                    return ""
                
                rows = ""
                for i, row in enumerate(matched_rows):
                    bg = "#f9f9f9" if style == "striped" and i % 2 == 0 else "#ffffff"
                    tr_style = f' style="background-color: {bg};"' if style == "striped" else ""
                    rows += f"        <tr{tr_style}>\n"
                    for col in table_fields:
                        val = escape(row.get(col, ""))
                        cell_style = ' style="padding: 10px; border: 1px solid #ddd;"' if style != "simple" else ""
                        rows += f"            <td{cell_style}>{val}</td>\n"
                    rows += "        </tr>\n"
                
                log_and_print("info", f"Generated {style} table rows: {len(matched_rows)} rows")
                return rows.strip()

            def generate_headers() -> str:
                headers_html = "\n".join([
                    f'            <th style="padding: 10px; border: 1px solid #ddd; background-color: #f5f5f5;">{col.replace("_", " ").title()}</th>'
                    for col in table_fields
                ])
                log_and_print("info", f"Generated table headers for {len(table_fields)} columns")
                return headers_html

            # FIXED: Generate all requested table variants
            if "table_rows" in field_names:
                field_values["table_rows"] = generate_table_rows()
                log_and_print("info", f"Generated table_rows: {len(field_values['table_rows'])} characters")
                
            if "styled_table_rows" in field_names:
                field_values["styled_table_rows"] = generate_table_rows("striped")
                log_and_print("info", f"Generated styled_table_rows: {len(field_values['styled_table_rows'])} characters")
                
            if "simple_table_rows" in field_names:
                field_values["simple_table_rows"] = generate_table_rows("simple")
                log_and_print("info", f"Generated simple_table_rows: {len(field_values['simple_table_rows'])} characters")
                
            if "csv_table_rows" in field_names:
                csv_content = "\n".join(
                    " | ".join(row.get(col, "") for col in table_fields)
                    for row in matched_rows
                ).strip()
                field_values["csv_table_rows"] = csv_content
                log_and_print("info", f"Generated csv_table_rows: {len(field_values['csv_table_rows'])} characters")
                
            if "table_headers" in field_names:
                field_values["table_headers"] = generate_headers()
                log_and_print("info", f"Generated table_headers: {len(field_values['table_headers'])} characters")
                
            if "dynamic_table" in field_names:
                # FIXED: dynamic_table should use the same content as table_rows
                field_values["dynamic_table"] = generate_table_rows()
                log_and_print("info", f"Generated dynamic_table: {len(field_values['dynamic_table'])} characters")

            # FIXED: Debug output to verify table generation
            for field_name in DYNAMIC_FIELDS:
                if field_name in field_values and field_values[field_name]:
                    preview = field_values[field_name][:100].replace('\n', '\\n')
                    log_and_print("info", f"Field '{field_name}' preview: {preview}...")
                elif field_name in field_names:
                    log_and_print("warning", f"Field '{field_name}' is empty after generation")

            log_and_print("info", f"Dynamic table generation completed successfully")
        else:
            log_and_print("info", "No dynamic table fields requested, skipping table generation")

    except Exception as e:
        log_and_print("error", f"Failed to extract field values: {e}")
        import traceback
        log_and_print("error", f"Traceback: {traceback.format_exc()}")

    return field_values




def get_recipients_for_multi_mode(base_folder: Path, dry_run: bool, test_mode: bool = False, custom_test_path: str = None) -> Tuple[List[Dict], List[str], List[str], int, int, int]:
    """Get recipients for multi mode operation with test mode support."""
    inventory_path = get_inventory_path(test_mode, custom_test_path)  # UPDATED CALL
    
    # Read filter conditions
    filters = read_file(base_folder / "filter.txt").splitlines()
    filters = [f.strip() for f in filters if f.strip() and not f.strip().startswith('#')]
    
    if not filters:
        log_and_print("error", "No valid filter conditions found in filter.txt")
        sys.exit(1)
    
    # Read field names for substitution (optional)
    field_names = []
    field_file = base_folder / "field.txt"
    if field_file.is_file():
        try:
            field_content = read_file(field_file)
            field_names = [line.strip() for line in field_content.splitlines() if line.strip()]
            log_and_print("info", f"Loaded {len(field_names)} field names for substitution: {', '.join(field_names)}")
        except Exception as exc:
            log_and_print("warning", f"Error reading field.txt: {exc}")
    else:
        log_and_print("info", "No field.txt found - no template substitution will be performed")
    
    # Read CC and BCC recipients - STORE ORIGINAL COUNTS IMMEDIATELY
    cc_emails = read_recipients(base_folder / "cc.txt")
    bcc_emails = read_recipients(base_folder / "bcc.txt")
    original_cc_count = len(deduplicate_emails(cc_emails))  # Store original count
    original_bcc_count = len(deduplicate_emails(bcc_emails))  # Store original count
    
    if cc_emails:
        log_and_print("info", f"Loaded {len(cc_emails)} CC recipients from cc.txt (will be added to each email)")
    if bcc_emails:
        log_and_print("info", f"Loaded {len(bcc_emails)} BCC recipients from bcc.txt (will be added to each email)")
    
    # Read additional_to.txt once (outside the loop)
    additional_to_file_path = base_folder / "additional_to.txt"
    additional_recipients = []
    if additional_to_file_path.is_file():
        additional_recipients = read_recipients(additional_to_file_path)
        if additional_recipients:
            log_and_print("info", f"Loaded {len(additional_recipients)} additional recipients from additional_to.txt (will be added to each email)")
    
    # Process each filter line to create individual email configurations
    email_configs = []
    total_original_recipients_count = 0
    
    for i, filter_line in enumerate(filters, 1):
        log_and_print("processing", f"Processing filter {i}/{len(filters)}: {filter_line}")
        
        # Get recipients for this specific filter
        filter_recipients = apply_filter_logic([filter_line], inventory_path)
        filter_recipients = deduplicate_emails(filter_recipients)
        
        # Merge with additional recipients
        if additional_recipients:
            original_count = len(filter_recipients)
            filter_recipients = merge_recipients(filter_recipients, additional_recipients)
            added_count = len(filter_recipients) - original_count
            if added_count > 0:
                log_and_print("info", f"Filter {i}: Added {added_count} additional recipients from additional_to.txt")
        
        if not filter_recipients:
            log_and_print("warning", f"Filter {i} matched no recipients: {filter_line}")
            continue
        
        # FIXED: Store original recipient count BEFORE any dry-run modifications
        original_recipients_count = len(filter_recipients)
        
        # Extract field values for substitution from matched rows in inventory
        field_values = {}
        if field_names:
            log_and_print("info", f"Filter {i}: Extracting field values from CSV for template substitution...")
            # FIXED: Pass base_folder to the function
            field_values = extract_field_values_from_matched_rows(filter_line, field_names, inventory_path, base_folder)
            
            # Validate and report field extraction results
            extracted_info = []
            empty_fields = []
            
            for field_name in field_names:
                field_value = field_values.get(field_name, "")
                if field_value:
                    value_count = len(field_value.split(',')) if ',' in field_value else 1
                    # Create a display-friendly preview
                    if value_count <= 3:
                        display_value = field_value
                    else:
                        first_three = ','.join(field_value.split(',')[:3])
                        display_value = f"{first_three}...+{value_count-3} more"
                    extracted_info.append(f"{field_name}=[{display_value}] ({value_count} unique)")
                else:
                    empty_fields.append(field_name)
            
            if extracted_info:
                log_and_print("info", f"Filter {i} successfully extracted: {', '.join(extracted_info)}")
            
            if empty_fields:
                log_and_print("warning", f"Filter {i} no values found for fields: {', '.join(empty_fields)}")
                log_and_print("info", f"  Check if these fields exist in inventory.csv and have data in matched rows")
            
            # Additional validation: warn if no substitutions will occur
            if not any(field_values.values()):
                log_and_print("warning", f"Filter {i}: No field values extracted - template placeholders will remain unchanged")
        else:
            log_and_print("info", f"Filter {i}: No field.txt found - no template substitution will be performed")
        
        # Create email configuration with SEPARATE fields for original and current recipients
        email_config = {
            'filter_line': filter_line,
            'recipients': filter_recipients.copy(),  # Current recipients (will be modified for dry-run)
            'original_recipients': filter_recipients.copy(),  # Original recipients (never modified)
            'field_values': field_values,
            'filter_number': i,
            'original_recipients_count': original_recipients_count  # Store original count
        }
        
        email_configs.append(email_config)
        
        # FIXED: Add to total_original_recipients_count BEFORE any dry-run modifications
        total_original_recipients_count += original_recipients_count
        
        log_and_print("info", f"Filter {i} will generate 1 email for {original_recipients_count} recipients")
    
    if not email_configs:
        log_and_print("error", "No filters generated any recipients")
        sys.exit(1)
    
    log_and_print("info", f"Multi mode will generate {len(email_configs)} individual emails")
    log_and_print("info", f"Total unique recipient addresses across all emails: {total_original_recipients_count}")
    
    if dry_run:
        # In dry-run mode, replace ONLY the 'recipients' field with approvers, keep 'original_recipients' intact
        approver_emails = read_recipients(base_folder / "approver.txt")
        approver_emails = deduplicate_emails(approver_emails)
        
        if not approver_emails:
            log_and_print("error", "No valid approver emails found in approver.txt")
            sys.exit(1)
        
        # Replace only the 'recipients' field with approvers for dry-run (keep original_recipients unchanged)
        for config in email_configs:
            config['recipients'] = approver_emails  # Replace with approvers for sending
            # config['original_recipients'] remains unchanged for reference
        
        final_cc_recipients = []  # No CC/BCC in dry-run
        final_bcc_recipients = []
        
        # Save original recipient data using original_recipients field
        original_configs_for_saving = []
        for config in email_configs:
            original_config = config.copy()
            # Use the preserved original_recipients for saving
            original_config['recipients'] = config['original_recipients']
            original_configs_for_saving.append(original_config)
        
        # Save original recipient data
        save_multi_mode_recipients(base_folder, original_configs_for_saving, cc_emails, bcc_emails)
        
        log_and_print("draft", f"DRY-RUN MODE: Will send {len(email_configs)} draft emails to {len(approver_emails)} approvers")
        log_and_print("draft", f"Original campaign would send to {total_original_recipients_count} total recipients")
        
    else:
        # Live mode - use actual CC/BCC
        final_cc_recipients = deduplicate_emails(cc_emails)
        final_bcc_recipients = deduplicate_emails(bcc_emails)
        
        # Save recipients in live mode
        save_multi_mode_recipients(base_folder, email_configs, final_cc_recipients, final_bcc_recipients)
    
    # Return original counts regardless of dry-run mode
    return (email_configs, final_cc_recipients, final_bcc_recipients, 
            total_original_recipients_count, original_cc_count, original_bcc_count)   
    

def save_multi_mode_recipients(base_folder: Path, email_configs: List[Dict], 
                               cc_recipients: List[str] = None, bcc_recipients: List[str] = None) -> None:
    """
    Save multi-mode recipients and field values to files.
    FIXED: Now properly saves field values as JSON files.
    """
    cc_recipients = cc_recipients or []
    bcc_recipients = bcc_recipients or []
    
    try:
        # Create a recipients subfolder for better organization
        recipients_folder = base_folder / "recipients"
        recipients_folder.mkdir(exist_ok=True)
        
        # Save individual filter recipient files
        all_unique_recipients = set()
        filter_summaries = []
        
        for i, config in enumerate(email_configs, 1):
            filter_line = config['filter_line']
            recipients = config['recipients']
            field_values = config.get('field_values', {})
            
            # Create a safe filename from filter line
            safe_filter_name = re.sub(r'[^\w\s.-]', '_', filter_line)[:50]  # Limit length
            safe_filter_name = re.sub(r'\s+', '_', safe_filter_name)  # Replace spaces with underscores
            
            # Save individual filter recipients
            filter_file = recipients_folder / f"filter_{i:03d}_{safe_filter_name}.txt"
            
            try:
                with filter_file.open('w', encoding='utf-8') as f:
                    # Write header with filter info
                    f.write(f"# Filter {i}: {filter_line}\n")
                    f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# Recipients: {len(recipients)}\n")
                    if field_values:
                        f.write(f"# Field values: {field_values}\n")
                    f.write("#\n")
                    
                    # Write recipients
                    for email in recipients:
                        f.write(f"{email}\n")
                        all_unique_recipients.add(email.lower())
                
                log_and_print("file", f"Saved {len(recipients)} recipients for filter {i} to {filter_file.name}")
                
                # FIXED: Save field values as JSON file if they exist
                if field_values:
                    json_file = recipients_folder / f"filter_{i:03d}_{safe_filter_name}_fields.json"
                    try:
                        with json_file.open('w', encoding='utf-8') as f:
                            json.dump({
                                'filter_number': i,
                                'filter_line': filter_line,
                                'recipient_count': len(recipients),
                                'generated_at': datetime.now().isoformat(),
                                'field_values': field_values
                            }, f, indent=2, ensure_ascii=False)
                        log_and_print("file", f"Saved field values for filter {i} to {json_file.name}")
                    except Exception as exc:
                        log_and_print("error", f"Failed to save field values JSON for filter {i}: {exc}")
                
                # Add to summary
                filter_summaries.append({
                    'filter_number': i,
                    'filter_line': filter_line,
                    'filename': filter_file.name,
                    'recipient_count': len(recipients),
                    'field_values': field_values,
                    'json_file': f"filter_{i:03d}_{safe_filter_name}_fields.json" if field_values else None
                })
                
            except Exception as exc:
                log_and_print("error", f"Failed to save recipients for filter {i}: {exc}")
        
        # Save CC recipients if any
        if cc_recipients:
            cc_file = recipients_folder / "cc_recipients.txt"
            try:
                with cc_file.open('w', encoding='utf-8') as f:
                    f.write(f"# CC Recipients\n")
                    f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# Recipients: {len(cc_recipients)}\n")
                    f.write("#\n")
                    for email in cc_recipients:
                        f.write(f"{email}\n")
                log_and_print("file", f"Saved {len(cc_recipients)} CC recipients to {cc_file.name}")
            except Exception as exc:
                log_and_print("error", f"Failed to save CC recipients: {exc}")
        
        # Save BCC recipients if any
        if bcc_recipients:
            bcc_file = recipients_folder / "bcc_recipients.txt"
            try:
                with bcc_file.open('w', encoding='utf-8') as f:
                    f.write(f"# BCC Recipients\n")
                    f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# Recipients: {len(bcc_recipients)}\n")
                    f.write("#\n")
                    for email in bcc_recipients:
                        f.write(f"{email}\n")
                log_and_print("file", f"Saved {len(bcc_recipients)} BCC recipients to {bcc_file.name}")
            except Exception as exc:
                log_and_print("error", f"Failed to save BCC recipients: {exc}")
        
        # Save comprehensive summary file
        summary_file = recipients_folder / "multi_mode_summary.txt"
        try:
            with summary_file.open('w', encoding='utf-8') as f:
                f.write("MULTI-MODE RECIPIENT SUMMARY\n")
                f.write("=" * 50 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Filters: {len(email_configs)}\n")
                f.write(f"Unique Recipients (TO): {len(all_unique_recipients)}\n")
                f.write(f"CC Recipients: {len(cc_recipients)}\n")
                f.write(f"BCC Recipients: {len(bcc_recipients)}\n")
                f.write("\n")
                
                # Individual filter details
                f.write("FILTER BREAKDOWN:\n")
                f.write("-" * 30 + "\n")
                total_to_recipients = 0
                
                for summary in filter_summaries:
                    f.write(f"\nFilter {summary['filter_number']}:\n")
                    f.write(f"  Condition: {summary['filter_line']}\n")
                    f.write(f"  Recipients: {summary['recipient_count']}\n")
                    f.write(f"  File: {summary['filename']}\n")
                    if summary['json_file']:
                        f.write(f"  Field Values JSON: {summary['json_file']}\n")
                    if summary['field_values']:
                        f.write(f"  Field Values Preview: {summary['field_values']}\n")
                    total_to_recipients += summary['recipient_count']
                
                f.write(f"\nTOTAL STATISTICS:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Total TO emails across all filters: {total_to_recipients}\n")
                f.write(f"Unique TO recipients: {len(all_unique_recipients)}\n")
                
                if len(email_configs) > 1 and (cc_recipients or bcc_recipients):
                    cc_bcc_total = (len(cc_recipients) + len(bcc_recipients)) * len(email_configs)
                    f.write(f"Total CC/BCC emails (sent with each filter): {cc_bcc_total}\n")
                    f.write(f"  - CC emails: {len(cc_recipients)} × {len(email_configs)} = {len(cc_recipients) * len(email_configs)}\n")
                    f.write(f"  - BCC emails: {len(bcc_recipients)} × {len(email_configs)} = {len(bcc_recipients) * len(email_configs)}\n")
                
                grand_total = total_to_recipients + (len(cc_recipients) + len(bcc_recipients)) * len(email_configs)
                f.write(f"GRAND TOTAL EMAILS: {grand_total}\n")
                
                # File listing
                f.write(f"\nGENERATED FILES:\n")
                f.write("-" * 20 + "\n")
                for summary in filter_summaries:
                    f.write(f"  {summary['filename']}\n")
                    if summary['json_file']:
                        f.write(f"  {summary['json_file']}\n")
                if cc_recipients:
                    f.write(f"  cc_recipients.txt\n")
                if bcc_recipients:
                    f.write(f"  bcc_recipients.txt\n")
                f.write(f"  multi_mode_summary.txt (this file)\n")
            
            log_and_print("file", f"Saved multi-mode summary to {summary_file.name}")
            
        except Exception as exc:
            log_and_print("error", f"Failed to save multi-mode summary: {exc}")
        
        # Save consolidated recipient list (all unique TO recipients)
        if all_unique_recipients:
            all_recipients_file = recipients_folder / "all_unique_recipients.txt"
            try:
                with all_recipients_file.open('w', encoding='utf-8') as f:
                    f.write(f"# All Unique TO Recipients (Multi-Mode)\n")
                    f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# Total Unique Recipients: {len(all_unique_recipients)}\n")
                    f.write(f"# Source: {len(email_configs)} filter conditions\n")
                    f.write("#\n")
                    for email in sorted(all_unique_recipients):
                        f.write(f"{email}\n")
                
                log_and_print("file", f"Saved {len(all_unique_recipients)} unique recipients to {all_recipients_file.name}")
                
            except Exception as exc:
                log_and_print("error", f"Failed to save consolidated recipient list: {exc}")
        
        # FIXED: Create consolidated field values JSON
        if any(config.get('field_values') for config in email_configs):
            consolidated_fields_file = recipients_folder / "all_field_values.json"
            try:
                consolidated_data = {
                    'generated_at': datetime.now().isoformat(),
                    'total_filters': len(email_configs),
                    'filters': []
                }
                
                for i, config in enumerate(email_configs, 1):
                    if config.get('field_values'):
                        consolidated_data['filters'].append({
                            'filter_number': i,
                            'filter_line': config['filter_line'],
                            'recipient_count': len(config['recipients']),
                            'field_values': config['field_values']
                        })
                
                with consolidated_fields_file.open('w', encoding='utf-8') as f:
                    json.dump(consolidated_data, f, indent=2, ensure_ascii=False)
                
                log_and_print("file", f"Saved consolidated field values to {consolidated_fields_file.name}")
                
            except Exception as exc:
                log_and_print("error", f"Failed to save consolidated field values: {exc}")
        
        # Log summary of what was saved
        log_and_print("backup", f"Multi-mode recipients saved to {recipients_folder.name}/")
        json_count = len([config for config in email_configs if config.get('field_values')])
        log_and_print("info", f"Created {len(filter_summaries)} filter files, {json_count} JSON field files, 1 summary file, 1 consolidated file")
        if cc_recipients or bcc_recipients:
            extra_files = []
            if cc_recipients:
                extra_files.append("CC")
            if bcc_recipients:
                extra_files.append("BCC")
            log_and_print("info", f"Additional files: {', '.join(extra_files)} recipient lists")
        
    except Exception as exc:
        log_and_print("error", f"Error saving multi-mode recipients: {exc}")



def prompt_for_confirmation() -> bool:
    """Prompt the user for a yes/no confirmation to proceed."""
    response = input("Do you want to proceed with sending emails? (yes/no): ").strip().lower()
    return response == 'yes'

def send_via_sendmail(recipients: List[str], subject: str, body_html: str, 
                     from_address: str, attachment_folder: Path = None, 
                     dry_run: bool = False, original_recipients_count: int = 0,
                     base_folder: Path = None, cc_recipients: List[str] = None,
                     bcc_recipients: List[str] = None,
                     original_cc_count: int = 0, original_bcc_count: int = 0,
                     filter_info: str = None) -> bool:
    """Send email using sendmail command. In dry-run mode, sends only to approvers with DRAFT prefix."""
    
    cc_recipients = cc_recipients or []
    bcc_recipients = bcc_recipients or []
    
    # Prepare subject for dry-run mode
    final_subject = subject
    if dry_run:
        # Add DRAFT prefix if not already present
        if not subject.upper().startswith('DRAFT'):
            final_subject = f"DRAFT - {subject}"
        
        # Add recipient count info to body for dry-run
        filter_info_html = f"<p style=\"color: #333333; margin: 4px 0; font-size: 14px;\"><strong>Filter:</strong> {filter_info}</p>" if filter_info else ""
        
        draft_info = f"""
        <div style="background-color: #f8f9fa; border: 2px solid #007BFF; padding: 12px; margin: 10px 0; border-radius: 6px; max-width: 500px; width: 100%; margin-left: 20px;">
            <h3 style="color: #0056b3; margin: 0 0 8px 0; font-size: 16px;">📝 Draft Email – Internal Review 🔍</h3>
            <p style="color: #333333; margin: 4px 0; font-size: 14px;"><strong>Status:</strong> This is a draft email shared for review and approval.</p>
            {filter_info_html}
            <p style="color: #333333; margin: 4px 0; font-size: 14px;"><strong>Original Recipient Count:</strong> {original_recipients_count}</p>
            <p style="color: #333333; margin: 5px 0;"><strong>Original CC Recipients:</strong> {original_cc_count}</p>
            <p style="color: #333333; margin: 5px 0;"><strong>Original BCC Recipients:</strong> {original_bcc_count}</p>
            <p style="color: #333333; margin: 5px 0;"><strong>Once approved, this message will be delivered to all {original_recipients_count + original_cc_count + original_bcc_count} intended recipients.</strong></p>
        </div>
        <hr style="margin: 16px 0; border: 0; border-top: 1px solid #ddd;">
        """
        body_html = draft_info + body_html
        
        total_original = original_recipients_count + original_cc_count + original_bcc_count
        log_and_print("draft", f"DRAFT mode: Sending to {len(recipients)} approver(s) instead of {total_original} original recipients")
        log_and_print("draft", f"Original breakdown - TO: {original_recipients_count}, CC: {original_cc_count}, BCC: {original_bcc_count}")
        log_and_print("draft", f"Subject: {final_subject}")
        log_and_print("draft", f"Approvers: {', '.join(recipients[:3])}{'...' if len(recipients) > 3 else ''}")
        
        if attachment_folder and attachment_folder.exists():
            attachments = [f.name for f in attachment_folder.iterdir() if f.is_file()]
            if attachments:
                log_and_print("draft", f"Attachments: {', '.join(attachments[:3])}{'...' if len(attachments) > 3 else ''}")
    else:
        total_recipients = len(recipients) + len(cc_recipients) + len(bcc_recipients)
        log_and_print("info", f"LIVE mode: Sending to {total_recipients} total recipients")
        log_and_print("info", f"TO: {len(recipients)}, CC: {len(cc_recipients)}, BCC: {len(bcc_recipients)}")
        log_and_print("info", f"Subject: {final_subject}")
        log_and_print("info", f"TO: {', '.join(recipients[:3])}{'...' if len(recipients) > 3 else ''}")
        if cc_recipients:
            log_and_print("info", f"CC: {', '.join(cc_recipients[:3])}{'...' if len(cc_recipients) > 3 else ''}")
        if bcc_recipients:
            log_and_print("info", f"BCC: {', '.join(bcc_recipients[:3])}{'...' if len(bcc_recipients) > 3 else ''}")
            
        if attachment_folder and attachment_folder.exists():
            attachments = [f.name for f in attachment_folder.iterdir() if f.is_file()]
            if attachments:
                log_and_print("info", f"Attachments: {', '.join(attachments[:3])}{'...' if len(attachments) > 3 else ''}")
    
    try:
        # Create the email message with base_folder for image embedding
        msg = create_email_message(recipients, final_subject, body_html, from_address, 
                                 attachment_folder, base_folder, cc_recipients, bcc_recipients)
        
        # Convert message to string
        email_content = msg.as_string()
        
        # Find sendmail path
        sendmail_path = find_sendmail_path()
        
        # All recipients (TO, CC, BCC) must be provided to sendmail for delivery
        all_recipients_for_delivery = recipients + cc_recipients + bcc_recipients
        
        # Call sendmail with proper arguments
        sendmail_cmd = [sendmail_path, '-f', from_address] + all_recipients_for_delivery
        
        process = subprocess.Popen(
            sendmail_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=email_content, timeout=60)
        
        if process.returncode == 0:
            if dry_run:
                log_and_print("success", f"DRAFT email sent successfully to {len(recipients)} approver(s)")
            else:
                log_and_print("success", f"Email sent successfully to {len(all_recipients_for_delivery)} total recipients")
            return True
        else:
            log_and_print("error", f"Sendmail failed with return code {process.returncode}")
            if stderr:
                log_and_print("error", f"Sendmail stderr: {stderr}")
            return False
            
    except FileNotFoundError:
        log_and_print("error", f"Sendmail not found at {sendmail_path}. Please install sendmail.")
        return False
    except subprocess.TimeoutExpired:
        log_and_print("error", "Sendmail timeout - operation took too long")
        return False
    except Exception as exc:
        log_and_print("error", f"Error sending email via sendmail: {exc}")
        return False

def send_single_mode_emails(recipients: List[str], subject: str, body_html: str, 
                           from_address: str, batch_size: int, dry_run: bool = False, 
                           delay: float = 5.0, attachment_folder: Path = None,
                           cc_recipients: List[str] = None, bcc_recipients: List[str] = None,
                           original_recipients_count: int = 0, base_folder: Path = None,
                           original_cc_count: int = 0, original_bcc_count: int = 0) -> None:
    """Send emails in single mode with batching."""
    
    cc_recipients = cc_recipients or []
    bcc_recipients = bcc_recipients or []
    
    # Initialize counters and totals
    total_recipients = len(recipients)
    total_batches = (total_recipients + batch_size - 1) // batch_size if total_recipients > 0 else 0
    successful_batches = 0
    failed_batches = 0
    
    # Handle edge case where no TO recipients but CC/BCC exist
    if total_recipients == 0 and (cc_recipients or bcc_recipients):
        # Create a single "batch" with just CC/BCC recipients
        log_and_print("info", "No TO recipients, sending single email with CC/BCC only")
        
        if dry_run:
            log_and_print("processing", f"Processing DRAFT email (CC/BCC only to approvers)")
        else:
            batch_total = len(cc_recipients) + len(bcc_recipients)
            log_and_print("processing", f"Processing email with {batch_total} CC/BCC recipients only")
        
        # Send email with empty TO list but include CC/BCC
        if send_via_sendmail([], subject, body_html, from_address, attachment_folder, 
                           dry_run, original_recipients_count, base_folder, 
                           cc_recipients, bcc_recipients, original_cc_count, original_bcc_count):
            successful_batches = 1
            log_and_print("success", "CC/BCC-only email completed successfully")
        else:
            failed_batches = 1
            log_and_print("error", "CC/BCC-only email failed")
    else:
        # Process TO recipients in batches
        for i in range(0, total_recipients, batch_size):
            batch = recipients[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            # Include CC/BCC in ALL batches
            current_cc = cc_recipients
            current_bcc = bcc_recipients
            
            if dry_run:
                log_and_print("processing", f"Processing DRAFT batch {batch_num}/{total_batches} ({len(batch)} approver(s))")
            else:
                batch_total = len(batch) + len(current_cc) + len(current_bcc)
                log_and_print("processing", f"Processing batch {batch_num}/{total_batches} ({batch_total} recipients)")
                if current_cc or current_bcc:
                    log_and_print("info", f"CC/BCC included in this batch")
            
            # Send current batch with CC/BCC included
            if send_via_sendmail(batch, subject, body_html, from_address, attachment_folder, 
                               dry_run, original_recipients_count, base_folder, 
                               current_cc, current_bcc, original_cc_count, original_bcc_count):
                successful_batches += 1
                log_and_print("success", f"Batch {batch_num} completed successfully")
            else:
                failed_batches += 1
                log_and_print("error", f"Batch {batch_num} failed")
            
            # Add delay between batches (except for the last batch)
            if i + batch_size < total_recipients and not dry_run:
                log_and_print("info", f"Waiting {delay} seconds before next batch...")
                time.sleep(delay)
    
    # Summary
    if dry_run:
        total_original = original_recipients_count + original_cc_count + original_bcc_count
        log_and_print("info", f"SINGLE MODE DRAFT processing complete: {successful_batches} successful, {failed_batches} failed")
        if total_original > 0:
            log_and_print("info", f"DRAFT emails sent to approvers for campaign targeting {total_original} recipients")
    else:
        log_and_print("info", f"SINGLE MODE batch processing complete: {successful_batches} successful, {failed_batches} failed")
        if successful_batches > 0:
            total_sent = (original_recipients_count + 
                         (original_cc_count * successful_batches) + 
                         (original_bcc_count * successful_batches))
            log_and_print("info", f"Total emails delivered: {total_sent}")
            if successful_batches > 1 and (original_cc_count > 0 or original_bcc_count > 0):
                log_and_print("info", f"Note: CC/BCC recipients received {successful_batches} copies (one per batch)")

def send_multi_mode_emails(email_configs: List[Dict], subject_template: str, body_template: str,
                          from_address: str, dry_run: bool = False, delay: float = 5.0,
                          attachment_folder: Path = None, base_folder: Path = None,
                          cc_recipients: List[str] = None, bcc_recipients: List[str] = None,
                          original_cc_count: int = 0, original_bcc_count: int = 0,
                          batch_size: int = 500) -> None:
    """Send emails in multi mode - one personalized email per filter condition with batching support."""
    
    cc_recipients = cc_recipients or []
    bcc_recipients = bcc_recipients or []
    
    successful_emails = 0
    failed_emails = 0
    total_batches = 0
    successful_batches = 0
    failed_batches = 0
    
    # Track which configs were successful for final calculation
    successful_configs = []
    
    log_and_print("info", f"MULTI MODE: Processing {len(email_configs)} filter conditions with batch-size {batch_size}")
    
    for config_num, config in enumerate(email_configs, 1):
        filter_line = config['filter_line']
        recipients = config['recipients']
        field_values = config.get('field_values', {})
        original_count = config.get('original_recipients_count', len(recipients))
        
        # Personalize subject and body
        personalized_subject = subject_template
        personalized_body = body_template
        
        if field_values:
            personalized_subject = substitute_placeholders(subject_template, field_values)
            personalized_body = substitute_placeholders(body_template, field_values)
            log_and_print("info", f"Filter {config_num}: Personalized subject: {personalized_subject}")
        
        # Calculate batches for this filter
        total_recipients = len(recipients)
        filter_batches = (total_recipients + batch_size - 1) // batch_size if total_recipients > 0 else 0
        total_batches += filter_batches
        
        log_and_print("processing", f"Processing filter {config_num}/{len(email_configs)}: {filter_line}")
        log_and_print("info", f"Recipients: {total_recipients}, Batches: {filter_batches}")
        
        # Handle case where no TO recipients but CC/BCC exist
        if total_recipients == 0 and (cc_recipients or bcc_recipients):
            log_and_print("info", f"Filter {config_num}: No TO recipients, sending single email with CC/BCC only")
            
            filter_info = filter_line if dry_run else None
            if send_via_sendmail([], personalized_subject, personalized_body, from_address,
                               attachment_folder, dry_run, original_count, base_folder,
                               cc_recipients, bcc_recipients, original_cc_count, original_bcc_count,
                               filter_info):
                successful_emails += 1
                successful_batches += 1
                successful_configs.append(config)  # Track successful config
                log_and_print("success", f"Filter {config_num} CC/BCC-only email sent successfully")
            else:
                failed_emails += 1
                failed_batches += 1
                log_and_print("error", f"Filter {config_num} CC/BCC-only email failed")
        else:
            # Process recipients in batches for this filter
            filter_successful_batches = 0
            filter_failed_batches = 0
            
            for i in range(0, total_recipients, batch_size):
                batch = recipients[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                # Include CC/BCC in ALL batches for this filter
                current_cc = cc_recipients
                current_bcc = bcc_recipients
                
                if dry_run:
                    log_and_print("processing", f"Filter {config_num}, Batch {batch_num}/{filter_batches}: DRAFT to {len(batch)} approver(s)")
                else:
                    batch_total = len(batch) + len(current_cc) + len(current_bcc)
                    log_and_print("processing", f"Filter {config_num}, Batch {batch_num}/{filter_batches}: {batch_total} recipients")
                    if current_cc or current_bcc:
                        log_and_print("info", f"CC/BCC included in this batch")
                
                # Send current batch with CC/BCC included
                filter_info = filter_line if dry_run else None
                if send_via_sendmail(batch, personalized_subject, personalized_body, from_address,
                                   attachment_folder, dry_run, original_count, base_folder,
                                   current_cc, current_bcc, original_cc_count, original_bcc_count,
                                   filter_info):
                    filter_successful_batches += 1
                    successful_batches += 1
                    log_and_print("success", f"Filter {config_num}, Batch {batch_num} completed successfully")
                else:
                    filter_failed_batches += 1
                    failed_batches += 1
                    log_and_print("error", f"Filter {config_num}, Batch {batch_num} failed")
                
                # Add delay between batches within the same filter (except for the last batch)
                if i + batch_size < total_recipients and not dry_run:
                    log_and_print("info", f"Waiting {delay} seconds before next batch...")
                    time.sleep(delay)
            
            # Determine if this filter was successful (at least one batch succeeded)
            if filter_successful_batches > 0:
                successful_emails += 1
                successful_configs.append(config)  # Track successful config
                log_and_print("success", f"Filter {config_num} completed: {filter_successful_batches}/{filter_successful_batches + filter_failed_batches} batches successful")
            else:
                failed_emails += 1
                log_and_print("error", f"Filter {config_num} failed: all {filter_failed_batches} batches failed")
        
        # Add delay between filters (except for the last one)
        if config_num < len(email_configs) and not dry_run:
            log_and_print("info", f"Waiting {delay} seconds before next filter...")
            time.sleep(delay)
    
    # Summary
    if dry_run:
        log_and_print("info", f"MULTI MODE DRAFT processing complete:")
        log_and_print("info", f"  - Filters processed: {successful_emails} successful, {failed_emails} failed")
        log_and_print("info", f"  - Batches processed: {successful_batches} successful, {failed_batches} failed")
        log_and_print("info", f"DRAFT emails sent to approvers for {len(email_configs)} individual campaigns")
    else:
        log_and_print("info", f"MULTI MODE processing complete:")
        log_and_print("info", f"  - Filters processed: {successful_emails} successful, {failed_emails} failed")
        log_and_print("info", f"  - Batches processed: {successful_batches} successful, {failed_batches} failed")
        
        if successful_batches > 0:
            # Calculate total emails delivered across all successful batches
            total_emails_delivered = 0
            for config in successful_configs:  # Use successful_configs instead
                recipients_count = len(config['recipients'])
                filter_batches = (recipients_count + batch_size - 1) // batch_size if recipients_count > 0 else 1
                # Each batch includes CC/BCC
                total_emails_delivered += recipients_count + (original_cc_count + original_bcc_count) * filter_batches
            
            log_and_print("info", f"Total individual emails delivered: {total_emails_delivered}")
            if (original_cc_count > 0 or original_bcc_count > 0):
                log_and_print("info", f"Note: CC/BCC recipients received multiple emails (one per batch per filter)")



def embed_images_in_html(html_content: str, base_folder: Path) -> Tuple[str, List[MIMEImage]]:
    """
    Replace image src attributes with cid references and return embedded images.
    """
    images_folder = base_folder / "images"
    embedded_images = []
    
    if not images_folder.exists():
        log_and_print("info", "No images folder found, skipping image embedding")
        return html_content, embedded_images
    
    # Find all img tags with src attributes
    img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
    
    def replace_img_src(match):
        img_tag = match.group(0)
        src = match.group(1)
        
        # Skip if already a cid: reference
        if src.startswith('cid:'):
            return img_tag
            
        # Skip external URLs (keep them as-is, but warn user)
        if src.startswith(('http://', 'https://')):
            log_and_print("warning", f"External image URL found: {src} - may be blocked by email clients")
            return img_tag
        
        # Handle local file references
        image_filename = Path(src).name
        image_path = images_folder / image_filename
        
        if not image_path.exists():
            log_and_print("warning", f"Image file not found: {image_path}")
            return img_tag
        
        try:
            # Read and encode image
            with open(image_path, 'rb') as img_file:
                img_data = img_file.read()
            
            # Create Content-ID
            cid = f"image_{len(embedded_images)}_{image_filename.replace('.', '_')}"
            
            # Create MIME image
            mime_type, _ = mimetypes.guess_type(str(image_path))
            if mime_type and mime_type.startswith('image/'):
                maintype, subtype = mime_type.split('/', 1)
                mime_img = MIMEImage(img_data, subtype)
                mime_img.add_header('Content-ID', f'<{cid}>')
                mime_img.add_header('Content-Disposition', 'inline', filename=image_filename)
                embedded_images.append(mime_img)
                
                # Replace src with cid reference
                new_img_tag = re.sub(r'src=["\'][^"\']+["\']', f'src="cid:{cid}"', img_tag)
                log_and_print("info", f"Embedded image: {image_filename} as {cid}")
                return new_img_tag
            else:
                log_and_print("warning", f"Unsupported image type: {image_path}")
                return img_tag
                
        except Exception as exc:
            log_and_print("error", f"Failed to embed image {image_path}: {exc}")
            return img_tag
    
    # Replace all img tags
    modified_html = re.sub(img_pattern, replace_img_src, html_content)
    
    if embedded_images:
        log_and_print("info", f"Embedded {len(embedded_images)} image(s) in email")
    
    return modified_html, embedded_images





def get_inventory_fields_for_help(test_mode: bool = False, custom_test_path: str = None) -> str:
    """
    Get available fields from inventory.csv for CLI help display.
    Returns a formatted string of available fields or error message.
    FIXED: Better error handling for custom test paths.
    """
    try:
        inventory_path = get_inventory_path(test_mode, custom_test_path)
        
        # FIXED: Better inventory name determination
        if test_mode:
            if custom_test_path:
                inventory_name = f"custom test inventory: {Path(custom_test_path).name}"
            else:
                inventory_name = "test-inventory.csv"
        else:
            inventory_name = "inventory.csv"
            
    except ValueError as e:
        return f"  [Inventory validation error: {e}]"
    
    try:
        with open(inventory_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            available_fields = reader.fieldnames or []
            
        if not available_fields:
            return f"  [No headers found in {inventory_name}]"
        
        # Format fields in a nice column layout
        field_list = sorted(available_fields)
        formatted_fields = []
        
        # Group fields in rows of 4 for better readability
        for i in range(0, len(field_list), 4):
            row_fields = field_list[i:i+4]
            formatted_row = "  " + " | ".join(f"{field:<15}" for field in row_fields)
            formatted_fields.append(formatted_row)
        
        result = f"  Available fields in {inventory_name} ({len(field_list)} total):\n"
        result += "\n".join(formatted_fields)
        return result
        
    except Exception as exc:
        return f"  [Error reading {inventory_name}: {exc}]"


def print_filter_syntax_help():
    """Print help information about filter syntax."""
    help_text = """
FILTER SYNTAX HELP:
==================
Filters use PromQL-style syntax with the following operators:
  =   Exact match (case-insensitive)
  !=  Not equal (case-insensitive)  
  =~  Regex match (case-insensitive)
  !~  Regex not match (case-insensitive)
  *   Wildcard match using *, ?, [] patterns

Examples:
  department=Engineering
  status!=inactive
  name=~"^John.*"
  email!~"@test\\.com$"
  department=*Sales*

Multiple conditions on same line = AND logic:
  department=Engineering,status=active

Multiple lines = OR logic:
  department=Engineering
  department=Sales

Comments start with # and are ignored.
"""
    print(help_text)
    

def main():
    """Enhanced main function with comprehensive help documentation"""
    
    # Enhanced help text with comprehensive information
    help_description = """
NotifyBot - Advanced Email Campaign Manager

OVERVIEW:
=========
NotifyBot is a sophisticated email campaign tool that supports two operating modes:
- SINGLE MODE: Send one email to many recipients (traditional broadcast)
- MULTI MODE: Send personalized emails based on filter conditions

OPERATING MODES:
===============
SINGLE MODE:
  • One email content sent to all recipients
  • Recipients from to.txt, filter.txt, additional_to.txt, cc.txt, or bcc.txt
  • Supports batching for large recipient lists
  • Best for announcements, newsletters, general communications

MULTI MODE:
  • Multiple personalized emails based on filter.txt conditions
  • Each filter condition generates a separate email
  • Template substitution using field.txt placeholders
  • Dynamic table generation with table-columns.txt
  • Best for targeted, personalized communications

MODE DETERMINATION (Priority Order):
  1. CLI --mode argument (highest priority)
  2. mode.txt file in campaign folder
  3. Default: single mode

REQUIRED FILES:
==============
All Modes:
  • subject.txt - Email subject line (supports template placeholders in multi mode)
  • body.html - Email body content (supports template placeholders in multi mode)
  • from.txt - Sender email address
  • approver.txt - Email addresses for dry-run testing

Single Mode Recipients (at least one required):
  • to.txt - Primary recipients (semicolon-separated)
  • cc.txt - CC recipients (semicolon-separated) 
  • bcc.txt - BCC recipients (semicolon-separated)
  • additional_to.txt - Additional TO recipients to merge
  • filter.txt + inventory.csv - Filter-based recipients

Multi Mode Requirements:
  • filter.txt - Filter conditions (one per line, OR logic between lines)
  • inventory.csv or test-inventory.csv - Data source for filtering
  
OPTIONAL FILES:
==============
  • field.txt - Field names for template substitution (multi mode)
  • table-columns.txt - Columns for dynamic table generation
  • field-inventory.csv - Local inventory (overrides global inventory)
  • mode.txt - Operating mode (single or multi)
  • attachment/ - Folder containing email attachments (15MB total limit)
  • images/ - Folder containing images to embed in emails
  • additional_to.txt - Additional recipients to merge (both modes)
  • cc.txt - CC recipients (both modes)
  • bcc.txt - BCC recipients (both modes)

SIGNATURE:
=========
  • /notifybot/signature.html - Global signature appended to all emails
  • Automatically combined with email body
  • HTML format supported

TEMPLATE SUBSTITUTION (Multi Mode):
==================================
Use {fieldname} placeholders in subject.txt and body.html
Available placeholders are defined in field.txt and populated from inventory data

Dynamic Table Fields:
  • {dynamic_table} - HTML table with matched data
  • {table_rows} - Just the table rows (no headers)
  • {styled_table_rows} - Striped table rows
  • {simple_table_rows} - Plain table rows
  • {csv_table_rows} - Pipe-separated table data
  • {table_headers} - Table headers only

FILTER SYNTAX (filter.txt):
===========================
Supports PromQL-style operators:
  = Exact match (case-insensitive)
  != Not equal (case-insensitive)
  =~ Regex match (case-insensitive)
  !~ Regex not match (case-insensitive)
  * Wildcard match (*, ?, [])

Examples:
  department=Engineering
  status!=inactive
  name=~"^John.*"
  location=*Office*

Logic:
  • Multiple conditions on same line = AND logic
  • Multiple lines = OR logic
  • Lines starting with # are comments

INVENTORY FILES:
===============
Priority Order (highest to lowest):
  1. field-inventory.csv (in campaign folder) - Used for field validation
  2. inventory.csv or test-inventory.csv - Global data source

TEST MODE:
=========
  • Use --test flag to use test-inventory.csv instead of inventory.csv
  • Use --test-inventory PATH for custom test inventory file
  • Helps prevent accidental sends to production data

DRY-RUN MODE:
============
  • Use --dry-run flag for safe testing
  • Sends DRAFT emails to approvers only
  • Shows original recipient counts in email
  • No actual recipients receive emails
  • Always recommended before live campaigns

BATCHING:
========
  • Large recipient lists are processed in batches
  • Default batch size: 500 recipients
  • Configurable delay between batches: 5.0 seconds
  • Prevents server overload and rate limiting

FOLDER STRUCTURE EXAMPLE:
========================
/notifybot/basefolder/my-campaign/
  ├── subject.txt          # Email subject
  ├── body.html           # Email body (HTML)
  ├── from.txt            # Sender address
  ├── approver.txt        # Approver emails for dry-run
  ├── mode.txt            # Operating mode (optional)
  ├── to.txt              # Primary recipients (optional)
  ├── cc.txt              # CC recipients (optional)
  ├── bcc.txt             # BCC recipients (optional)
  ├── additional_to.txt   # Additional recipients (optional)
  ├── filter.txt          # Filter conditions (multi mode)
  ├── field.txt           # Template fields (multi mode)
  ├── table-columns.txt   # Table columns (dynamic tables)
  ├── field-inventory.csv # Local inventory (optional)
  ├── attachment/         # Email attachments
  │   ├── document.pdf
  │   └── spreadsheet.xlsx
  ├── images/            # Embedded images
  │   ├── logo.png
  │   └── banner.jpg
  └── recipients/        # Generated recipient files
      ├── filter_001_department_Engineering.txt
      ├── cc_recipients.txt
      └── multi_mode_summary.txt

WORKFLOW RECOMMENDATIONS:
========================
1. Create campaign folder in /notifybot/basefolder/
2. Add required files (subject.txt, body.html, from.txt, approver.txt)
3. Test with --dry-run flag first
4. Review generated recipient files in recipients/ folder
5. Run live campaign without --dry-run

SAFETY FEATURES:
===============
  • Dry-run mode prevents accidental sends
  • Email validation and syntax checking
  • File existence verification
  • Attachment size limits (15MB total)
  • Confirmation prompts (unless --force)
  • Comprehensive logging
  • Recipient deduplication

COMMON USE CASES:
================
Single Mode:
  • Company-wide announcements
  • Newsletter distributions
  • Event notifications
  • Policy updates

Multi Mode:
  • Personalized onboarding emails
  • Department-specific communications
  • Role-based notifications
  • Custom reports for different teams

TROUBLESHOOTING:
===============
  • Check logs in /notifybot/logs/notifybot.log
  • Verify inventory.csv headers match field.txt
  • Ensure all required files exist
  • Test filter syntax with --dry-run
  • Check email addresses format
  • Verify attachment sizes (<15MB total)
"""

    parser = argparse.ArgumentParser(
        description=help_description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
EXAMPLES:
========
Basic dry-run test:
  python notifybot.py --base-folder my-campaign --dry-run

Live single mode with custom batch size:
  python notifybot.py --base-folder newsletter --batch-size 100 --delay 2.0

Multi mode with test inventory:
  python notifybot.py --base-folder personalized --mode multi --test --dry-run

Force send without confirmation:
  python notifybot.py --base-folder urgent --force

Custom test inventory:
  python notifybot.py --base-folder test-campaign --test --test-inventory /path/to/test.csv --dry-run

{get_inventory_fields_for_help()}

For more information, check the logs at /notifybot/logs/notifybot.log
        """
    )
    
    # Main arguments with enhanced help
    parser.add_argument(
        "--base-folder", 
        required=True, 
        metavar="FOLDER_NAME",
        help="""Campaign folder name inside /notifybot/basefolder/ [REQUIRED]
             Example: --base-folder my-campaign
             This folder should contain all campaign files (subject.txt, body.html, etc.)"""
    )
                       
    parser.add_argument(
        "--test", 
        action="store_true", 
        help="""Enable TEST MODE: Use test-inventory.csv instead of inventory.csv
             Recommended for testing campaigns before going live.
             Prevents accidental sends to production inventory data."""
    )
    
    parser.add_argument(
        "--test-inventory", 
        metavar="PATH",
        help="""Custom path to test inventory CSV file (requires --test flag)
             Example: --test-inventory /path/to/my-test-data.csv
             Allows testing with custom datasets without affecting main inventory.
             Must be used together with --test flag to take effect."""
    )

    parser.add_argument(
        "--mode", 
        choices=['single', 'multi'], 
        metavar="MODE",
        help="""Override operating mode [single|multi]
             single: One email sent to many recipients (broadcast)
             multi: Multiple personalized emails based on filter conditions
             Overrides mode.txt file setting if present.
             
             SINGLE MODE: Traditional email broadcast
             - Uses to.txt, cc.txt, bcc.txt, or filter-based recipients  
             - Same content to all recipients
             - Best for announcements, newsletters
             
             MULTI MODE: Personalized campaigns
             - Uses filter.txt conditions to create multiple emails
             - Each filter generates a separate personalized email
             - Supports template substitution with field.txt
             - Best for targeted, customized communications"""
    )
    
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="""SAFE MODE: Send draft emails to approvers only
             - No actual recipients receive emails
             - DRAFT prefix added to subject line
             - Shows original recipient counts in email body  
             - Sends to addresses in approver.txt instead
             - Generates all recipient files for review
             - STRONGLY RECOMMENDED before live campaigns
             
             Perfect for:
             - Testing email content and formatting
             - Verifying recipient lists and filters
             - Getting approval from stakeholders
             - Ensuring everything works correctly"""
    )
    
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="""Skip confirmation prompt and send immediately
             By default, NotifyBot asks for confirmation before sending.
             Use this flag to bypass the prompt for automated workflows.
             
             WARNING: Use with caution, especially in live mode!
             Always test with --dry-run first."""
    )
    
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=500, 
        metavar="N",
        help="""Recipients per batch to prevent server overload (default: 500)
             Large recipient lists are split into smaller batches.
             Smaller batches = slower sending but more server-friendly.
             Larger batches = faster sending but may hit rate limits.
             
             Recommended values:
             - Small lists (<1000): 500 (default)
             - Medium lists (1000-5000): 250-300  
             - Large lists (>5000): 100-200
             
             Each batch includes CC/BCC recipients in single mode.
             In multi mode, each filter is processed in batches."""
    )
    
    parser.add_argument(
        "--delay", 
        type=float, 
        default=5.0, 
        metavar="SECONDS",
        help="""Delay between batches in seconds (default: 5.0)
             Prevents overwhelming the email server and reduces spam risk.
             
             Recommended values:
             - Fast servers: 1.0-2.0 seconds
             - Standard servers: 5.0 seconds (default)
             - Slow/shared servers: 10.0+ seconds
             
             In multi mode, delay applies between:
             - Batches within the same filter
             - Different filter conditions"""
    )
    
    # Rest of the main function remains the same...
    args = parser.parse_args()
    
    # Set up logging FIRST before any other operations
    setup_logging()
    
    # Validation for --test-inventory without --test AFTER logging is set up
    if args.test_inventory and not args.test:
        log_and_print("warning", "--test-inventory provided without --test flag. Custom inventory path will be ignored.")
        log_and_print("info", "To use custom test inventory, use both flags: --test --test-inventory /path/to/file.csv")
        args.test_inventory = None
    
    if args.test:
        if args.test_inventory:
            log_and_print("mode", f"TEST MODE: Using custom test inventory: {args.test_inventory}")
            log_and_print("info", f"Custom test inventory validated: {args.test_inventory}")
        else:
            log_and_print("mode", "TEST MODE: Using default test-inventory.csv")
    
    # Get inventory fields for help text - Now safe to call after logging is set up
    inventory_fields_help = get_inventory_fields_for_help(args.test, args.test_inventory)
    
    try:
        base_folder = validate_base_folder(args.base_folder)
        
        # Determine operating mode
        mode = determine_mode(base_folder, args.mode)
        
        # Check required files based on mode
        required_files = ["subject.txt", "body.html", "from.txt", "approver.txt"]
        check_required_files(base_folder, required_files, args.dry_run, mode, args.test, args.test_inventory)
        # Read email content
        subject = read_file(base_folder / "subject.txt")
        body_html = read_file(base_folder / "body.html")
        from_address = read_file(base_folder / "from.txt")
        
        # Read signature (optional)
        signature_html = read_signature()
        
        # Combine body and signature
        final_body_html = combine_body_and_signature(body_html, signature_html)
        
        # Validate essential content
        if not subject:
            log_and_print("error", "Subject is empty")
            sys.exit(1)
        if not body_html:
            log_and_print("error", "Body HTML is empty")
            sys.exit(1)
        if not from_address or not is_valid_email(from_address):
            log_and_print("error", f"Invalid from address: {from_address}")
            sys.exit(1)
        
        # Check attachment folder
        attachment_folder = base_folder / "attachment"
        if attachment_folder.exists():
            attachment_count = len([f for f in attachment_folder.iterdir() if f.is_file()])
            log_and_print("info", f"Found {attachment_count} attachment(s) in {attachment_folder}")
        else:
            attachment_folder = None
            log_and_print("info", "No attachment folder found")
        
        # Process based on mode - FIXED: Pass args properly to both mode functions
        if mode == "single":
            (final_recipients, final_cc_recipients, final_bcc_recipients, 
             original_recipients_count, original_cc_count, original_bcc_count) = get_recipients_for_single_mode(
                 base_folder, args.dry_run, args.test, args.test_inventory)
            
            # Show summary
            log_and_print("confirmation", f"SINGLE MODE Email Summary:")
            log_and_print("confirmation", f"From: {from_address}")
            log_and_print("confirmation", f"Subject: {subject}")
            if signature_html:
                log_and_print("confirmation", f"Signature: Loaded ({len(signature_html)} characters)")
            if args.dry_run:
                total_original = original_recipients_count + original_cc_count + original_bcc_count
                log_and_print("confirmation", f"Mode: DRY-RUN (DRAFT emails to approvers)")
                log_and_print("confirmation", f"Approvers: {len(final_recipients)}")
                log_and_print("confirmation", f"Original campaign would target: {total_original} recipients")
                log_and_print("confirmation", f"  - TO: {original_recipients_count}")
                log_and_print("confirmation", f"  - CC: {original_cc_count}")
                log_and_print("confirmation", f"  - BCC: {original_bcc_count}")
            else:
                total_live = len(final_recipients) + len(final_cc_recipients) + len(final_bcc_recipients)
                log_and_print("confirmation", f"Mode: LIVE")
                log_and_print("confirmation", f"Total Recipients: {total_live}")
                log_and_print("confirmation", f"  - TO: {len(final_recipients)}")
                log_and_print("confirmation", f"  - CC: {len(final_cc_recipients)}")
                log_and_print("confirmation", f"  - BCC: {len(final_bcc_recipients)}")
                log_and_print("confirmation", f"Batch size: {args.batch_size}")
                log_and_print("confirmation", f"Delay: {args.delay}s")
            
            if not args.force:
                if not prompt_for_confirmation():
                    log_and_print("info", "Email sending aborted by user.")
                    sys.exit(0)
            
            # Send emails in single mode
            send_single_mode_emails(
                final_recipients, 
                subject, 
                final_body_html,  # Use final_body_html with signature
                from_address, 
                args.batch_size, 
                dry_run=args.dry_run, 
                delay=args.delay,
                attachment_folder=attachment_folder,
                original_recipients_count=original_recipients_count,
                base_folder=base_folder,
                cc_recipients=final_cc_recipients,
                bcc_recipients=final_bcc_recipients,
                original_cc_count=original_cc_count,
                original_bcc_count=original_bcc_count
            )
            
        elif mode == "multi":
            (email_configs, final_cc_recipients, final_bcc_recipients, 
             total_original_recipients_count, original_cc_count, original_bcc_count) = get_recipients_for_multi_mode(
                 base_folder, args.dry_run, args.test, args.test_inventory)
            
            # Show summary - FIXED VERSION
            log_and_print("confirmation", f"MULTI MODE Email Summary:")
            log_and_print("confirmation", f"From: {from_address}")
            log_and_print("confirmation", f"Subject Template: {subject}")
            if signature_html:
                log_and_print("confirmation", f"Signature: Loaded ({len(signature_html)} characters)")
            log_and_print("confirmation", f"Number of Individual Emails: {len(email_configs)}")
            
            if args.dry_run:
                total_cc_bcc_original = original_cc_count + original_bcc_count
                # FIXED: Get approver count from the first config's current recipients (which are now approvers)
                approver_count = len(email_configs[0]['recipients']) if email_configs else 0
                total_draft_emails = len(email_configs)
                
                log_and_print("confirmation", f"Mode: DRY-RUN (DRAFT emails to approvers)")
                log_and_print("confirmation", f"Will send {total_draft_emails} draft emails to {approver_count} approver(s)")
                log_and_print("confirmation", f"Original campaign breakdown:")
                log_and_print("confirmation", f"  - Individual emails: {len(email_configs)}")
                log_and_print("confirmation", f"  - Total TO recipients across all emails: {total_original_recipients_count}")
                log_and_print("confirmation", f"  - CC per email: {original_cc_count}")
                log_and_print("confirmation", f"  - BCC per email: {original_bcc_count}")
                if len(email_configs) > 1 and total_cc_bcc_original > 0:
                    total_cc_bcc_emails = (original_cc_count + original_bcc_count) * len(email_configs)
                    log_and_print("confirmation", f"  - Total CC/BCC emails: {total_cc_bcc_emails} ({original_cc_count + original_bcc_count} × {len(email_configs)} emails)")
                
                # FIXED: Show breakdown of original recipients per filter for better clarity
                log_and_print("confirmation", f"Original filter breakdown:")
                for i, config in enumerate(email_configs[:3], 1):
                    original_count = config.get('original_recipients_count', 0)
                    filter_line = config['filter_line']
                    # Truncate long filter lines for display
                    display_filter = filter_line[:50] + "..." if len(filter_line) > 50 else filter_line
                    log_and_print("confirmation", f"  {i}. {display_filter} → {original_count} recipient(s)")
                if len(email_configs) > 3:
                    remaining_total = sum(config.get('original_recipients_count', 0) for config in email_configs[3:])
                    log_and_print("confirmation", f"  ... and {len(email_configs) - 3} more filters → {remaining_total} additional recipient(s)")
                
            else:
                total_cc_bcc_per_email = len(final_cc_recipients) + len(final_bcc_recipients)
                log_and_print("confirmation", f"Mode: LIVE")
                log_and_print("confirmation", f"Will send {len(email_configs)} individual emails")
                log_and_print("confirmation", f"Total TO recipients across all emails: {total_original_recipients_count}")
                log_and_print("confirmation", f"CC per email: {len(final_cc_recipients)}")
                log_and_print("confirmation", f"BCC per email: {len(final_bcc_recipients)}")
                if len(email_configs) > 1 and total_cc_bcc_per_email > 0:
                    total_cc_bcc_emails = total_cc_bcc_per_email * len(email_configs)
                    log_and_print("confirmation", f"Total CC/BCC emails: {total_cc_bcc_emails} ({total_cc_bcc_per_email} × {len(email_configs)} emails)")
                
                # Show filter examples for live mode
                log_and_print("confirmation", f"Filter examples:")
                for i, config in enumerate(email_configs[:3], 1):
                    recipient_count = len(config.get('recipients', []))
                    filter_line = config['filter_line']
                    display_filter = filter_line[:50] + "..." if len(filter_line) > 50 else filter_line
                    log_and_print("confirmation", f"  {i}. {display_filter} → {recipient_count} recipient(s)")
                if len(email_configs) > 3:
                    log_and_print("confirmation", f"  ... and {len(email_configs) - 3} more")
            
            log_and_print("confirmation", f"Email delay: {args.delay}s")
            
            # Confirmation prompt unless --force
            if not args.force:
                if not prompt_for_confirmation():
                    log_and_print("info", "Email sending aborted by user.")
                    sys.exit(0)
            
            # Send emails in multi mode
            send_multi_mode_emails(
                email_configs,
                subject,  # subject template
                final_body_html,  # body template with signature
                from_address,
                dry_run=args.dry_run,
                delay=args.delay,
                attachment_folder=attachment_folder,
                base_folder=base_folder,
                cc_recipients=final_cc_recipients,
                bcc_recipients=final_bcc_recipients,
                original_cc_count=original_cc_count,
                original_bcc_count=original_bcc_count,
                batch_size=args.batch_size
            )
        
        log_and_print("success", f"NotifyBot {mode.upper()} MODE execution completed successfully")
        
    except MissingRequiredFilesError as e:
        log_and_print("error", str(e))
        sys.exit(1)
    except ValueError as e:
        log_and_print("error", str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        log_and_print("warning", "Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_and_print("error", f"Unexpected error: {e}")
        log_and_print("error", f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
