# NotifyBot Functions List

## Validation Functions
1. **`validate_fields_against_inventory(base_folder, inventory_path, mode)`**
   - Validate that all field names used in filter.txt and field.txt exist in inventory.csv headers
   - Returns: Tuple of (is_valid, error_messages)

2. **`validate_fields_with_priority(base_folder, mode)`**
   - Enhanced field validation with priority-based inventory checking
   - Priority: local field-inventory.csv > global inventory.csv
   - Returns: Tuple of (is_valid, error_messages)

3. **`check_required_files(base, required, dry_run, mode)`**
   - Check for required input files and validate field names
   - Raises MissingRequiredFilesError if files are missing

4. **`validate_base_folder(base_folder)`**
   - Ensure base folder is valid relative path inside /notifybot/basefolder
   - Returns: Validated Path object

5. **`is_valid_email(email)`**
   - Check email syntax using email_validator with sendmail compatibility
   - Returns: Boolean

## Utility Functions
6. **`csv_log_entry(message)`**
   - Generate log entry in CSV format with proper escaping
   - Returns: CSV formatted string

7. **`setup_logging()`**
   - Configure logging to INFO+ level in structured CSV format
   - Creates global log_and_print function

8. **`determine_mode(base_folder, cli_mode)`**
   - Determine operating mode with priority: CLI > mode.txt > default (single)
   - Returns: String ('single' or 'multi')

9. **`read_signature()`**
   - Read signature from /notifybot/signature.html file
   - Returns: HTML signature content or empty string

10. **`combine_body_and_signature(body_html, signature_html)`**
    - Combine body HTML and signature HTML with proper spacing
    - Returns: Combined HTML string

11. **`find_sendmail_path()`**
    - Find sendmail executable path in common locations
    - Returns: Path to sendmail executable

## File I/O Functions
12. **`read_file(path)`**
    - Read text file content and strip whitespace
    - Returns: File content as string

13. **`extract_emails(raw, delimiters)`**
    - Split and trim emails from raw string by delimiters
    - Returns: List of email strings

14. **`read_recipients(path, delimiters)`**
    - Read and validate emails from a file (semicolon-separated)
    - Returns: List of valid email addresses

15. **`deduplicate_emails(emails)`**
    - Deduplicate email addresses (case-insensitive) while preserving order
    - Returns: List of unique emails

16. **`write_recipients_to_file(path, recipients)`**
    - Write recipients list to file with deduplication
    - Returns: None

17. **`merge_recipients(base_recipients, additional_recipients)`**
    - Merge two lists of recipients, removing duplicates
    - Returns: Merged and deduplicated list

## Email Creation Functions
18. **`sanitize_filename(filename)`**
    - Sanitize filename to prevent issues with special characters
    - Returns: Sanitized filename string

19. **`add_attachments(msg, attachment_folder)`**
    - Add all files from attachment folder to email message
    - Returns: None (modifies msg in place)

20. **`create_email_message(recipients, subject, body_html, from_address, attachment_folder, base_folder, cc_recipients, bcc_recipients)`**
    - Create properly formatted email message with embedded images and attachments
    - Returns: MIMEMultipart message object

21. **`embed_images_in_html(html_content, base_folder)`**
    - Replace image src attributes with cid references and return embedded images
    - Returns: Tuple of (modified_html, list_of_mime_images)

## Filter Logic Functions
22. **`matches_filter_conditions(row, filters)`**
    - Check if a row matches filter conditions with PromQL-style syntax
    - Supports operators: =, !=, =~, !~, wildcards
    - Returns: Boolean

23. **`validate_filter_syntax(filters, available_fields)`**
    - Validate filter syntax and check field names against available fields
    - Returns: Tuple of (is_valid, error_messages)

24. **`print_filter_syntax_help()`**
    - Print help information about filter syntax
    - Returns: None

25. **`apply_filter_logic(filters, inventory_path)`**
    - Apply enhanced filter logic using PromQL-style syntax
    - Returns: List of filtered email recipients

26. **`parse_filter_condition(condition)`**
    - Parse a single PromQL-style condition
    - Returns: Tuple of (key, operator, value)

