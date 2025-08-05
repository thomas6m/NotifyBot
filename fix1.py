def validate_from_address(base_folder: Path) -> str:
    """
    Validate that from.txt contains exactly one valid email address.
    
    Args:
        base_folder: Base folder containing from.txt
        
    Returns:
        str: The validated from email address
        
    Raises:
        MissingRequiredFilesError: If validation fails
    """
    from_file = base_folder / "from.txt"
    
    if not from_file.is_file():
        raise MissingRequiredFilesError("from.txt file is missing")
    
    try:
        from_content = read_file(from_file)
        
        if not from_content:
            raise MissingRequiredFilesError("from.txt is empty")
        
        # Extract all potential email addresses from the content
        # Split by common delimiters and newlines
        potential_emails = []
        for line in from_content.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):  # Skip empty lines and comments
                # Split by common delimiters
                emails_in_line = extract_emails(line, ";,")
                potential_emails.extend(emails_in_line)
        
        # Remove duplicates while preserving order
        unique_emails = []
        seen = set()
        for email in potential_emails:
            email_lower = email.lower()
            if email_lower not in seen:
                seen.add(email_lower)
                unique_emails.append(email)
        
        # Validate count
        if len(unique_emails) == 0:
            raise MissingRequiredFilesError("from.txt contains no valid email addresses")
        elif len(unique_emails) > 1:
            log_and_print("error", f"from.txt contains multiple email addresses: {', '.join(unique_emails)}")
            log_and_print("error", "from.txt must contain exactly ONE email address")
            raise MissingRequiredFilesError(
                f"from.txt contains {len(unique_emails)} email addresses, but exactly 1 is required. "
                f"Found: {', '.join(unique_emails)}"
            )
        
        # Validate the single email address
        from_address = unique_emails[0]
        if not is_valid_email(from_address):
            raise MissingRequiredFilesError(f"Invalid from address in from.txt: {from_address}")
        
        log_and_print("info", f"Validated from address: {from_address}")
        return from_address
        
    except Exception as exc:
        if isinstance(exc, MissingRequiredFilesError):
            raise
        else:
            raise MissingRequiredFilesError(f"Error reading from.txt: {exc}")


def validate_essential_content(subject: str, body_html: str, from_address: str) -> None:
    """
    Validate essential email content after reading from files.
    
    Args:
        subject: Email subject from subject.txt
        body_html: Email body from body.html  
        from_address: From address from from.txt
        
    Raises:
        MissingRequiredFilesError: If validation fails
    """
    errors = []
    
    if not subject:
        errors.append("Subject is empty (subject.txt)")
    
    if not body_html:
        errors.append("Body HTML is empty (body.html)")
    
    if not from_address:
        errors.append("From address is empty (from.txt)")
    elif not is_valid_email(from_address):
        errors.append(f"Invalid from address: {from_address}")
    
    if errors:
        for error in errors:
            log_and_print("error", error)
        raise MissingRequiredFilesError(f"Essential content validation failed: {', '.join(errors)}")
    
    log_and_print("info", "Essential content validation passed")
