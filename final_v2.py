import csv
import logging
import time
import sys
import traceback
from pathlib import Path
from typing import List, Dict
import subprocess
import argparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def log_and_print(level, message):
    levels = {"info": logging.info, "error": logging.error, "warning": logging.warning, "success": logging.info}
    levels.get(level, logging.info)(message)

def is_valid_email(email):
    """Check if an email is valid (basic check)."""
    return "@" in email

def read_recipients(file_path: Path) -> list:
    """Reads recipients from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        log_and_print("error", f"File not found: {file_path}")
        return []

def read_filter_csv(filter_csv_path: Path) -> list:
    """Reads filter.csv and returns a list of AND conditions for each OR condition row."""
    filters = []
    
    if not filter_csv_path.exists():
        log_and_print("error", f"Filter file not found: {filter_csv_path}")
        return filters
    
    try:
        with open(filter_csv_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                # Each line is a set of AND conditions, so we split by commas
                filters.append([condition.strip() for condition in row])
        
        log_and_print("info", f"Loaded {len(filters)} OR conditions from {filter_csv_path}")
        
    except Exception as exc:
        log_and_print("error", f"Error reading filter file: {exc}")
    
    return filters

def apply_filter_logic(filters: list, inventory_path: Path) -> list:
    """Apply the filter logic using 'filter.csv' and 'inventory.csv'."""
    filtered_recipients = []
    
    if not inventory_path.exists():
        log_and_print("error", f"Inventory file not found: {inventory_path}")
        return filtered_recipients
    
    try:
        with open(inventory_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                # Check if the row matches any filter condition (OR condition)
                if matches_filter_conditions(row, filters):
                    if 'email' in row and is_valid_email(row['email']):
                        filtered_recipients.append(row["email"])
                    else:
                        log_and_print("warning", f"Row missing valid email: {row}")
        
        log_and_print("info", f"Filter applied: {len(filtered_recipients)} recipients selected from inventory")
        
    except Exception as exc:
        log_and_print("error", f"Error applying filter logic: {exc}")
    
    return filtered_recipients

def matches_filter_conditions(row: dict, filters: list) -> bool:
    """Check if a row matches any filter conditions (OR condition)."""
    for filter_condition in filters:
        # filter_condition is a list of key=value conditions (AND conditions)
        match = True
        for condition in filter_condition:
            key, value = condition.split('=', 1)
            key, value = key.strip(), value.strip()

            if key in row and str(row[key]).lower() == value.lower():
                continue
            else:
                match = False
                break
        
        if match:
            return True  # If any row satisfies a filter (OR logic)
    
    return False  # If no row satisfies any filter (OR logic)

def create_email_message(recipients: List[str], subject: str, body_html: str, from_address: str, attachment_folder: Path = None):
    """Create a properly formatted email message with attachments."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    # Create multipart message
    msg = MIMEMultipart('mixed')
    msg['From'] = from_address
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = subject
    
    # Add HTML body
    html_part = MIMEText(body_html, 'html', 'utf-8')
    msg.attach(html_part)
    
    # Add attachments if folder exists
    if attachment_folder and attachment_folder.exists():
        add_attachments(msg, attachment_folder)
    
    return msg

def send_via_sendmail(recipients: List[str], subject: str, body_html: str, from_address: str, attachment_folder: Path = None, dry_run: bool = False):
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
        log_and_print("error", f"Sendmail not found. Please install sendmail.")
        return False
    except subprocess.TimeoutExpired:
        log_and_print("error", "Sendmail timeout - operation took too long")
        return False
    except Exception as exc:
        log_and_print("error", f"Error sending email via sendmail: {exc}")
        return False

def send_email_batch(recipients: List[str], subject: str, body_html: str, from_address: str, batch_size: int, dry_run: bool = False, delay: float = 5.0, attachment_folder: Path = None):
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
    parser.add_argument("--delay", type=float, default=5.0, help="Delay between batches in seconds (default: 5.0).")
    args = parser.parse_args()

    base_folder = Path(f"/notifybot/{args.base_folder}")
    inventory_path = base_folder / "inventory.csv"
    filter_csv_path = base_folder / "filter.csv"
    
    # Load the filter conditions
    filters = read_filter_csv(filter_csv_path)
    if not filters:
        log_and_print("error", "No valid filters found. Exiting.")
        sys.exit(1)
    
    # Apply the filter to inventory
    recipients = apply_filter_logic(filters, inventory_path)
    
    if not recipients:
        log_and_print("error", "No recipients found after applying filters. Exiting.")
        sys.exit(1)
    
    # Email details
    subject = "Test Email"
    body_html = "<html><body><h1>Hello, this is a test email!</h1></body></html>"
    from_address = "sender@example.com"
    
    # Confirm and send emails
    if not args.force and not prompt_for_confirmation():
        log_and_print("info", "Email sending cancelled by user.")
        sys.exit(0)
    
    send_email_batch(recipients, subject, body_html, from_address, args.batch_size, args.dry_run, args.delay)

if __name__ == "__main__":
    main()
