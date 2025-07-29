#!/usr/bin/env python3
"""
NotifyBot: Automated email batch sender with single/multi mode support, filtering, logging, signature support, and dry-run.

Usage:
    python notifybot.py --base-folder emails --dry-run
    python notifybot.py --base-folder emails --force --mode single
    python notifybot.py --base-folder emails --batch-size 500 --delay 5.0 --mode multi

CLI Options:
    --base-folder         Base directory containing email input files [REQUIRED]. 
                          The directory should be inside /notifybot/basefolder.
    --mode               Force mode: 'single' or 'multi' (overrides mode.txt)
    --dry-run            Simulate sending emails without SMTP. Sends only to approvers with DRAFT prefix.
    --batch-size         Number of emails to send per batch (default: 500).
    --delay              Delay in seconds between batches (default: 5.0).
    --force              Skip confirmation prompt (for automation).

Single Mode - Sends ONE email to MULTIPLE recipients:
    Required files: subject.txt, body.html, from.txt, approver.txt
    Recipient sources: to.txt OR filter.txt+inventory.csv OR additional_to.txt
    Optional: cc.txt, bcc.txt, attachment/, images/, signature.html

Multi Mode - Sends MULTIPLE personalized emails:
    Required files: subject.txt, body.html, from.txt, approver.txt, filter.txt
    Optional: field.txt (for placeholder substitution), cc.txt, bcc.txt, attachment/, images/, signature.html
    Each line in filter.txt creates a separate personalized email.
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
INVENTORY_PATH = NOTIFYBOT_ROOT / "inventory" / "inventory.csv"  # New location of inventory.csv

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
    Read signature from /notifybot/signature.html file if it exists.
    Returns empty string if file doesn't exist or can't be read.
    
    Returns:
        str: Signature HTML content or empty string
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
    Combine body HTML and signature HTML properly.
    Adds appropriate spacing and formatting between body and signature.
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

def check_required_files(base: Path, required: List[str], dry_run: bool = True, mode: str = "single") -> None:
    """Ensure required files exist based on mode."""
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        raise MissingRequiredFilesError(f"Missing required files: {', '.join(missing)}")
    
    # Multi mode requires filter.txt
    if mode == "multi":
        if not (base / "filter.txt").is_file():
            raise MissingRequiredFilesError("Multi mode requires filter.txt")
        if not INVENTORY_PATH.is_file():
            raise MissingRequiredFilesError("Multi mode requires inventory.csv at /notifybot/inventory/inventory.csv")
    
    # Single mode requires at least one recipient source in live mode
    if mode == "single" and not dry_run:
        has_to = (base / "to.txt").is_file()
        has_filters = (base / "filter.txt").is_file() and INVENTORY_PATH.is_file()
        has_additional = (base / "additional_to.txt").is_file()
        has_cc = (base / "cc.txt").is_file()
        has_bcc = (base / "bcc.txt").is_file()
        
        if not (has_to or has_filters or has_additional or has_cc or has_bcc):
            raise MissingRequiredFilesError(
                "Single mode requires at least one recipient source: 'to.txt', 'filter.txt + inventory.csv', 'additional_to.txt', 'cc.txt', or 'bcc.txt'."
            )

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
    Check if a row matches the filter conditions with wildcard support.
    Each line in filters represents an OR condition.
    Within each line, comma-separated conditions are AND conditions.
    
    Supports wildcards:
    - * matches any sequence of characters
    - ? matches any single character
    - [seq] matches any character in seq
    - [!seq] matches any character not in seq
    """
    if not filters:
        return True  # No filters means include all
    
    def matches_pattern(text: str, pattern: str) -> bool:
        """Check if text matches pattern with wildcard support."""
        # Convert both to lowercase for case-insensitive matching
        text = str(text).lower()
        pattern = pattern.lower()
        
        # Use fnmatch for Unix shell-style wildcards
        return fnmatch.fnmatch(text, pattern)
    
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
                
            if '=' in condition:
                # Key=value format with wildcard support
                key, value = condition.split('=', 1)
                key, value = key.strip(), value.strip()
                
                if key not in row:
                    line_matches = False
                    break  # Key doesn't exist, condition fails
                
                # Use wildcard matching instead of exact matching
                if not matches_pattern(row[key], value):
                    line_matches = False
                    break  # This AND condition failed
            else:
                # Simple wildcard search in all values
                condition_matched = False
                for row_value in row.values():
                    if matches_pattern(row_value, condition):
                        condition_matched = True
                        break
                
                if not condition_matched:
                    line_matches = False
                    break  # This AND condition failed
        
        # If this line matched completely (all AND conditions), return True (OR logic)
        if line_matches:
            return True
    
    # None of the OR conditions matched
    return False

