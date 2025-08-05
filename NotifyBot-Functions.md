# NotifyBot Functions List

## Core Functions

### 1. **validate_fields_against_inventory(base_folder, inventory_path, mode="single")**
- Validates field names in filter.txt and field.txt against inventory.csv headers
- Returns tuple of (is_valid, error_messages)

### 2. **validate_fields_with_priority(base_folder, mode="single")**
- Enhanced field validation with priority-based inventory checking
- Checks local field-inventory.csv first, then falls back to global inventory.csv

### 3. **check_required_files(base, required, dry_run=True, mode="single")**
- Checks for required files and validates field names
- Uses priority-based validation system

### 4. **validate_base_folder(base_folder)**
- Ensures base folder is a valid relative path inside /notifybot/basefolder
- Returns validated Path object

## Logging Functions

### 5. **csv_log_entry(message)**
- Generates log entry in CSV format with proper escaping
- Includes timestamp and username

### 6. **setup_logging()**
- Configures logging to INFO+ level with CSV format
- Creates global log_and_print function

## Mode and Configuration Functions

### 7. **determine_mode(base_folder, cli_mode=None)**
- Determines operating mode with priority: CLI > mode.txt > default (single)

### 8. **read_signature()**
- Reads signature from /notifybot/signature.html
- Returns HTML content or empty string

### 9. **combine_body_and_signature(body_html, signature_html)**
- Combines body HTML and signature with proper formatting

## Email Utility Functions

### 10. **find_sendmail_path()**
- Locates sendmail executable in common system paths

### 11. **is_valid_email(email)**
- Validates email syntax using email_validator with sendmail compatibility

### 12. **read_file(path)**
- Reads text file content and strips whitespace

### 13. **extract_emails(raw, delimiters=";")**
- Splits and trims emails from raw string by delimiters

### 14. **read_recipients(path, delimiters=";")**
- Reads and validates emails from a file (semicolon-separated)

### 15. **deduplicate_emails(emails)**
- Removes duplicate email addresses (case-insensitive) while preserving order

### 16. **write_recipients_to_file(path, recipients)**
- Writes recipients list to file with deduplication

### 17. **merge_recipients(base_recipients, additional_recipients)**
- Merges two recipient lists, removing duplicates

## Email Creation Functions

### 18. **sanitize_filename(filename)**
- Sanitizes filename to prevent issues with special characters

### 19. **add_attachments(msg, attachment_folder)**
- Adds all files from attachment folder to email message

### 20. **create_email_message(recipients, subject, body_html, from_address, ...)**
- Creates properly formatted email message with embedded images and attachments

### 21. **embed_images_in_html(html_content, base_folder)**
- Replaces image src attributes with cid references for email embedding
- Returns modified HTML and list of embedded images

## Filter Logic Functions

### 22. **matches_filter_conditions(row, filters)**
- Checks if a CSV row matches filter conditions using PromQL-style syntax
- Supports operators: =, !=, =~, !~, and wildcards

### 23. **validate_filter_syntax(filters, available_fields=None)**
- Validates filter syntax and checks field names against available fields

### 24. **print_filter_syntax_help()**
- Prints help information about filter syntax

### 25. **apply_filter_logic(filters, inventory_path)**
- Applies filter logic to inventory.csv and returns matching email recipients

### 26. **parse_filter_condition(condition)**
- Parses single PromQL-style condition into (key, operator, value) tuple

### 27. **test_filter_conditions(filters, inventory_path, max_examples=5)**
- Tests filter conditions and shows examples of matched/unmatched rows (debugging)

### 28. **analyze_inventory_data(inventory_path)**
- Analyzes inventory data to help users understand available fields and values

## Template Functions

### 29. **substitute_placeholders(template, field_values)**
- Replaces placeholders in template with field values
- Enhanced handling of comma-separated values

### 30. **get_template_substitution_preview(subject_template, body_template, field_values)**
- Generates preview of template substitution for logging/debugging

### 31. **extract_field_values_from_matched_rows(filter_line, field_names, inventory_path, base_folder)**
- Extracts unique field values from matched CSV rows for template substitution
- Uses priority-based inventory selection (local field-inventory.csv first)

## Recipient Management Functions

### 32. **get_recipients_for_single_mode(base_folder, dry_run)**
- Gets recipients for single mode operation
- Returns recipients, CC, BCC lists and original counts

### 33. **get_recipients_for_multi_mode(base_folder, dry_run)**
- Gets recipients for multi mode operation
- Returns email configurations, CC, BCC lists and counts

### 34. **save_multi_mode_recipients(base_folder, email_configs, cc_recipients=None, bcc_recipients=None)**
- Saves recipient details for multi-mode to provide reference copies
- Creates individual files for each filter and summary

## Email Sending Functions

### 35. **prompt_for_confirmation()**
- Prompts user for yes/no confirmation to proceed

### 36. **send_via_sendmail(recipients, subject, body_html, from_address, ...)**
- Sends email using sendmail command
- Handles dry-run mode with DRAFT prefix

### 37. **send_single_mode_emails(recipients, subject, body_html, from_address, ...)**
- Sends emails in single mode with batching support

### 38. **send_multi_mode_emails(email_configs, subject_template, body_template, ...)**
- Sends emails in multi mode with personalized content per filter

## Helper Functions

### 39. **get_inventory_fields_for_help()**
- Gets available fields from inventory.csv for CLI help display

### 40. **main()**
- Main function that orchestrates the entire email sending process
- Handles CLI arguments, mode determination, and execution flow

## Exception Classes

### 41. **MissingRequiredFilesError(Exception)**
- Custom exception for missing required input files

---

## Function Categories Summary:
- **Validation & Setup**: 4 functions
- **Logging**: 2 functions  
- **Configuration**: 3 functions
- **Email Utilities**: 8 functions
- **Email Creation**: 4 functions
- **Filter Logic**: 7 functions
- **Templates**: 3 functions
- **Recipients**: 3 functions
- **Email Sending**: 4 functions
- **Helpers**: 2 functions
- **Main**: 1 function
- **Exceptions**: 1 class

**Total: 41 functions + 1 exception class**
