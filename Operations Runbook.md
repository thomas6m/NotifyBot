# NotifyBot Email Sender - Operations Runbook

## Overview

This runbook provides step-by-step procedures for operating the NotifyBot Email Sender script in production environments.

## Pre-Flight Checklist

### System Requirements Verification

- [ ] Python 3.6+ installed and accessible
- [ ] Local SMTP server running (Postfix/Sendmail)
- [ ] Sufficient disk space for logs and backups
- [ ] Network connectivity verified
- [ ] Script permissions set correctly (`chmod +x notifybot.py`)

### Email Campaign Setup

- [ ] All required files created in campaign folder
- [ ] Email content reviewed and approved
- [ ] Recipient lists validated
- [ ] Attachments prepared and tested
- [ ] Dry run completed successfully

## Standard Operating Procedures

### 1. Campaign Preparation

#### Step 1.1: Create Campaign Directory

```bash
mkdir -p /campaigns/$(date +%Y%m%d)_campaign_name
cd /campaigns/$(date +%Y%m%d)_campaign_name
```

#### Step 1.2: Prepare Required Files

Create the following files:

```bash
# Sender information
echo "noreply@company.com" > from.txt

# Email subject
echo "Monthly Newsletter - December 2024" > subject.txt

# HTML body content
cat > body.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Newsletter</title>
</head>
<body>
    <h1>Monthly Newsletter</h1>
    <p>Dear Subscriber,</p>
    <p>Here's your monthly update...</p>
</body>
</html>
EOF

# Approver list
echo "manager@company.com" > approver.txt
echo "backup@company.com" >> approver.txt
```

#### Step 1.3: Set Up Recipient Lists

```bash
# Primary recipients (if not using filtering)
cat > to.txt << 'EOF'
user1@company.com
user2@company.com
EOF

# Optional: CC recipients
echo "cc@company.com" > cc.txt

# Optional: BCC recipients
echo "bcc@company.com" > bcc.txt
```

#### Step 1.4: Configure Filtering (Optional)

If using inventory-based filtering:

```bash
# Create inventory CSV
cat > inventory.csv << 'EOF'
name,department,emailids,status,location
John Doe,Engineering,john.doe@company.com,active,US
Jane Smith,Marketing,jane.smith@company.com,active,UK
EOF

# Create filter conditions
cat > filter.txt << 'EOF'
department,status
Engineering,active
Marketing,active
EOF
```

### 2. Pre-Deployment Testing

#### Step 2.1: Validate Configuration

```bash
# Check all required files exist
ls -la from.txt subject.txt body.html approver.txt

# Verify file contents
echo "=== FROM ==="
cat from.txt
echo "=== SUBJECT ==="
cat subject.txt
echo "=== APPROVERS ==="
cat approver.txt
```

#### Step 2.2: Perform Dry Run

```bash
# Execute dry run
python3 /path/to/notifybot.py . --dry-run

# Check logs for any issues
tail -f notifybot.log
```

#### Step 2.3: Verify Dry Run Results

- [ ] Approvers received draft email
- [ ] Email formatting appears correct
- [ ] Attachments (if any) are properly attached
- [ ] No errors in log file
- [ ] Subject line includes "[DRAFT]" prefix

### 3. Production Deployment

#### Step 3.1: Final Recipient List Review

```bash
# Check recipient count
wc -l to.txt

# Review first few recipients
head -10 to.txt

# Check for duplicates
sort to.txt | uniq -d
```

#### Step 3.2: Set Production Parameters

```bash
# Calculate optimal batch size based on recipient count
RECIPIENT_COUNT=$(wc -l < to.txt)
BATCH_SIZE=$((RECIPIENT_COUNT / 10))  # 10 batches
BATCH_SIZE=$((BATCH_SIZE > 500 ? 500 : BATCH_SIZE))  # Cap at 500
BATCH_SIZE=$((BATCH_SIZE < 50 ? 50 : BATCH_SIZE))    # Minimum 50

echo "Recipient count: $RECIPIENT_COUNT"
echo "Batch size: $BATCH_SIZE"
```

#### Step 3.3: Execute Production Send

```bash
# Start the email campaign
python3 /path/to/notifybot.py . \
    --batch-size $BATCH_SIZE \
    --delay 10 \
    --attachments-folder ./attachments

# Monitor progress
tail -f notifybot.log
```

### 4. Monitoring and Maintenance

#### Step 4.1: Real-Time Monitoring

```bash
# Monitor log file during send
tail -f notifybot.log | grep -E "(ERROR|WARNING|INFO)"

# Check system resources
top -p $(pgrep -f notifybot.py)

# Monitor SMTP queue
mailq
```

#### Step 4.2: Progress Tracking

```bash
# Check send progress
grep "Sent to" notifybot.log | wc -l

# Monitor batch completion
grep "Waiting.*seconds" notifybot.log | tail -5

# Check for errors
grep "ERROR" notifybot.log | tail -10
```

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue: "Missing required files" Error

**Symptoms:**
- Script exits with red error message
- Missing file names listed