## Testing and Analysis Functions
27. **`test_filter_conditions(filters, inventory_path, max_examples)`**
    - Test filter conditions and show examples of matched/unmatched rows
    - Returns: None (prints results)

28. **`analyze_inventory_data(inventory_path)`**
    - Analyze inventory data to help users understand available fields and values
    - Returns: None (prints analysis)

## Template Functions
29. **`substitute_placeholders(template, field_values)`**
    - Replace placeholders in template with field values
    - Enhanced handling of comma-separated values
    - Returns: Template with placeholders replaced

30. **`get_template_substitution_preview(subject_template, body_template, field_values)`**
    - Generate preview of template substitution for logging/debugging
    - Returns: Dict with 'subject', 'body_preview', 'substitutions_made'

31. **`extract_field_values_from_matched_rows(filter_line, field_names, inventory_path)`**
    - Extract unique field values from matched rows for template substitution
    - Uses priority-based inventory selection
    - Returns: Dict of field_name -> comma_separated_values

## Recipient Processing Functions
32. **`get_recipients_for_single_mode(base_folder, dry_run)`**
    - Get recipients for single mode operation
    - Returns: Tuple of (recipients, cc_recipients, bcc_recipients, original_counts...)

33. **`get_recipients_for_multi_mode(base_folder, dry_run)`**
    - Get recipients for multi mode operation with field value extraction
    - Returns: Tuple of (email_configs, cc_recipients, bcc_recipients, original_counts...)

34. **`save_multi_mode_recipients(base_folder, email_configs, cc_recipients, bcc_recipients)`**
    - Save recipient details for multi-mode operation
    - Creates individual files for each filter and summary
    - Returns: None

## Email Sending Functions
35. **`prompt_for_confirmation()`**
    - Prompt user for yes/no confirmation to proceed
    - Returns: Boolean

36. **`send_via_sendmail(recipients, subject, body_html, from_address, attachment_folder, dry_run, original_recipients_count, base_folder, cc_recipients, bcc_recipients, original_cc_count, original_bcc_count, filter_info)`**
    - Send email using sendmail command
    - In dry-run mode, sends only to approvers with DRAFT prefix
    - Returns: Boolean (success/failure)

37. **`send_single_mode_emails(recipients, subject, body_html, from_address, batch_size, dry_run, delay, attachment_folder, cc_recipients, bcc_recipients, original_recipients_count, base_folder, original_cc_count, original_bcc_count)`**
    - Send emails in single mode with batching
    - Returns: None

38. **`send_multi_mode_emails(email_configs, subject_template, body_template, from_address, dry_run, delay, attachment_folder, base_folder, cc_recipients, bcc_recipients, original_cc_count, original_bcc_count, batch_size)`**
    - Send emails in multi mode - one personalized email per filter condition
    - Returns: None

## Helper Functions
39. **`get_inventory_fields_for_help()`**
    - Get available fields from inventory.csv for CLI help display
    - Returns: Formatted string of available fields

40. **`main()`**
    - Main function with argument parsing and execution flow
    - Handles both single and multi mode operations
    - Returns: None

## Exception Classes
41. **`MissingRequiredFilesError`**
    - Custom exception for missing required input files
    - Inherits from Exception

## Global Constants
- `NOTIFYBOT_ROOT`: Path("/notifybot")
- `BASEFOLDER_PATH`: NOTIFYBOT_ROOT / "basefolder"
- `LOG_FILENAME`: NOTIFYBOT_ROOT / "logs" / "notifybot.log"
- `INVENTORY_PATH`: NOTIFYBOT_ROOT / "inventory" / "inventory.csv"

## Key Features Supported
- **Single Mode**: One email to multiple recipients
- **Multi Mode**: Multiple personalized emails based on filter conditions
- **Dry-run Mode**: Send drafts to approvers only
- **Template Substitution**: Replace placeholders with CSV field values
- **Filter Logic**: PromQL-style filtering with operators (=, !=, =~, !~, wildcards)
- **Image Embedding**: Embed images as inline attachments
- **Batch Processing**: Send emails in configurable batches with delays
- **Signature Support**: Global signature from /notifybot/signature.html
- **Priority-based Inventory**: Local field-inventory.csv takes precedence over global
- **Comprehensive Logging**: CSV-formatted logs with emojis and timestamps