def apply_filter_logic(filters: List[str], inventory_path: Path) -> List[str]:
    """Apply the filter logic using 'filter.txt' and 'inventory.csv'."""
    filtered_recipients = []
    
    if not inventory_path.exists():
        log_and_print("error", f"Inventory file not found: {inventory_path}")
        return filtered_recipients
    
    try:
        with open(inventory_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                if matches_filter_conditions(row, filters):
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
        
        log_and_print("info", f"Filter applied: {len(filtered_recipients)} unique recipients selected from inventory")
        
    except Exception as exc:
        log_and_print("error", f"Error applying filter logic: {exc}")
    
    return filtered_recipients

def extract_field_values_from_filter(filter_line: str, field_names: List[str]) -> Dict[str, str]:
    """
    Extract field values from a filter line for template substitution.
    
    Args:
        filter_line: Single filter line like "department=sales,region=north"
        field_names: List of field names to extract
    
    Returns:
        Dictionary of field_name -> value mappings
    """
    field_values = {}
    
    # Initialize all fields to empty
    for field in field_names:
        field_values[field] = ""
    
    # Parse filter conditions
    and_conditions = [condition.strip() for condition in filter_line.split(',')]
    
    for condition in and_conditions:
        if '=' in condition:
            key, value = condition.split('=', 1)
            key, value = key.strip(), value.strip()
            
            # If this key is in our field names, store its value
            if key in field_names:
                field_values[key] = value
    
    return field_values

def substitute_placeholders(template: str, field_values: Dict[str, str]) -> str:
    """
    Replace placeholders in template with field values.
    
    Args:
        template: Template string with placeholders like "Report for {department}"
        field_values: Dictionary of field_name -> value mappings
    
    Returns:
        Template with placeholders replaced
    """
    result = template
    for field, value in field_values.items():
        placeholder = f"{{{field}}}"
        result = result.replace(placeholder, value)
    
    return result

def get_recipients_for_single_mode(base_folder: Path, dry_run: bool) -> Tuple[List[str], List[str], List[str], int, int, int]:
    """
    Get recipients for single mode operation.
    
    Returns:
        (final_recipients, final_cc_recipients, final_bcc_recipients, 
         original_recipients_count, original_cc_count, original_bcc_count)
    """
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
            
        # Calculate original TO recipients
        if to_file_path.is_file():
            original_recipients = read_recipients(to_file_path)
            if additional_to_file_path.is_file():
                additional_recipients = read_recipients(additional_to_file_path)
                if additional_recipients:
                    original_recipients = merge_recipients(original_recipients, additional_recipients)
        elif filter_file_path.is_file() and INVENTORY_PATH.is_file():
            filters = read_file(filter_file_path).splitlines()
            filtered_recipients = apply_filter_logic(filters, INVENTORY_PATH)
            original_recipients = deduplicate_emails(filtered_recipients)
                    
            if additional_to_file_path.is_file():
                additional_recipients = read_recipients(additional_to_file_path)
                if additional_recipients:
                    original_recipients = merge_recipients(original_recipients, additional_recipients)
            if original_recipients and not to_file_path.is_file():
                write_recipients_to_file(to_file_path, original_recipients)
        elif additional_to_file_path.is_file():
            original_recipients = read_recipients(additional_to_file_path)
            if original_recipients and not to_file_path.is_file():
                write_recipients_to_file(to_file_path, original_recipients)

        original_recipients_count = len(deduplicate_emails(original_recipients))
        original_cc_count = len(deduplicate_emails(cc_emails))
        original_bcc_count = len(deduplicate_emails(bcc_emails))
        
        total_original = original_recipients_count + original_cc_count + original_bcc_count
        log_and_print("draft", f"DRY-RUN MODE: Will send to {len(final_recipients)} approvers instead of {total_original} actual recipients")
        
    else:
        # Live mode - determine actual recipients
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
                    log_and_print("info", f"Merged {len(additional_recipients)} additional recipients from additional_to.txt")
                    log_and_print("info", f"Total recipients after merge: {len(recipients)} (added {len(recipients) - original_count} new)")
        
        # Priority 2: Use filter logic if to.txt doesn't exist
        elif filter_file_path.is_file() and INVENTORY_PATH.is_file():
            filters = read_file(filter_file_path).splitlines()
            recipients = apply_filter_logic(filters, INVENTORY_PATH)
            log_and_print("info", f"Loaded {len(recipients)} recipients from filter logic")
            
            # Check for additional_to.txt and merge with filtered results
            if additional_to_file_path.is_file():
                additional_recipients = read_recipients(additional_to_file_path)
                if additional_recipients:
                    original_count = len(recipients)
                    recipients = merge_recipients(recipients, additional_recipients)
                    log_and_print("info", f"Merged {len(additional_recipients)} additional recipients from additional_to.txt")
                    log_and_print("info", f"Total recipients after merge: {len(recipients)} (added {len(recipients) - original_count} new)")
            
            # Write the merged results to to.txt for future reference
            if recipients:
                write_recipients_to_file(to_file_path, recipients)
                log_and_print("file", f"Created to.txt with {len(recipients)} merged recipients (filter + additional)")
        
        # Priority 3: Use only additional_to.txt if nothing else is available
        elif additional_to_file_path.is_file():
            recipients = read_recipients(additional_to_file_path)
            log_and_print("info", f"Loaded {len(recipients)} recipients from additional_to.txt only")
            
            # Create to.txt from additional_to.txt
            if recipients:
                write_recipients_to_file(to_file_path, recipients)
                log_and_print("file", f"Created to.txt from additional_to.txt with {len(recipients)} recipients")
        
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

def get_recipients_for_multi_mode(base_folder: Path, dry_run: bool) -> Tuple[List[Dict], List[str], List[str], int, int, int]:
    """
    Get recipients for multi mode operation.
    
    Returns:
        (email_configs, final_cc_recipients, final_bcc_recipients, 
         total_original_recipients_count, original_cc_count, original_bcc_count)
    """
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
    
    # Read CC and BCC recipients
    cc_emails = read_recipients(base_folder / "cc.txt")
    bcc_emails = read_recipients(base_folder / "bcc.txt")
    
    if cc_emails:
        log_and_print("info", f"Loaded {len(cc_emails)} CC recipients from cc.txt (will be added to each email)")
    if bcc_emails:
        log_and_print("info", f"Loaded {len(bcc_emails)} BCC recipients from bcc.txt (will be added to each email)")
    
    # Process each filter line to create individual email configurations
    email_configs = []
    total_original_recipients_count = 0
    
    for i, filter_line in enumerate(filters, 1):
        log_and_print("processing", f"Processing filter {i}/{len(filters)}: {filter_line}")
        
        # Get recipients for this specific filter
        filter_recipients = apply_filter_logic([filter_line], INVENTORY_PATH)
        filter_recipients = deduplicate_emails(filter_recipients)
        
        if not filter_recipients:
            log_and_print("warning", f"Filter {i} matched no recipients: {filter_line}")
            continue
        
        # Extract field values for substitution
        field_values = {}
        if field_names:
            field_values = extract_field_values_from_filter(filter_line, field_names)
            log_and_print("info", f"Filter {i} field values: {field_values}")
        
        # Create email configuration
        email_config = {
            'filter_line': filter_line,
            'recipients': filter_recipients,
            'field_values': field_values,
            'filter_number': i
        }
        
        email_configs.append(email_config)
        total_original_recipients_count += len(filter_recipients)
        
        log_and_print("info", f"Filter {i} will generate 1 email for {len(filter_recipients)} recipients")
    
    if not email_configs:
        log_and_print("error", "No filters generated any recipients")
        sys.exit(1)
    
    log_and_print("info", f"Multi mode will generate {len(email_configs)} individual emails")
    log_and_print("info", f"Total unique recipient addresses across all emails: {total_original_recipients_count}")
    
    if dry_run:
        # In dry-run mode, replace all recipients with approvers
        approver_emails = read_recipients(base_folder / "approver.txt")
        approver_emails = deduplicate_emails(approver_emails)
        
        if not approver_emails:
            log_and_print("error", "No valid approver emails found in approver.txt")
            sys.exit(1)
        
        # Replace recipients in each email config with approvers
        for config in email_configs:
            config['original_recipients_count'] = len(config['recipients'])
            config['recipients'] = approver_emails  # All emails go to approvers in dry-run
        
        final_cc_recipients = []  # No CC/BCC in dry-run
        final_bcc_recipients = []
        original_cc_count = len(deduplicate_emails(cc_emails))
        original_bcc_count = len(deduplicate_emails(bcc_emails))
        
        log_and_print("draft", f"DRY-RUN MODE: Will send {len(email_configs)} draft emails to {len(approver_emails)} approvers")
        log_and_print("draft", f"Original campaign would send to {total_original_recipients_count} total recipients")
        
    else:
        # Live mode - use actual CC/BCC
        final_cc_recipients = deduplicate_emails(cc_emails)
        final_bcc_recipients = deduplicate_emails(bcc_emails)
        original_cc_count = len(final_cc_recipients)
        original_bcc_count = len(final_bcc_recipients)
        
        # Add original count for each config
        for config in email_configs:
            config['original_recipients_count'] = len(config['recipients'])
    
    return (email_configs, final_cc_recipients, final_bcc_recipients, 
            total_original_recipients_count, original_cc_count, original_bcc_count)

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
                          original_cc_count: int = 0, original_bcc_count: int = 0) -> None:
    """Send emails in multi mode - one personalized email per filter condition."""
    
    cc_recipients = cc_recipients or []
    bcc_recipients = bcc_recipients or []
    
    successful_emails = 0
    failed_emails = 0
    total_emails = len(email_configs)
    
    log_and_print("info", f"MULTI MODE: Sending {total_emails} individual emails")
    
    for i, config in enumerate(email_configs, 1):
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
            log_and_print("info", f"Email {i}: Personalized subject: {personalized_subject}")
        
        # Log email details
        if dry_run:
            log_and_print("processing", f"Processing DRAFT email {i}/{total_emails} to {len(recipients)} approver(s)")
            log_and_print("draft", f"Filter: {filter_line}")
        else:
            total_recipients_this_email = len(recipients) + len(cc_recipients) + len(bcc_recipients)
            log_and_print("processing", f"Processing email {i}/{total_emails} to {total_recipients_this_email} recipients")
            log_and_print("info", f"Filter: {filter_line}")
            log_and_print("info", f"TO: {len(recipients)}, CC: {len(cc_recipients)}, BCC: {len(bcc_recipients)}")
        
        # Send the email
        filter_info = filter_line if dry_run else None
        if send_via_sendmail(recipients, personalized_subject, personalized_body, from_address,
                           attachment_folder, dry_run, original_count, base_folder,
                           cc_recipients, bcc_recipients, original_cc_count, original_bcc_count,
                           filter_info):
            successful_emails += 1
            log_and_print("success", f"Email {i} sent successfully")
        else:
            failed_emails += 1
            log_and_print("error", f"Email {i} failed")
        
        # Add delay between emails (except for the last one)
        if i < total_emails and not dry_run:
            log_and_print("info", f"Waiting {delay} seconds before next email...")
            time.sleep(delay)
    
    # Summary
    if dry_run:
        log_and_print("info", f"MULTI MODE DRAFT processing complete: {successful_emails} successful, {failed_emails} failed")
        log_and_print("info", f"DRAFT emails sent to approvers for {total_emails} individual campaigns")
    else:
        log_and_print("info", f"MULTI MODE processing complete: {successful_emails} successful, {failed_emails} failed")
        if successful_emails > 0:
            # In multi mode, CC/BCC are sent with EVERY email
            total_emails_delivered = 0
            for config in email_configs[:successful_emails]:  # Only count successful ones
                original_count = config.get('original_recipients_count', len(config['recipients']))
                total_emails_delivered += original_count + original_cc_count + original_bcc_count
            
            log_and_print("info", f"Total individual emails delivered: {total_emails_delivered}")
            if successful_emails > 1 and (original_cc_count > 0 or original_bcc_count > 0):
                log_and_print("info", f"Note: CC/BCC recipients received {successful_emails} separate emails")

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

