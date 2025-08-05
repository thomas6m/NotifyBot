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

def validate_fields_against_inventory(base_folder: Path, inventory_path: Path, mode: str = "single") -> Tuple[bool, List[str]]:
    """
    Validate that all field names used in filter.txt and field.txt exist in inventory.csv headers.
    
    Args:
        base_folder: Base folder containing filter.txt and field.txt
        inventory_path: Path to inventory.csv file
        mode: Operating mode ("single" or "multi") - field.txt only validated in multi mode
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    if not inventory_path.exists():
        errors.append(f"Inventory file not found: {inventory_path}")
        return False, errors
    
    # Read available fields from inventory.csv
    try:
        with open(inventory_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            available_fields = set(reader.fieldnames or [])
            
        if not available_fields:
            errors.append("No headers found in inventory.csv")
            return False, errors
            
        log_and_print("info", f"Available fields in inventory.csv: {', '.join(sorted(available_fields))}")
        
    except Exception as exc:
        errors.append(f"Error reading inventory.csv headers: {exc}")
        return False, errors
    
    # Check filter.txt for field names
    filter_file = base_folder / "filter.txt"
    if filter_file.is_file():
        try:
            filter_content = read_file(filter_file)
            filter_lines = [line.strip() for line in filter_content.splitlines() 
                          if line.strip() and not line.strip().startswith('#')]
            
            # Extract field names from filter conditions
            filter_fields = set()
            for line_num, filter_line in enumerate(filter_lines, 1):
                # Split by commas for AND conditions
                conditions = [condition.strip() for condition in filter_line.split(',')]
                
                for condition in conditions:
                    if not condition:
                        continue
                    
                    # Extract field name from condition (before operator)
                    # Support operators: =~, !~, !=, =
                    field_name = None
                    for op in ['=~', '!~', '!=', '=']:
                        if op in condition:
                            field_name = condition.split(op)[0].strip()
                            break
                    
                    if field_name and field_name not in available_fields:
                        filter_fields.add(field_name)
                        errors.append(f"filter.txt line {line_num}: Field '{field_name}' not found in inventory.csv")
            
            if filter_fields:
                log_and_print("error", f"Invalid fields in filter.txt: {', '.join(sorted(filter_fields))}")
            else:
                log_and_print("info", "All filter.txt field names validated successfully")
                
        except Exception as exc:
            errors.append(f"Error validating filter.txt: {exc}")
    
    # Check field.txt for field names - ONLY in multi mode
    if mode == "multi":
        field_file = base_folder / "field.txt"
        if field_file.is_file():
            try:
                field_content = read_file(field_file)
                field_names = [line.strip() for line in field_content.splitlines() if line.strip()]
                
                invalid_fields = []
                for line_num, field_name in enumerate(field_names, 1):
                    if field_name not in available_fields:
                        invalid_fields.append(field_name)
                        errors.append(f"field.txt line {line_num}: Field '{field_name}' not found in inventory.csv")
                
                if invalid_fields:
                    log_and_print("error", f"Invalid fields in field.txt: {', '.join(invalid_fields)}")
                else:
                    if field_names:  # Only log success if there were field names to validate
                        log_and_print("info", "All field.txt field names validated successfully")
                    
            except Exception as exc:
                errors.append(f"Error validating field.txt: {exc}")
        else:
            log_and_print("info", "No field.txt found (optional for multi mode)")
    # In single mode, field.txt is not validated at all (no logging needed)
    
    # Provide helpful suggestions if there are errors
    if errors:
        log_and_print("info", "Field validation failed. Available fields in inventory.csv:")
        for field in sorted(available_fields):
            log_and_print("info", f"  - {field}")
    
    return len(errors) == 0, errors

def validate_fields_with_priority(base_folder: Path, mode: str = "single") -> Tuple[bool, List[str]]:
    """
    Enhanced field validation with priority-based inventory checking.
    
    Priority rules:
    1. All fields in filter.txt should exist in /notifybot/inventory/inventory.csv
    2. All fields in field.txt should exist in <base-folder>/field-inventory.csv if it exists,
       AND all fields in filter.txt should also exist in <base-folder>/field-inventory.csv
    3. If <base-folder>/field-inventory.csv doesn't exist, then all fields in field.txt 
       should exist in /notifybot/inventory/inventory.csv
    
    Args:
        base_folder: Base folder containing filter.txt and field.txt
        mode: Operating mode ("single" or "multi") - field.txt only validated in multi mode
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check if global inventory exists
    if not INVENTORY_PATH.exists():
        errors.append(f"Global inventory file not found: {INVENTORY_PATH}")
        return False, errors
    
    # Check if local field inventory exists
    local_field_inventory_path = base_folder / "field-inventory.csv"
    has_local_field_inventory = local_field_inventory_path.exists()
    
    # Read available fields from global inventory
    try:
        with open(INVENTORY_PATH, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            # Strip whitespace from field names
            global_available_fields = set(field.strip() for field in (reader.fieldnames or []))
            
        if not global_available_fields:
            errors.append("No headers found in global inventory.csv")
            return False, errors
            
        log_and_print("info", f"Global inventory fields: {', '.join(sorted(global_available_fields))}")
        
    except Exception as exc:
        errors.append(f"Error reading global inventory.csv headers: {exc}")
        return False, errors
    
    # Read available fields from local field inventory if it exists
    local_available_fields = set()
    if has_local_field_inventory:
        try:
            with open(local_field_inventory_path, mode="r", newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                # Strip whitespace from field names - THIS IS THE KEY FIX
                local_available_fields = set(field.strip() for field in (reader.fieldnames or []))
                
            if not local_available_fields:
                errors.append(f"No headers found in local field-inventory.csv")
                return False, errors
                
            log_and_print("info", f"Local field-inventory.csv found with fields: {', '.join(sorted(local_available_fields))}")
            
        except Exception as exc:
            errors.append(f"Error reading local field-inventory.csv headers: {exc}")
            return False, errors
    else:
        log_and_print("info", "No local field-inventory.csv found, using global inventory for field.txt validation")
    
    # RULE 1: Validate filter.txt against global inventory
    filter_file = base_folder / "filter.txt"
    if filter_file.is_file():
        try:
            filter_content = read_file(filter_file)
            filter_lines = [line.strip() for line in filter_content.splitlines() 
                          if line.strip() and not line.strip().startswith('#')]
            
            # Extract field names from filter conditions
            filter_fields = set()
            for line_num, filter_line in enumerate(filter_lines, 1):
                # Split by commas for AND conditions
                conditions = [condition.strip() for condition in filter_line.split(',')]
                
                for condition in conditions:
                    if not condition:
                        continue
                    
                    # Extract field name from condition (before operator)
                    field_name = None
                    for op in ['=~', '!~', '!=', '=']:
                        if op in condition:
                            field_name = condition.split(op)[0].strip()
                            break
                    
                    if field_name:
                        filter_fields.add(field_name)
                        
                        # Check against global inventory
                        if field_name not in global_available_fields:
                            errors.append(f"filter.txt line {line_num}: Field '{field_name}' not found in global inventory.csv")
                        
                        # RULE 2: If local field inventory exists, also check filter fields against it
                        if has_local_field_inventory and field_name not in local_available_fields:
                            errors.append(f"filter.txt line {line_num}: Field '{field_name}' not found in local field-inventory.csv")
            
            if filter_fields:
                if not any(f"Field '{field}' not found" in error for error in errors):
                    log_and_print("info", "All filter.txt field names validated successfully against global inventory")
                    if has_local_field_inventory:
                        if not any("field-inventory.csv" in error for error in errors):
                            log_and_print("info", "All filter.txt field names validated successfully against local field-inventory")
                else:
                    invalid_global = [field for field in filter_fields if field not in global_available_fields]
                    if invalid_global:
                        log_and_print("error", f"Invalid fields in filter.txt (global inventory): {', '.join(sorted(invalid_global))}")
                    
                    if has_local_field_inventory:
                        invalid_local = [field for field in filter_fields if field not in local_available_fields]
                        if invalid_local:
                            log_and_print("error", f"Invalid fields in filter.txt (local field-inventory): {', '.join(sorted(invalid_local))}")
                
        except Exception as exc:
            errors.append(f"Error validating filter.txt: {exc}")
    
    # RULE 2 & 3: Validate field.txt - ONLY in multi mode
    if mode == "multi":
        field_file = base_folder / "field.txt"
        if field_file.is_file():
            try:
                field_content = read_file(field_file)
                field_names = [line.strip() for line in field_content.splitlines() if line.strip()]
                
                if field_names:
                    # Determine which inventory to validate against
                    if has_local_field_inventory:
                        # RULE 2: Use local field inventory for field.txt validation
                        inventory_to_use = local_available_fields
                        inventory_name = "local field-inventory.csv"
                        log_and_print("info", f"Validating field.txt against local field-inventory.csv (priority)")
                    else:
                        # RULE 3: Fallback to global inventory for field.txt validation
                        inventory_to_use = global_available_fields
                        inventory_name = "global inventory.csv"
                        log_and_print("info", f"Validating field.txt against global inventory.csv (fallback)")
                    
                    invalid_fields = []
                    for line_num, field_name in enumerate(field_names, 1):
                        # Strip whitespace from field name from field.txt as well
                        field_name = field_name.strip()
                        if field_name not in inventory_to_use:
                            invalid_fields.append(field_name)
                            errors.append(f"field.txt line {line_num}: Field '{field_name}' not found in {inventory_name}")
                    
                    if invalid_fields:
                        log_and_print("error", f"Invalid fields in field.txt ({inventory_name}): {', '.join(invalid_fields)}")
                    else:
                        log_and_print("info", f"All field.txt field names validated successfully against {inventory_name}")
                else:
                    log_and_print("info", "field.txt is empty - no fields to validate")
                    
            except Exception as exc:
                errors.append(f"Error validating field.txt: {exc}")
        else:
            log_and_print("info", "No field.txt found (optional for multi mode)")
    
    # Provide helpful suggestions if there are errors
    if errors:
        log_and_print("info", "Field validation failed. Available fields:")
        log_and_print("info", f"Global inventory.csv: {', '.join(sorted(global_available_fields))}")
        if has_local_field_inventory:
            log_and_print("info", f"Local field-inventory.csv: {', '.join(sorted(local_available_fields))}")
    
    return len(errors) == 0, errors





def check_required_files(base: Path, required: List[str], dry_run: bool = True, mode: str = "single") -> None:
    """Updated check_required_files function to use the new priority-based validation."""
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        raise MissingRequiredFilesError(f"Missing required files: {', '.join(missing)}")
    
    # Multi mode requires filter.txt
    if mode == "multi":
        if not (base / "filter.txt").is_file():
            raise MissingRequiredFilesError("Multi mode requires filter.txt")
        if not INVENTORY_PATH.is_file():
            raise MissingRequiredFilesError("Multi mode requires inventory.csv at /notifybot/inventory/inventory.csv")
    
    # Single mode requires at least one recipient source (ALWAYS - dry-run or live)
    if mode == "single":
        has_to = (base / "to.txt").is_file()
        has_filters = (base / "filter.txt").is_file() and INVENTORY_PATH.is_file()
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
        is_valid, validation_errors = validate_fields_with_priority(base, mode)
        
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
    Check if a row matches the filter conditions with PromQL-style syntax support.
    Each line in filters represents an OR condition.
    Within each line, comma-separated conditions are AND conditions.
    
    Supported operators:
    - = : Exact match
    - != : Not equal
    - =~ : Regex match  
    - !~ : Regex not match
    - * : Wildcard (fnmatch style)
    - ? : Single character wildcard
    - [seq] : Character class
    - [!seq] : Negated character class
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
        Parse a single condition and return (key, operator, value).
        
        Examples:
        - department="sales" -> ("department", "=", "sales")
        - region!="europe" -> ("region", "!=", "europe")  
        - name=~".*Manager.*" -> ("name", "=~", ".*Manager.*")
        - email!~".*(test|demo).*" -> ("email", "!~", ".*(test|demo).*")
        - status=active* -> ("status", "*", "active*")
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
    Validate filter syntax and optionally check field names against available fields.
    
    Args:
        filters: List of filter conditions
        available_fields: Optional set of available field names for validation
    
    Returns:
        Tuple of (is_valid, error_messages)
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


def print_filter_syntax_help():
    """Print help information about filter syntax."""
    help_text = """
NOTIFYBOT FILTER SYNTAX GUIDE
=============================

Basic Operators:
  =    Exact match (case-insensitive)
  !=   Not equal (case-insensitive)  
  =~   Regex match (case-insensitive)
  !~   Regex not match (case-insensitive)

Wildcard Operators (fnmatch style):
  *    Matches any sequence of characters
  ?    Matches any single character
  [seq] Matches any character in seq
  [!seq] Matches any character not in seq

Logic:
  , (comma)     AND condition within same line
  New line      OR condition between lines
  # (hash)      Comment lines (ignored)

Examples:
  department="sales"                    # Exact match
  region!="europe"                      # Not equal  
  name=~".*Manager.*"                   # Regex match
  email!~".*(test|demo).*"              # Regex not match
  status=active*                        # Wildcard match
  department="sales",region="north"     # AND condition
  department="sales"                    # OR condition
  department="marketing"                # (on separate lines)

Complex Examples:
  # Sales in North America OR Marketing globally
  department="sales",country=~"USA|Canada|Mexico"
  department="marketing"
  
  # All employees except contractors
  name!~".*(Contract|Temp|Intern).*"
  
  # Engineering team in English-speaking countries
  department="engineering",country=~"USA|Canada|UK|Australia"
"""
    print(help_text)
    

def apply_filter_logic(filters: List[str], inventory_path: Path) -> List[str]:
    """
    Apply the enhanced filter logic using PromQL-style syntax with 'filter.txt' and 'inventory.csv'.
    Now includes field validation against inventory headers.
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
        print_filter_syntax_help()
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



def parse_filter_condition(condition: str) -> tuple:
    """
    Parse a single PromQL-style condition and return (key, operator, value).
    
    Examples:
    - department="sales" -> ("department", "=", "sales")
    - region!="europe" -> ("region", "!=", "europe")  
    - name=~".*Manager.*" -> ("name", "=~", ".*Manager.*")
    - email!~".*(test|demo).*" -> ("email", "!~", ".*(test|demo).*")
    - status=active* -> ("status", "*", "active*")
    """
    condition = condition.strip()
    
    # Check for regex operators first (longer patterns)
    if '=~' in condition:
        key, value = condition.split('=~', 1)
        return key.strip(), '=~', value.strip()
    elif '!~' in condition:
        key, value = condition.split('!~', 1)
        return key.strip(), '!~', value.strip()
    elif '!=' in condition:
        key, value = condition.split('!=', 1)
        return key.strip(), '!=', value.strip()
    elif '=' in condition:
        key, value = condition.split('=', 1)
        value = value.strip()
        # Check if value contains wildcards
        if '*' in value or '?' in value or '[' in value:
            return key.strip(), '*', value
        else:
            return key.strip(), '=', value
    else:
        # Simple wildcard search in all values (backward compatibility)
        return None, '*', condition

def get_template_substitution_preview(subject_template: str, body_template: str, 
                                    field_values: Dict[str, str]) -> Dict[str, str]:
    """
    Generate a preview of template substitution for logging/debugging.
    
    Returns:
        Dict with 'subject' and 'body_preview' keys
    """
    preview_subject = substitute_placeholders(subject_template, field_values)
    
    # For body preview, just show first 100 characters with substitutions
    preview_body = substitute_placeholders(body_template, field_values)
    if len(preview_body) > 100:
        preview_body = preview_body[:100] + "..."
    
    return {
        'subject': preview_subject,
        'body_preview': preview_body,
        'substitutions_made': len([k for k, v in field_values.items() if v])
    }
    
    
def test_filter_conditions(filters: List[str], inventory_path: Path, max_examples: int = 5) -> None:
    """
    Test filter conditions and show examples of matched and unmatched rows.
    Useful for debugging filter logic.
    
    Args:
        filters: List of filter conditions
        inventory_path: Path to inventory CSV file
        max_examples: Maximum number of examples to show for each category
    """
    if not inventory_path.exists():
        print(f"Error: Inventory file not found: {inventory_path}")
        return
    
    print("FILTER TESTING MODE")
    print("=" * 50)
    
    # Validate syntax first
    is_valid, errors = validate_filter_syntax(filters)
    if not is_valid:
        print("❌ Filter syntax validation failed:")
        for error in errors:
            print(f"   {error}")
        print()
        print_filter_syntax_help()
        return
    
    print("✅ Filter syntax validation passed")
    print()
    
    # Show active filters
    active_filters = [f.strip() for f in filters if f.strip() and not f.strip().startswith('#')]
    print(f"Active filter conditions ({len(active_filters)}):")
    for i, filter_line in enumerate(active_filters, 1):
        print(f"  {i}. {filter_line}")
    print()
    
    try:
        matched_rows = []
        unmatched_rows = []
        total_rows = 0
        
        with open(inventory_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            
            print(f"Available columns: {', '.join(reader.fieldnames)}")
            print()
            
            for row in reader:
                total_rows += 1
                
                if matches_filter_conditions(row, filters):
                    matched_rows.append(row)
                else:
                    unmatched_rows.append(row)
        
        # Show statistics
        print(f"RESULTS SUMMARY:")
        print(f"  Total rows: {total_rows}")
        print(f"  Matched rows: {len(matched_rows)}")
        print(f"  Unmatched rows: {len(unmatched_rows)}")
        
        if total_rows > 0:
            match_percentage = (len(matched_rows) / total_rows) * 100
            print(f"  Match rate: {match_percentage:.1f}%")
        print()
        
        # Show examples of matched rows
        if matched_rows:
            print(f"✅ MATCHED ROWS (showing up to {max_examples} examples):")
            for i, row in enumerate(matched_rows[:max_examples], 1):
                print(f"  {i}. {dict(row)}")
            if len(matched_rows) > max_examples:
                print(f"  ... and {len(matched_rows) - max_examples} more")
            print()
        else:
            print("❌ NO ROWS MATCHED - Check your filter conditions")
            print()
        
        # Show examples of unmatched rows (helpful for debugging)
        if unmatched_rows and len(matched_rows) < total_rows:
            print(f"❌ UNMATCHED ROWS (showing up to {max_examples} examples):")
            for i, row in enumerate(unmatched_rows[:max_examples], 1):
                print(f"  {i}. {dict(row)}")
            if len(unmatched_rows) > max_examples:
                print(f"  ... and {len(unmatched_rows) - max_examples} more")
            print()
        
        # Show email extraction results
        if matched_rows:
            print("📧 EMAIL EXTRACTION TEST:")
            valid_emails = []
            invalid_emails = []
            
            for row in matched_rows:
                if 'email' in row:
                    email_string = row['email']
                    individual_emails = extract_emails(email_string, ";")
                    
                    for email in individual_emails:
                        if is_valid_email(email):
                            valid_emails.append(email)
                        else:
                            invalid_emails.append(email)
            
            unique_valid_emails = deduplicate_emails(valid_emails)
            
            print(f"  Valid emails found: {len(valid_emails)}")
            print(f"  Unique valid emails: {len(unique_valid_emails)}")
            if invalid_emails:
                print(f"  Invalid emails found: {len(invalid_emails)}")
                for email in invalid_emails[:3]:
                    print(f"    - {email}")
                if len(invalid_emails) > 3:
                    print(f"    ... and {len(invalid_emails) - 3} more")
            
            print(f"  Sample valid emails:")
            for email in unique_valid_emails[:5]:
                print(f"    - {email}")
            if len(unique_valid_emails) > 5:
                print(f"    ... and {len(unique_valid_emails) - 5} more")
        
    except Exception as exc:
        print(f"Error during filter testing: {exc}")

def analyze_inventory_data(inventory_path: Path) -> None:
    """
    Analyze inventory data to help users understand available fields and values.
    """
    if not inventory_path.exists():
        print(f"Error: Inventory file not found: {inventory_path}")
        return
    
    print("INVENTORY DATA ANALYSIS")
    print("=" * 50)
    
    try:
        with open(inventory_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            
            if not reader.fieldnames:
                print("Error: No headers found in CSV file")
                return
            
            print(f"Available columns ({len(reader.fieldnames)}):")
            for col in reader.fieldnames:
                print(f"  - {col}")
            print()
            
            # Analyze data
            field_values = {field: set() for field in reader.fieldnames}
            total_rows = 0
            
            for row in reader:
                total_rows += 1
                for field, value in row.items():
                    if value:  # Only add non-empty values
                        field_values[field].add(str(value).strip())
            
            print(f"Total rows: {total_rows}")
            print()
            
            # Show unique values for each field (limited)
            for field, values in field_values.items():
                unique_count = len(values)
                print(f"{field} ({unique_count} unique values):")
                
                sorted_values = sorted(list(values))
                if unique_count <= 10:
                    # Show all values if 10 or fewer
                    for value in sorted_values:
                        print(f"  - {value}")
                else:
                    # Show first 5 and mention the rest
                    for value in sorted_values[:5]:
                        print(f"  - {value}")
                    print(f"  ... and {unique_count - 5} more")
                print()
            
    except Exception as exc:
        print(f"Error analyzing inventory data: {exc}")
    
def substitute_placeholders(template: str, field_values: Dict[str, str]) -> str:
    """
    Replace placeholders in template with field values.
    ENHANCED: Better handling of comma-separated values and improved formatting.
    
    Args:
        template: Template string with placeholders like "Report for {department}"
        field_values: Dictionary of field_name -> value mappings
    
    Returns:
        Template with placeholders replaced
        
    Examples:
        template: "Sales report for {department} in {region}"
        field_values: {"department": "sales,sales_north", "region": "north,south,east"}
        result: "Sales report for sales and sales_north in north, south, and east"
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
                clean_value = value if value else f"{{{field}}}" # ← HERE'S THE PROBLEM
            
            # Perform the substitution
            result = result.replace(placeholder, clean_value)
            substitutions_made += 1
    
    # Log substitution details if any were made
    if substitutions_made > 0:
        log_and_print("info", f"Template substitution: {substitutions_made} placeholder(s) replaced")
    
    return result




def get_recipients_for_single_mode(base_folder: Path, dry_run: bool) -> Tuple[List[str], List[str], List[str], int, int, int]:
    """
    Get recipients for single mode operation.
    ENHANCED: Now includes proper logging for additional_to.txt merging.
    
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
                        
        elif filter_file_path.is_file() and INVENTORY_PATH.is_file():
            filters = read_file(filter_file_path).splitlines()
            filtered_recipients = apply_filter_logic(filters, INVENTORY_PATH)
            original_recipients = deduplicate_emails(filtered_recipients)
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
        elif filter_file_path.is_file() and INVENTORY_PATH.is_file():
            filters = read_file(filter_file_path).splitlines()
            recipients = apply_filter_logic(filters, INVENTORY_PATH)
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

def extract_field_values_from_matched_rows(filter_line: str, field_names: List[str], inventory_path: Path, base_folder: Path) -> Dict[str, str]:
    """
    Extract ALL unique field values from matched rows in inventory.csv for template substitution.
    Collects all unique values for each field from all rows that match the filter.
    ENHANCED: Now properly uses priority-based inventory selection (local field-inventory.csv first, then global).
    FIXED: Now receives base_folder as parameter for reliable local field-inventory.csv detection.
    
    Args:
        filter_line: Single filter line like "department='sales',region!='europe'" or "department=sales*"
        field_names: List of field names to extract
        inventory_path: Path to global inventory.csv
        base_folder: Base folder path containing potential field-inventory.csv
    
    Returns:
        Dictionary of field_name -> comma_separated_unique_values mappings from all matched rows
    """
    field_values = {}
    
    # Initialize all fields to empty
    for field in field_names:
        field_values[field] = ""
    
    # PRIORITY-BASED INVENTORY SELECTION - FIXED LOGIC
    local_field_inventory_path = base_folder / "field-inventory.csv"
    
    # Priority 1: Check for local field-inventory.csv 
    if local_field_inventory_path.exists():
        actual_inventory_path = local_field_inventory_path
        inventory_source = "local field-inventory.csv"
        log_and_print("info", f"Using local field-inventory.csv for field extraction (priority): {actual_inventory_path}")
    else:
        actual_inventory_path = inventory_path  # Use the global inventory
        inventory_source = "global inventory.csv"
        log_and_print("info", f"Using global inventory.csv for field extraction (fallback): {actual_inventory_path}")
        log_and_print("info", f"Local field-inventory.csv not found at: {local_field_inventory_path}")
    
    if not actual_inventory_path.exists():
        log_and_print("warning", f"Inventory file not found: {actual_inventory_path}")
        return field_values
    
    try:
        # Dictionary to store unique values for each field
        field_unique_values = {field: set() for field in field_names}
        matched_rows_count = 0
        total_rows_processed = 0
        
        with open(actual_inventory_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            
            # Get headers and strip whitespace - CRITICAL FIX
            raw_headers = reader.fieldnames or []
            clean_headers = [header.strip() for header in raw_headers]
            
            # Verify that all requested field names exist in CSV headers
            available_fields = set(clean_headers)
            missing_fields = [field for field in field_names if field not in available_fields]
            if missing_fields:
                log_and_print("warning", f"Fields not found in {inventory_source}: {', '.join(missing_fields)}")
                log_and_print("info", f"Available fields: {', '.join(sorted(available_fields))}")
                log_and_print("info", f"Raw headers from CSV: {raw_headers}")
            
            # Find ALL rows that match this filter and extract their actual field values
            for row in reader:
                total_rows_processed += 1
                
                # Create cleaned row for filter matching (clean keys AND values)
                cleaned_row = {}
                for raw_header, raw_value in row.items():
                    clean_header = raw_header.strip() if raw_header else raw_header
                    clean_value = raw_value.strip() if raw_value else raw_value
                    cleaned_row[clean_header] = clean_value
                
                # Check if this row matches the filter condition
                if matches_filter_conditions(cleaned_row, [filter_line]):
                    matched_rows_count += 1
                    
                    # Extract ACTUAL values from this matched row (not the filter pattern)
                    for field in field_names:
                        if field in cleaned_row:
                            raw_value = cleaned_row[field]
                            if raw_value:  # Only process non-empty values
                                raw_value_str = str(raw_value).strip()
                                if raw_value_str:  # Double-check it's not just whitespace
                                    # Handle comma-separated values within a single CSV cell
                                    if ',' in raw_value_str:
                                        # Split comma-separated values and add each one
                                        for sub_value in raw_value_str.split(','):
                                            clean_sub_value = sub_value.strip()
                                            if clean_sub_value:
                                                field_unique_values[field].add(clean_sub_value)
                                    else:
                                        # Single value in the cell
                                        field_unique_values[field].add(raw_value_str)
                            else:
                                # Handle empty values properly by logging them but not adding to results
                                log_and_print("info", f"Row {total_rows_processed}: Field '{field}' is empty in matched row")
                        else:
                            log_and_print("warning", f"Row {total_rows_processed}: Field '{field}' not found in row columns")
        
        # Convert sets to comma-separated strings, sorted for consistency
        for field in field_names:
            if field_unique_values[field]:
                # Sort values for consistent output
                sorted_values = sorted(list(field_unique_values[field]))
                field_values[field] = ",".join(sorted_values)
            else:
                # Keep empty string for fields with no values (don't set to None)
                field_values[field] = ""
        
        # Enhanced logging with better details
        if matched_rows_count > 0:
            log_and_print("info", f"Field extraction from filter: '{filter_line}' using {inventory_source}")
            log_and_print("info", f"  - Processed {total_rows_processed} total rows")
            log_and_print("info", f"  - Found {matched_rows_count} matching rows")
            
            extracted_fields = []
            for field_name in field_names:
                field_value = field_values.get(field_name, "")
                if field_value:
                    unique_count = len(field_value.split(','))
                    # Show first few values for preview
                    preview_values = field_value.split(',')[:3]
                    preview = ','.join(preview_values)
                    if unique_count > 3:
                        preview += f"...+{unique_count-3} more"
                    extracted_fields.append(f"{field_name}=[{preview}] ({unique_count} unique)")
                else:
                    extracted_fields.append(f"{field_name}=[] (no values found)")
            
            if extracted_fields:
                log_and_print("info", f"  - Extracted: {'; '.join(extracted_fields)}")
            else:
                log_and_print("warning", f"  - No field values extracted despite {matched_rows_count} matched rows")
                
            # Debug logging to help troubleshoot
            log_and_print("info", f"  - Debug: Available clean headers: {', '.join(sorted(available_fields))}")
            log_and_print("info", f"  - Debug: Requested fields: {', '.join(field_names)}")
            
        else:
            log_and_print("warning", f"No rows matched filter for field extraction: {filter_line}")
            log_and_print("info", f"  - Processed {total_rows_processed} total rows from {inventory_source}")
            log_and_print("info", f"  - Available headers: {', '.join(sorted(available_fields))}")
    
    except Exception as exc:
        log_and_print("error", f"Error extracting field values from {inventory_source}: {exc}")
        log_and_print("error", f"Filter: {filter_line}")
        log_and_print("error", f"Fields requested: {field_names}")
        # Additional debug info
        try:
            log_and_print("error", f"Inventory path: {actual_inventory_path}")
            log_and_print("error", f"Inventory exists: {actual_inventory_path.exists()}")
        except:
            pass
    
    return field_values



def get_recipients_for_multi_mode(base_folder: Path, dry_run: bool) -> Tuple[List[Dict], List[str], List[str], int, int, int]:
    """
    Get recipients for multi mode operation.
    ENHANCED: Improved field value extraction with better validation and logging.
    FIXED: Now passes base_folder to extract_field_values_from_matched_rows for proper local field-inventory.csv detection.
    
    Returns:
        (email_configs, final_cc_recipients, final_bcc_recipients, 
         total_original_recipients_count, total_original_cc_count, total_original_bcc_count)
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
        filter_recipients = apply_filter_logic([filter_line], INVENTORY_PATH)
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
            field_values = extract_field_values_from_matched_rows(filter_line, field_names, INVENTORY_PATH, base_folder)
            
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
    Save recipient details for multi-mode operation to provide reference copies.
    Creates individual files for each filter and a summary file.
    
    Args:
        base_folder: Base folder path
        email_configs: List of email configurations from multi-mode
        cc_recipients: List of CC recipients (optional)
        bcc_recipients: List of BCC recipients (optional)
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
                
                # Add to summary
                filter_summaries.append({
                    'filter_number': i,
                    'filter_line': filter_line,
                    'filename': filter_file.name,
                    'recipient_count': len(recipients),
                    'field_values': field_values
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
                    if summary['field_values']:
                        f.write(f"  Field Values: {summary['field_values']}\n")
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
        
        # Log summary of what was saved
        log_and_print("backup", f"Multi-mode recipients saved to {recipients_folder.name}/")
        log_and_print("info", f"Created {len(filter_summaries)} filter files, 1 summary file, 1 consolidated file")
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

def get_inventory_fields_for_help() -> str:
    """
    Get available fields from inventory.csv for CLI help display.
    Returns a formatted string of available fields or error message.
    """
    try:
        if not INVENTORY_PATH.exists():
            return "  [Inventory file not found at /notifybot/inventory/inventory.csv]"
        
        with open(INVENTORY_PATH, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            available_fields = reader.fieldnames or []
            
        if not available_fields:
            return "  [No headers found in inventory.csv]"
        
        # Format fields in a nice column layout
        field_list = sorted(available_fields)
        formatted_fields = []
        
        # Group fields in rows of 4 for better readability
        for i in range(0, len(field_list), 4):
            row_fields = field_list[i:i+4]
            formatted_row = "  " + " | ".join(f"{field:<15}" for field in row_fields)
            formatted_fields.append(formatted_row)
        
        result = f"  Available fields in inventory.csv ({len(field_list)} total):\n"
        result += "\n".join(formatted_fields)
        return result
        
    except Exception as exc:
        return f"  [Error reading inventory.csv: {exc}]"



def main():
    """Enhanced main function with single/multi mode support and signature functionality"""
    
    # Get inventory fields for help text
    inventory_fields_help = get_inventory_fields_for_help()
    
    parser = argparse.ArgumentParser(
        description="Send batch emails with single/multi mode support and signature.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
PRECHECK REQUIREMENTS:
======================

SINGLE MODE Requirements:
  Required files: subject.txt, body.html, from.txt, approver.txt
  Recipient sources (at least ONE required):
    - to.txt (direct recipient list)
    - filter.txt + inventory.csv (filtered recipients)
    - additional_to.txt (additional recipients)
    - cc.txt (CC recipients)
    - bcc.txt (BCC recipients)
  Optional files: cc.txt, bcc.txt, field.txt, mode.txt
  Optional folders: attachment/, images/

MULTI MODE Requirements:
  Required files: subject.txt, body.html, from.txt, approver.txt, filter.txt
  Optional files: field.txt, cc.txt, bcc.txt, additional_to.txt, mode.txt
  Optional folders: attachment/, images/

INVENTORY FIELDS & VALIDATION:
==============================

Priority-based Field Validation:
  1. filter.txt fields → validated against /notifybot/inventory/inventory.csv (ALWAYS)
  2. field.txt fields → validated with priority system:
     - If <base-folder>/field-inventory.csv exists: use it for field.txt validation
     - If local field-inventory.csv exists: filter.txt fields ALSO validated against it
     - If no local field-inventory.csv: field.txt validated against global inventory.csv

Global Inventory Location: /notifybot/inventory/inventory.csv
Local Field Inventory: <base-folder>/field-inventory.csv (optional)

{inventory_fields_help}

Field Validation Rules:
  - All field names in filter.txt must exist in global inventory.csv headers
  - If local field-inventory.csv exists: filter.txt fields must also exist there
  - field.txt validation priority: local field-inventory.csv > global inventory.csv
  - Filter syntax supports: =, !=, =~, !~, wildcards (*, ?, [])

FILTER SYNTAX EXAMPLES:
=======================
  department="sales"                    # Exact match
  region!="europe"                      # Not equal  
  name=~".*Manager.*"                   # Regex match
  email!~".*(test|demo).*"              # Regex not match
  status=active*                        # Wildcard match
  department="sales",region="north"     # AND condition
  department="sales"                    # OR condition
  department="marketing"                # (on separate lines)

File Locations:
  - Base folder: /notifybot/basefolder/<your-folder>/
  - Global inventory: /notifybot/inventory/inventory.csv
  - Local field inventory: /notifybot/basefolder/<your-folder>/field-inventory.csv (optional)
  - Logs: /notifybot/logs/notifybot.log

Examples:
  python notifybot.py --base-folder email --dry-run
  python notifybot.py --base-folder email --force --mode single
  python notifybot.py --base-folder email --batch-size 300 --delay 10 --mode multi
        """
    )
    
    # Updated argument with clearer help text
    parser.add_argument("--base-folder", 
                       required=True, 
                       metavar="BASE_FOLDER",
                       help="Base folder name inside /notifybot/basefolder/ [REQUIRED]")
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
