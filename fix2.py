# Replace this section in the main function:

# OLD CODE:
# # Read email content
# subject = read_file(base_folder / "subject.txt")
# body_html = read_file(base_folder / "body.html")
# from_address = read_file(base_folder / "from.txt")
# 
# # ... signature code ...
# 
# # Validate essential content
# if not subject:
#     log_and_print("error", "Subject is empty")
#     sys.exit(1)
# if not body_html:
#     log_and_print("error", "Body HTML is empty")
#     sys.exit(1)
# if not from_address or not is_valid_email(from_address):
#     log_and_print("error", f"Invalid from address: {from_address}")
#     sys.exit(1)

# NEW CODE:
        # Read email content
        subject = read_file(base_folder / "subject.txt")
        body_html = read_file(base_folder / "body.html")
        
        # Validate from address with enhanced checking
        from_address = validate_from_address(base_folder)
        
        # Read signature (optional)
        signature_html = read_signature()
        
        # Combine body and signature
        final_body_html = combine_body_and_signature(body_html, signature_html)
        
        # Validate essential content
        validate_essential_content(subject, body_html, from_address)