def main():
    """Enhanced main function with single/multi mode support and signature functionality"""
    parser = argparse.ArgumentParser(description="Send batch emails with single/multi mode support and signature.")
    parser.add_argument("--base-folder", required=True, help="Base folder name inside /notifybot/basefolder.")
    parser.add_argument("--mode", choices=['single', 'multi'], help="Force mode: 'single' or 'multi' (overrides mode.txt)")
    parser.add_argument("--dry-run", action="store_true", help="Send emails only to approvers with DRAFT prefix.")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt.")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of emails per batch (default: 500).")
    parser.add_argument("--delay", type=float, default=5.0, help="Delay in seconds between batches (default: 5.0).")
    
    args = parser.parse_args()
    
    setup_logging()
    
    try:
        base_folder = validate_base_folder(args.base_folder)
        
        # Determine operating mode
        mode = determine_mode(base_folder, args.mode)
        
        # Check required files based on mode
        required_files = ["subject.txt", "body.html", "from.txt", "approver.txt"]
        check_required_files(base_folder, required_files, args.dry_run, mode)
        
        # Read email content
        subject = read_file(base_folder / "subject.txt")
        body_html = read_file(base_folder / "body.html")
        from_address = read_file(base_folder / "from.txt")
        
        # Read signature (optional)
        signature_html = read_signature(base_folder)
        
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
        
        # Process based on mode
        if mode == "single":
            # Single mode processing
            (final_recipients, final_cc_recipients, final_bcc_recipients, 
             original_recipients_count, original_cc_count, original_bcc_count) = get_recipients_for_single_mode(base_folder, args.dry_run)
            
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
            # Multi mode processing
            (email_configs, final_cc_recipients, final_bcc_recipients, 
             total_original_recipients_count, original_cc_count, original_bcc_count) = get_recipients_for_multi_mode(base_folder, args.dry_run)
            
            # Show summary
            log_and_print("confirmation", f"MULTI MODE Email Summary:")
            log_and_print("confirmation", f"From: {from_address}")
            log_and_print("confirmation", f"Subject Template: {subject}")
            if signature_html:
                log_and_print("confirmation", f"Signature: Loaded ({len(signature_html)} characters)")
            log_and_print("confirmation", f"Number of Individual Emails: {len(email_configs)}")
            
            if args.dry_run:
                total_cc_bcc_original = original_cc_count + original_bcc_count
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
            
            log_and_print("confirmation", f"Email delay: {args.delay}s")
            
            # Show first few filter examples
            log_and_print("confirmation", f"Filter examples:")
            for i, config in enumerate(email_configs[:3], 1):
                log_and_print("confirmation", f"  {i}. {config['filter_line']} → {len(config.get('recipients', []))} recipient(s)")
            if len(email_configs) > 3:
                log_and_print("confirmation", f"  ... and {len(email_configs) - 3} more")
            
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
                original_bcc_count=original_bcc_count
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
