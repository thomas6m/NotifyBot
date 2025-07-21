#!/usr/bin/env python3
"""
NotifyBot: Automated email batch sender with filtering, logging, and dry-run support.

Usage:
    python notifybot.py --base-folder emails --dry-run
    python notifybot.py --base-folder emails --force
    python notifybot.py --base-folder emails --batch-size 500 --delay 5.0

CLI Options:
    --base-folder         Base directory containing email input files [REQUIRED]. 
                          The directory should be inside /notifybot/basefolder.
                          Required files inside base folder:
                            - subject.txt       (email subject)
                            - body.html         (email body)
                            - from.txt          (email From address)
                            - approver.txt      (approver emails for dry-run)
                          Recipient source (at least one required for real email mode):
                            - to.txt                    List of recipient emails
                            - filter.txt + inventory.csv   Filter-based recipient extraction
                            - additional_to.txt         Additional emails (merged with filter results)
    --dry-run             Simulate sending emails without SMTP. Sends only to approvers with DRAFT prefix.
    --batch-size          Number of emails to send per batch (default: 500).
    --delay               Delay in seconds between batches (default: 5.0).
    --force               Skip confirmation prompt (for automation).
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
    """Generate log entry in CSV format."""
    timestamp_epoch = time.time_ns() // 1_000_000  # Nanoseconds to milliseconds
    try:
        username = os.getlogin()  # Get the username of the executor
    except OSError:
        # Fallback for environments where getlogin() fails
        username = os.getenv('USER', os.getenv('USERNAME', 'unknown'))
    return f"{timestamp_epoch},{username},{message}"

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
            "draft": "📝"
        }

        # Get emoji for level
        emoji = emoji_mapping.get(level.lower(), "")
        csv_log = csv_log_entry(f"{emoji} {message}")
        log_func = getattr(logging, level.lower(), logging.info)
        log_func(csv_log)
        print(f"{csv_log}")  # Print to the console as well

    globals()['log_and_print'] = log_and_print

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

def write_recipients_to_file(path: Path, recipients: List[str]) -> None:
    """Write recipients list to a file, one per line, with deduplication."""
    try:
        # Deduplicate recipients (case-insensitive)
        seen = set()
        unique_recipients = []
        for email in recipients:
            email_lower = email.lower()
            if email_lower not in seen:
                seen.add(email_lower)
                unique_recipients.append(email)
        
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
    # Use a set to track seen emails (case-insensitive)
    seen = set()
    merged = []
    
    # Add base recipients first
    for email in base_recipients:
        email_lower = email.lower()
        if email_lower not in seen:
            seen.add(email_lower)
            merged.append(email)
    
    # Add additional recipients
    for email in additional_recipients:
        email_lower = email.lower()
        if email_lower not in seen:
            seen.add(email_lower)
            merged.append(email)
    
    return merged

def deduplicate_file(path: Path) -> None:
    """Back up and deduplicate a file's lines."""
    if not path.is_file():
        return
    try:
        backup = path.with_name(f"{path.stem}_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}")
        shutil.copy2(path, backup)
        log_and_print("backup", f"💾 Backup created: {backup.name}")
        
        unique, seen = [], set()
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and line not in seen:
                seen.add(line)
                unique.append(line)
        
        path.write_text("\n".join(unique) + "\n", encoding="utf-8")
        log_and_print("info", f"Deduplicated {path.name}")
    except Exception as exc:
        log_and_print("error", f"Error during file deduplication for {path}: {exc}")