**Resolution:**
```bash
# Check which files are missing
ls -la from.txt subject.txt body.html approver.txt

# Create missing files
touch missing_file.txt
echo "content" > missing_file.txt
```

#### Issue: SMTP Connection Failures

**Symptoms:**
- "Failed to send email" errors
- Connection refused messages

**Resolution:**
```bash
# Check SMTP service status
systemctl status postfix
# or
systemctl status sendmail

# Restart SMTP service if needed
sudo systemctl restart postfix

# Test SMTP connectivity
telnet localhost 25
```

#### Issue: High Error Rate

**Symptoms:**
- Many "Failed to send" messages
- High error count in summary

**Resolution:**
```bash
# Reduce batch size
python3 /path/to/notifybot.py . --batch-size 10 --delay 30

# Check recipient list for invalid emails
grep -v "@" to.txt  # Should return nothing if all valid
```

#### Issue: Attachment Failures

**Symptoms:**
- "Failed to attach file" errors
- Red error messages for attachments

**Resolution:**
```bash
# Check attachment files exist
ls -la attachments/

# Verify file permissions
chmod 644 attachments/*

# Check file sizes
find attachments/ -type f -exec ls -lh {} \;
```

### Emergency Procedures

#### Emergency Stop

If campaign needs to be stopped immediately:

```bash
# Find the process
ps aux | grep notifybot.py

# Kill the process
kill -TERM <PID>

# Check remaining recipients
grep "Sent to" notifybot.log | wc -l
```

#### Rollback Procedures

If issues are detected post-send:

```bash
# Create incident report
cat > incident_report.txt << EOF
Date: $(date)
Campaign: $(pwd)
Issue: [Description]
Recipients affected: $(grep "Sent to" notifybot.log | wc -l)
Action taken: [Description]
EOF

# Preserve logs
cp notifybot.log incident_$(date +%Y%m%d_%H%M%S).log
```

## Maintenance Tasks

### Daily Maintenance

```bash
# Check log file size
ls -lh notifybot.log

# Archive old logs (if > 100MB)
if [ $(stat -f%z notifybot.log 2>/dev/null || stat -c%s notifybot.log) -gt 104857600 ]; then
    mv notifybot.log notifybot_$(date +%Y%m%d).log
fi

# Clean up backup files older than 30 days
find . -name "*.bak" -mtime +30 -delete
```

### Weekly Maintenance

```bash
# Check SMTP server health
systemctl status postfix

# Review error patterns
grep "ERROR" notifybot.log | cut -d' ' -f5- | sort | uniq -c | sort -nr

# Clean up old campaign directories
find /campaigns -type d -mtime +90 -exec rm -rf {} \;
```

### Monthly Maintenance

```bash
# Archive and rotate logs
mkdir -p /archives/$(date +%Y%m)
mv notifybot_*.log /archives/$(date +%Y%m)/

# Update email validation patterns if needed
# Review and update recipient lists
# Performance analysis and optimization
```

## Performance Optimization

### Batch Size Optimization

| Recipient Count | Recommended Batch Size | Delay (seconds) |
|----------------|------------------------|-----------------|
| < 100          | 25                     | 5               |
| 100-1000       | 50                     | 10              |
| 1000-5000      | 100                    | 15              |
| 5000-10000     | 250                    | 20              |
| > 10000        | 500                    | 30              |

### Resource Monitoring

```bash
# Monitor disk usage
df -h

# Monitor memory usage
free -h

# Monitor network connections
netstat -an | grep :25
```

## Security Considerations

### Access Control

```bash
# Set proper file permissions
chmod 600 *.txt
chmod 644 *.html
chmod 755 notifybot.py

# Limit access to campaign directories
chown -R emailuser:emailgroup /campaigns
chmod 750 /campaigns
```

### Log Security

```bash
# Ensure logs don't contain sensitive data
grep -i password notifybot.log  # Should return nothing
grep -i secret notifybot.log    # Should return nothing

# Set log file permissions
chmod 640 notifybot.log
```

## Compliance and Reporting

### Campaign Reporting

```bash
# Generate campaign summary
cat > campaign_summary.txt << EOF
Campaign: $(basename $(pwd))
Date: $(date)
Total Recipients: $(wc -l < to.txt)
Emails Sent: $(grep "Sent to" notifybot.log | wc -l)
Errors: $(grep "ERROR" notifybot.log | wc -l)
Duration: $(grep "Duration:" notifybot.log | tail -1 | cut -d: -f2)
EOF
```

### Audit Trail

```bash
# Create audit log entry
echo "$(date): Campaign $(basename $(pwd)) completed by $(whoami)" >> /var/log/email_campaigns.log
```

## Contact Information

- **Primary Contact:** IT Operations Team
- **Secondary Contact:** Email Administrator
- **Emergency Contact:** On-call Engineer
- **Escalation:** IT Manager

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0     | 2024-01-01 | Initial version |
| 1.1     | 2024-01-15 | Added attachment support |
| 1.2     | 2024-02-01 | Enhanced error handling |
