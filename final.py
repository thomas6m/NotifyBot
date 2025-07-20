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
    --dry-run             Simulate sending emails without SMTP.
    --batch-size          Number of emails to send per batch (default: 500).
    --delay               Delay in seconds between batches (default: 5.0).
    --force               Skip confirmation prompt (for automation).
"""

import argparse
import csv
import logging
import mimetypes
import re
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
from typing import List, Tuple, Dict, Set
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
    timestamp_epoch = int(time.time())  # Epoch timestamp
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
            "confirmation": "✋"
        }

        # Get emoji for level
        emoji = emoji_mapping.get(level.lower(), "")
        csv_log = csv_log_entry(f"{emoji} {message}")
        log_func = getattr(logging, level.lower(), logging.info)
        log_func(csv_log)
        print(f"{csv_log}")  # Print to the console as well

    globals()['log_and_print'] = log_and_print

def rotate_log_file() -> None:
    """Rotate current log file with a timestamp suffix."""
    log_path = LOG_FILENAME
    if log_path.is_file():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated = log_path.with_name(f"notifybot_{timestamp}.log")
        try:
            log_path.rename(rotated)
            log_and_print("info", f"Log file rotated: {rotated.name}")
        except Exception as exc:
            log_and_print("error", f"Failed to rotate log file: {exc}")

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
    """Write recipients list to a file, one per line."""
    try:
        with path.open('w', encoding='utf-8') as f:
            for email in recipients:
                f.write(f"{email}\n")
        log_and_print("file", f"Written {len(recipients)} recipients to {path.name}")
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
                        from_address: str, attachment_folder: Path = None) -> MIMEMultipart:
    """Create a properly formatted email message with attachments."""
    # Create multipart message
    msg = MIMEMultipart('mixed')
    msg['From'] = from_address
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = subject
    
    # Add HTML body
    html_part = MIMEText(body_html, 'html', 'utf-8')
    msg.attach(html_part)
    
    # Add attachments if folder exists
    add_attachments(msg, attachment_folder)
    
    return msg

def send_via_sendmail(recipients: List[str], subject: str, body_html: str, 
                     from_address: str, attachment_folder: Path = None, 
                     dry_run: bool = False) -> bool:
    """Send email using sendmail command."""
    if dry_run:
        log_and_print("info", f"Dry run: Would send email to {len(recipients)} recipients")
        log_and_print("info", f"Subject: {subject}")
        log_and_print("info", f"From: {from_address}")
        log_and_print("info", f"To: {', '.join(recipients[:3])}{'...' if len(recipients) > 3 else ''}")
        if attachment_folder and attachment_folder.exists():
            attachments = [f.name for f in attachment_folder.iterdir() if f.is_file()]
            if attachments:
                log_and_print("info", f"Attachments: {', '.join(attachments[:3])}{'...' if len(attachments) > 3 else ''}")
        return True
    
    try:
        # Create the email message
        msg = create_email_message(recipients, subject, body_html, from_address, attachment_folder)
        
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
                    delay: float = 5.0, attachment_folder: Path = None) -> None:
    """Send emails in batches with a delay between batches."""
    total_recipients = len(recipients)
    successful_batches = 0
    failed_batches = 0
    
    log_and_print("processing", f"Starting batch email send: {total_recipients} total recipients")
    
    for i in range(0, total_recipients, batch_size):
        batch = recipients[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total_recipients + batch_size - 1) // batch_size
        
        log_and_print("processing", f"Processing batch {batch_num}/{total_batches} ({len(batch)} recipients)")
        
        # Send current batch
        if send_via_sendmail(batch, subject, body_html, from_address, attachment_folder, dry_run):
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
    log_and_print("info", f"Batch processing complete: {successful_batches} successful, {failed_batches} failed")

def send_email(recipients: List[str], subject: str, body_html: str, 
              from_address: str, dry_run: bool = False) -> None:
    """Send an email to a batch of recipients using sendmail."""
    # This function is kept for backward compatibility but routing to sendmail
    attachment_folder = None  # Will be set properly in the main function
    send_via_sendmail(recipients, subject, body_html, from_address, attachment_folder, dry_run)

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
                # Basic filter implementation - customize based on your needs
                if matches_filter_conditions(row, filters):
                    if 'email' in row and is_valid_email(row['email']):
                        filtered_recipients.append(row["email"])
                    else:
                        log_and_print("warning", f"Row missing valid email: {row}")
        
        log_and_print("info", f"Filter applied: {len(filtered_recipients)} recipients selected from inventory")
        
    except Exception as exc:
        log_and_print("error", f"Error applying filter logic: {exc}")
    
    return filtered_recipients

def matches_filter_conditions(row: Dict, filters: List[str]) -> bool:
    """Check if a row matches the filter conditions."""
    # Example implementation - customize based on your filter requirements
    for filter_condition in filters:
        filter_condition = filter_condition.strip()
        if not filter_condition or filter_condition.startswith('#'):
            continue  # Skip empty lines and comments
        
        # Simple key=value filter format
        if '=' in filter_condition:
            key, value = filter_condition.split('=', 1)
            key, value = key.strip(), value.strip()
            
            if key in row and str(row[key]).lower() == value.lower():
                continue  # This condition matches
            else:
                return False  # This condition doesn't match
        else:
            # Simple substring search in all values
            if any(filter_condition.lower() in str(v).lower() for v in row.values()):
                continue
            else:
                return False
    
    return True  # All conditions matched

def prompt_for_confirmation() -> bool:
    """Prompt the user for a yes/no confirmation to proceed."""
    response = input("Do you want to proceed with sending emails? (yes/no): ").strip().lower()
    return response == 'yes'

def main():
    parser = argparse.ArgumentParser(description="Send batch emails with attachments.")
    parser.add_argument("--base-folder", required=True, help="Base folder name inside /notifybot/basefolder.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate sending emails.")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt.")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of emails per batch (default: 500).")
    parser.add_argument("--delay", type=float, default=5.0, help="Delay in seconds between batches (default: 5.0).")
    
    args = parser.parse_args()
    
    setup_logging()
    rotate_log_file()  # Rotate log at start of each run
    
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
        
        # Determine recipients based on available sources
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
            additional_recipients = []
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
        
        # Fallback for dry-run mode
        else:
            if args.dry_run and approver_emails:
                recipients = approver_emails
                log_and_print("info", f"Using approver emails for dry-run: {len(recipients)} recipients")
            else:
                log_and_print("error", "No valid recipient source found")
                sys.exit(1)
        
        if not recipients:
            log_and_print("error", "No valid recipients found")
            sys.exit(1)
        
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
        log_and_print("confirmation", f"Recipients: {len(recipients)}")
        log_and_print("confirmation", f"Batch size: {args.batch_size}")
        log_and_print("confirmation", f"Delay: {args.delay}s")
        log_and_print("confirmation", f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
        
        # Confirmation prompt unless --force
        if not args.force:
            if not prompt_for_confirmation():
                log_and_print("info", "Email sending aborted by user.")
                sys.exit(0)
        
        # Send emails in batches
        send_email_batch(
            recipients, 
            subject, 
            body_html, 
            from_address, 
            args.batch_size, 
            dry_run=args.dry_run, 
            delay=args.delay,
            attachment_folder=attachment_folder
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

if __name__ == "__main__":
    main()