def check_required_files(base: Path, required: List[str], dry_run: bool = True) -> None:
    """Ensure required files exist. In real mode, ensure valid recipient source."""
    missing = [f for f in required if not (base / f).is_file()]
    if missing:
        raise MissingRequiredFilesError(f"Missing required files: {', '.join(missing)}")
    
    if not dry_run:
        has_to = (base / "to.txt").is_file()
        has_filters = (base / "filter.txt").is_file() and INVENTORY_PATH.is_file()
        has_additional = (base / "additional_to.txt").is_file()
        
        if not (has_to or has_filters or has_additional):
            raise MissingRequiredFilesError(
                "Missing recipient source: Provide at least one of 'to.txt', 'filter.txt + inventory.csv', or 'additional_to.txt'."
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
                        base_folder: Path = None) -> MIMEMultipart:
    """Create a properly formatted email message with embedded images and attachments."""
    
    # Embed images if base_folder is provided
    embedded_images = []
    if base_folder:
        body_html, embedded_images = embed_images_in_html(body_html, base_folder)
    
    # Create multipart message - CHANGED from 'mixed' to 'related' for embedded images
    if embedded_images:
        msg = MIMEMultipart('related')  # Use 'related' when we have embedded images
    else:
        msg = MIMEMultipart('mixed')    # Use 'mixed' for attachments only
    
    msg['From'] = from_address
    msg['To'] = ', '.join(recipients)
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
    Check if a row matches the filter conditions.
    Each line in filters represents an OR condition.
    Within each line, comma-separated conditions are AND conditions.
    
    Example filter:
        department=sales,status=active
        department=marketing,region=west
        role=manager
    
    Logic: (sales AND active) OR (marketing AND west) OR (manager)
    """
    if not filters:
        return True  # No filters means include all
    
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
                # Key=value format
                key, value = condition.split('=', 1)
                key, value = key.strip(), value.strip()
                
                if key not in row or str(row[key]).lower() != value.lower():
                    line_matches = False
                    break  # This AND condition failed, so the entire line fails
            else:
                # Simple substring search in all values
                if not any(condition.lower() in str(v).lower() for v in row.values()):
                    line_matches = False
                    break  # This AND condition failed, so the entire line fails
        
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
        
        log_and_print("info", f"Filter applied: {len(filtered_recipients)} recipients selected from inventory")
        
    except Exception as exc:
        log_and_print("error", f"Error applying filter logic: {exc}")
    
    return filtered_recipients

def prompt_for_confirmation() -> bool:
    """Prompt the user for a yes/no confirmation to proceed."""
    response = input("Do you want to proceed with sending emails? (yes/no): ").strip().lower()
    return response == 'yes'

def send_via_sendmail(recipients: List[str], subject: str, body_html: str, 
                     from_address: str, attachment_folder: Path = None, 
                     dry_run: bool = False, original_recipients_count: int = 0,
                     base_folder: Path = None) -> bool:  # ADD base_folder parameter
    """Send email using sendmail command. In dry-run mode, sends only to approvers with DRAFT prefix."""
    
    # ... keep all your existing code until the try block ...
    # [All the existing subject preparation and logging code stays the same]
    
    # Prepare subject for dry-run mode
    final_subject = subject
    if dry_run:
        # Add DRAFT prefix if not already present
        if not subject.upper().startswith('DRAFT'):
            final_subject = f"DRAFT - {subject}"
        
        # Add recipient count info to body for dry-run
        draft_info = f"""
        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 20px 0; border-radius: 5px;">
            <h3 style="color: #856404; margin: 0 0 10px 0;">📝 DRAFT MODE - FOR APPROVAL ONLY</h3>
            <p style="color: #856404; margin: 5px 0;"><strong>Original Recipients Count:</strong> {original_recipients_count}</p>
            <p style="color: #856404; margin: 5px 0;"><strong>This email is being sent to approvers for review.</strong></p>
            <p style="color: #856404; margin: 5px 0;">When approved, it will be sent to all {original_recipients_count} intended recipients.</p>
        </div>
        <hr style="margin: 20px 0;">
        """
        body_html = draft_info + body_html
        
        log_and_print("draft", f"DRAFT mode: Sending to {len(recipients)} approver(s) instead of {original_recipients_count} original recipients")
        log_and_print("draft", f"Subject: {final_subject}")
        log_and_print("draft", f"Approvers: {', '.join(recipients[:3])}{'...' if len(recipients) > 3 else ''}")
        if attachment_folder and attachment_folder.exists():
            attachments = [f.name for f in attachment_folder.iterdir() if f.is_file()]
            if attachments:
                log_and_print("draft", f"Attachments: {', '.join(attachments[:3])}{'...' if len(attachments) > 3 else ''}")
    else:
        log_and_print("info", f"LIVE mode: Sending to {len(recipients)} recipients")
        log_and_print("info", f"Subject: {final_subject}")
        log_and_print("info", f"To: {', '.join(recipients[:3])}{'...' if len(recipients) > 3 else ''}")
        if attachment_folder and attachment_folder.exists():
            attachments = [f.name for f in attachment_folder.iterdir() if f.is_file()]
            if attachments:
                log_and_print("info", f"Attachments: {', '.join(attachments[:3])}{'...' if len(attachments) > 3 else ''}")
    
    try:
        # MODIFIED: Create the email message with base_folder for image embedding
        msg = create_email_message(recipients, final_subject, body_html, from_address, 
                                 attachment_folder, base_folder)
        
        # ... keep all the rest of your existing sendmail code unchanged ...
        
        # Convert message to string
        email_content = msg.as_string()
        
        # Find sendmail path
        sendmail_path = find_sendmail_path()
        
        # Call sendmail with proper arguments
        sendmail_cmd = [sendmail_path, '-t', '-f', from_address] + recipients
        
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
                log_and_print("success", f"Email sent successfully to {len(recipients)} recipients")
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
def send_email_batch(recipients: List[str], subject: str, body_html: str, 
                    from_address: str, batch_size: int, dry_run: bool = False, 
                    delay: float = 5.0, attachment_folder: Path = None,
                    original_recipients_count: int = 0, base_folder: Path = None) -> None:  # ADD base_folder
    """Send emails in batches with a delay between batches."""
    total_recipients = len(recipients)
    successful_batches = 0
    failed_batches = 0
    
    if dry_run:
        log_and_print("processing", f"Starting DRAFT email send to approvers: {total_recipients} approver(s)")
        log_and_print("processing", f"Original campaign would target: {original_recipients_count} recipients")
    else:
        log_and_print("processing", f"Starting batch email send: {total_recipients} total recipients")
    
    for i in range(0, total_recipients, batch_size):
        batch = recipients[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total_recipients + batch_size - 1) // batch_size
        
        if dry_run:
            log_and_print("processing", f"Processing DRAFT batch {batch_num}/{total_batches} ({len(batch)} approver(s))")
        else:
            log_and_print("processing", f"Processing batch {batch_num}/{total_batches} ({len(batch)} recipients)")
        
        # MODIFIED: Send current batch with base_folder
        if send_via_sendmail(batch, subject, body_html, from_address, attachment_folder, 
                           dry_run, original_recipients_count, base_folder):  # ADD base_folder
            successful_batches += 1
            if dry_run:
                log_and_print("success", f"DRAFT batch {batch_num} completed successfully")
            else:
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
        log_and_print("info", f"DRAFT processing complete: {successful_batches} successful, {failed_batches} failed")
        log_and_print("info", f"DRAFT emails sent to approvers for campaign targeting {original_recipients_count} recipients")
    else:
        log_and_print("info", f"Batch processing complete: {successful_batches} successful, {failed_batches} failed")


def send_email(recipients: List[str], subject: str, body_html: str, 
              from_address: str, dry_run: bool = False) -> None:
    """Send an email to a batch of recipients using sendmail."""
    # This function is kept for backward compatibility but routing to sendmail
    attachment_folder = None  # Will be set properly in the main function
    original_count = len(recipients) if not dry_run else 0
    send_via_sendmail(recipients, subject, body_html, from_address, attachment_folder, dry_run, original_count)
	
def main():
    parser = argparse.ArgumentParser(description="Send batch emails with attachments.")
    parser.add_argument("--base-folder", required=True, help="Base folder name inside /notifybot/basefolder.")
    parser.add_argument("--dry-run", action="store_true", help="Send emails only to approvers with DRAFT prefix.")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt.")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of emails per batch (default: 500).")
    parser.add_argument("--delay", type=float, default=5.0, help="Delay in seconds between batches (default: 5.0).")
    
    args = parser.parse_args()
    
    setup_logging()
    
    try:
        base_folder = validate_base_folder(args.base_folder)
        
        # Check required files based on mode
        required_files = ["subject.txt", "body.html", "from.txt", "approver.txt"]
        check_required_files(base_folder, required_files, args.dry_run)
        
        # Read email content
        subject = read_file(base_folder / "subject.txt")
        body_html = read_file(base_folder / "body.html")
        from_address = read_file(base_folder / "from.txt")
        approver_emails = read_recipients(base_folder / "approver.txt")
        
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
        if not approver_emails:
            log_and_print("error", "No valid approver emails found in approver.txt")
            sys.exit(1)
        
        # Determine recipients based on mode
        final_recipients = []
        original_recipients_count = 0
        
        if args.dry_run:
            # In dry-run mode, we only send to approvers but still need to count original recipients
            final_recipients = approver_emails
            
            # Count what would be the original recipients for display purposes
            original_recipients = []
            to_file_path = base_folder / "to.txt"
            additional_to_file_path = base_folder / "additional_to.txt"
            filter_file_path = base_folder / "filter.txt"
            
            # Try to determine original recipient count for dry-run information
            if to_file_path.is_file():
                original_recipients = read_recipients(to_file_path)
                log_and_print("info", f"Found {len(original_recipients)} recipients in to.txt (for count reference)")
                
                if additional_to_file_path.is_file():
                    additional_recipients = read_recipients(additional_to_file_path)
                    if additional_recipients:
                        original_recipients = merge_recipients(original_recipients, additional_recipients)
                        log_and_print("info", f"Would merge with {len(additional_recipients)} additional recipients")
            
            elif filter_file_path.is_file() and INVENTORY_PATH.is_file():
                filters = read_file(filter_file_path).splitlines()
                original_recipients = apply_filter_logic(filters, INVENTORY_PATH)
                log_and_print("info", f"Filter logic would select {len(original_recipients)} recipients (for count reference)")
                
                if additional_to_file_path.is_file():
                    additional_recipients = read_recipients(additional_to_file_path)
                    if additional_recipients:
                        original_recipients = merge_recipients(original_recipients, additional_recipients)
                        log_and_print("info", f"Would merge with {len(additional_recipients)} additional recipients")
                # 🚨 ADD THESE LINES:
                if original_recipients and not to_file_path.is_file():
                    write_recipients_to_file(to_file_path, original_recipients)
                    log_and_print("file", f"DRY-RUN: Created to.txt with {len(original_recipients)} recipients from filter logic")
            
            
            elif additional_to_file_path.is_file():
                original_recipients = read_recipients(additional_to_file_path)
                log_and_print("info", f"Found {len(original_recipients)} recipients in additional_to.txt (for count reference)")
                
                # 🚨 ADD THESE LINES:
                if original_recipients and not to_file_path.is_file():
                    write_recipients_to_file(to_file_path, original_recipients)
                    log_and_print("file", f"DRY-RUN: Created to.txt from additional_to.txt with {len(original_recipients)} recipients")
                
            original_recipients_count = len(original_recipients)
            log_and_print("draft", f"DRY-RUN MODE: Will send to {len(final_recipients)} approvers instead of {original_recipients_count} actual recipients")
            
        else:
            # Live mode - determine actual recipients
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
                log_and_print("error", "No valid recipient source found")
                sys.exit(1)
            
            if not recipients:
                log_and_print("error", "No valid recipients found")
                sys.exit(1)
            
            final_recipients = recipients
            original_recipients_count = len(recipients)
        
        # Set up attachment folder
        attachment_folder = base_folder / "attachment"
        if attachment_folder.exists():
            attachment_count = len([f for f in attachment_folder.iterdir() if f.is_file()])
            log_and_print("info", f"Found {attachment_count} attachment(s) in {attachment_folder}")
        else:
            attachment_folder = None
            log_and_print("info", "No attachment folder found")
        
        # Show summary
        log_and_print("confirmation", f"Email Summary:")
        log_and_print("confirmation", f"From: {from_address}")
        log_and_print("confirmation", f"Subject: {subject}")
        if args.dry_run:
            log_and_print("confirmation", f"Mode: DRY-RUN (DRAFT emails to approvers)")
            log_and_print("confirmation", f"Approvers: {len(final_recipients)}")
            log_and_print("confirmation", f"Original campaign would target: {original_recipients_count} recipients")
        else:
            log_and_print("confirmation", f"Mode: LIVE")
            log_and_print("confirmation", f"Recipients: {len(final_recipients)}")
        log_and_print("confirmation", f"Batch size: {args.batch_size}")
        log_and_print("confirmation", f"Delay: {args.delay}s")
        
        # Confirmation prompt unless --force
        if not args.force:
            if not prompt_for_confirmation():
                log_and_print("info", "Email sending aborted by user.")
                sys.exit(0)
        
        # Send emails in batches
        send_email_batch(
            final_recipients, 
            subject, 
            body_html, 
            from_address, 
            args.batch_size, 
            dry_run=args.dry_run, 
            delay=args.delay,
            attachment_folder=attachment_folder,
            original_recipients_count=original_recipients_count
            base_folder=base_folder
        )
        
        log_and_print("success", "NotifyBot execution completed successfully")
        
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


def embed_images_in_html(html_content: str, base_folder: Path) -> Tuple[str, List[MIMEImage]]:
    """
    Replace image src attributes with cid references and return embedded images.
    
    Args:
        html_content: HTML content with image tags
        base_folder: Base folder containing images subfolder
    
    Returns:
        Tuple of (modified_html, list_of_mime_images)
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

if __name__ == "__main__":
    main()
