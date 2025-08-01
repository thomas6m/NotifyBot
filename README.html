<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>🚀 NotifyBot User Runbook</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 2em; line-height: 1.6; background-color: #fff; color: #333; }
    h1, h2, h3 { color: #2a6592; }
    code { background: #f4f4f4; padding: 2px 4px; border-radius: 4px; }
    pre { background: #f8f8f8; padding: 1em; border-left: 4px solid #ccc; overflow-x: auto; }
    .box, .important, .tip, .note { background: #eef5fb; padding: 1em; border: 1px solid #b6d5f2; border-radius: 6px; margin-bottom: 1em; }
    .important { background-color: #FFCCCB; border-color: #8B0000; }
    .tip { background-color: #e6ffed; border-color: #28a745; }
    .note { background-color: #f1f1f1; border-color: #ccc; }
    .button-link {
      display: inline-block;
      padding: 0.5em 1em;
      background: #007bff;
      color: white;
      text-decoration: none;
      border-radius: 5px;
      margin-top: 1em;
    }
    table { border-collapse: collapse; width: 100%; margin-top: 1em; }
    table, th, td { border: 1px solid #ccc; }
    th, td { padding: 10px; text-align: left; }
  </style>
</head>
<body>

<h1>🚀 NotifyBot User Runbook</h1>

<div class="features">
  <p>
    <strong>NotifyBot</strong>, our smart, scalable solution for email automation.  
    Whether you're sending a handful of emails or thousands, NotifyBot makes it effortless, safe, and efficient.  
    It supports both single and multi modes, with dry-run and signature capabilities.
  </p>
  <ul class="feature-list">
    <li>📧 <b>Batch Email Sending</b>: Deliver emails in customizable batches with controlled delays</li>
    <li>🖋️ <b>HTML Email Support</b>: Craft rich, styled messages (with attachments!)</li>
    <li>🎯 <b>Recipient Filtering</b>: Easily target the right audience with CSV filters</li>
    <li>🧪 <b>Dry Run Mode</b>: Test configurations safely without sending actual emails</li>
    <li>✅ <b>Email Validation</b>: Automatically validate addresses to reduce bounces</li>
    <li>📎 <b>Attachment Support</b>: Attach files up to 15MB each</li>
    <li>🔁 <b>Deduplication</b>: Automatically remove duplicate recipients</li>
    <li>📊 <b>Logging & Transparency</b>: Detailed logs with automatic log rotation</li>
    <li>✍️ <b>Global Signature Support</b>: Automatically append signature to all emails</li>
    <li>🖼️ <b>Image Embedding</b>: Embed images directly in emails to avoid blocking</li>
  </ul>
  <p><i>Stay in control. Stay efficient. That's the NotifyBot way.</i></p>
</div>

<div class="important">
  ⚠️ <b>Critical Disclaimer:</b><br><br>
  📧 Always run NotifyBot in <code>--dry-run</code> mode first to verify recipients and content.<br>
  ❌ Do <b>not</b> use <code>--force</code> unless running in a fully automated script with prior approval.<br>
  ⚠️ Running live without a dry-run review may result in unintended mass emails.<br>
  📂 The <code>&lt;user-basefolder&gt;</code> is the directory where you must maintain all required input files 
  (e.g. <code>subject.txt</code>, <code>body.html</code>, <code>to.txt</code>).
</div>

<div class="tip">
  💡 <b>Tip:</b> Always replace <code>&lt;user-basefolder&gt;</code> in the examples below with the name of your campaign folder inside <code>/notifybot/basefolder/</code>.  
  Example: If your folder is <code>newsletter_august</code>, use:  
  <br><code>/notifybot/venv/bin/python notifybot.py --base-folder newsletter_august --dry-run</code>
</div>

<h2>🏗️ File Structure & Locations</h2>
<div class="box">
  <h3>Required Directory Structure:</h3>
  <pre>
/notifybot/
├── basefolder/                     # Your campaign folders go here
│   └── &lt;user-basefolder&gt;/         # Your specific campaign folder
│       ├── subject.txt             # Email subject (required)
│       ├── body.html               # Email body HTML (required)
│       ├── from.txt                # Sender email address (required)
│       ├── approver.txt            # Approvers for dry-run (required)
│       ├── mode.txt                # single or multi (optional)
│       ├── to.txt                  # Recipients for single mode (optional)
│       ├── cc.txt                  # CC recipients (optional)
│       ├── bcc.txt                 # BCC recipients (optional)
│       ├── filter.txt              # Filter conditions (for multi mode)
│       ├── field.txt               # Field names for substitution (multi mode)
│       ├── additional_to.txt       # Additional recipients to merge (optional)
│       ├── attachment/             # Folder for attachments (optional)
│       ├── images/                 # Folder for embedded images (optional)
│       └── recipients/             # Auto-generated recipient files
├── inventory/
│   └── inventory.csv               # Master recipient database
├── signature.html                  # Global signature file (optional)
└── logs/
    └── notifybot.log              # Application logs
  </pre>
</div>


<h2>🖼️ Image Embedding</h2>
<div class="box">
  <p><strong>NEW:</strong> Images are now automatically embedded in emails to prevent blocking by email clients.</p>
  <ul>
    <li>📁 <strong>Location:</strong> Place images in <code>&lt;user-basefolder&gt;/images/</code></li>
    <li>🔗 <strong>Usage:</strong> Reference images in your HTML using relative paths: <code>&lt;img src="logo.png"&gt;</code></li>
    <li>⚡ <strong>Automatic:</strong> Images are automatically converted to embedded attachments</li>
    <li>🚫 <strong>External URLs:</strong> External image URLs are preserved but may be blocked by email clients</li>
    <li>📏 <strong>Supported formats:</strong> All common image formats (PNG, JPG, GIF, etc.)</li>
  </ul>
</div>

<h2>🔍 Enhanced Filter Logic</h2>
<div class="box">
  <p>NotifyBot uses an enhanced PromQL-style filter engine with support for:</p>
  <ul>
    <li><code>=</code> – Exact match (case-insensitive)</li>
    <li><code>!=</code> – Not equal (case-insensitive)</li>
    <li><code>=~</code> – Regex match (case-insensitive)</li>
    <li><code>!~</code> – Regex not match (case-insensitive)</li>
    <li><code>*</code>, <code>?</code>, <code>[seq]</code> – Wildcard (fnmatch-style)</li>
  </ul>
  <p>
    Each line in <code>filter.txt</code> is treated as a separate <strong>OR clause</strong>.<br>
    Within a line, comma-separated conditions are evaluated as <strong>AND conditions</strong>.
  </p>
</div>

<h3>🧠 How the Matching Works</h3>
<ol>
  <li>Each line from <code>filter.txt</code> is parsed into individual conditions.</li>
  <li>Each row from <code>inventory.csv</code> is evaluated against these conditions.</li>
  <li>If any line (OR block) passes (i.e., all conditions within it are true), the row is included.</li>
  <li>Email addresses from the <code>email</code> field are split by semicolon and validated.</li>
  <li>Duplicate and invalid addresses are filtered out automatically.</li>
</ol>

<h3>📌 Additional Notes</h3>
<ul>
  <li>If a condition omits the field name (e.g. <code>*@example.com</code>), it is matched against <em>all fields</em> in the row.</li>
  <li>Regex errors are logged and ignored gracefully.</li>
  <li>Missing keys in the row will be skipped with a warning.</li>
  <li><strong>NEW:</strong> Enhanced syntax validation with detailed error messages</li>
  <li><strong>NEW:</strong> Filter testing mode available for debugging</li>
</ul>

<h3>✅ Examples</h3>
<pre>
# Match engineering employees in NA
department="engineering",region=~"USA|Canada"

# Exclude all interns and contractors
name!~".*(Intern|Contract).*"

# Wildcard fallback (any field containing the domain)
*@example.org

# Complex regex for multiple departments
department=~"(sales|marketing|support)"

# Exact match with wildcard value
status=active*
</pre>

<hr>

<h2>📤 Enhanced Recipient Priority</h2>
<h3>📧 Single Mode</h3>
<p><strong>Sends one email to multiple recipients.</strong> Used for announcements or bulk messages.</p>
<h4>Recipient Priority:</h4>
<ol>
  <li><strong>Dry Run Mode:</strong> Sends only to <code>approver.txt</code></li>
  <li><strong>Live Mode:</strong> Uses first available in this priority:
    <ul>
      <li><code>to.txt</code> (if exists, merges with <code>additional_to.txt</code>)</li>
      <li><code>filter.txt + inventory.csv</code> (creates <code>to.txt</code>, merges with <code>additional_to.txt</code>)</li>
      <li><code>additional_to.txt</code> only (creates <code>to.txt</code>)</li>
    </ul>
  </li>
  <li>Additionally merges any recipients from:
    <ul>
      <li><code>cc.txt</code></li>
      <li><code>bcc.txt</code></li>
    </ul>
  </li>
</ol>
<h4>📝 NEW Features:</h4>
<ul>
  <li><strong>Smart Merging:</strong> <code>additional_to.txt</code> is automatically merged with filter results or <code>to.txt</code></li>
  <li><strong>Auto-generation:</strong> <code>to.txt</code> is created automatically from filter results for future reference</li>
  <li><strong>Enhanced Logging:</strong> Detailed logs show merge operations and duplicate removal</li>
  <li><strong>Dry-run Protection:</strong> Existing <code>to.txt</code> is preserved during dry-run mode</li>
</ul>

<hr>

<h3>📬 Multi Mode</h3>
<p><strong>Sends multiple personalized emails.</strong> Used for targeted campaigns.</p>
<h4>Recipient Logic:</h4>
<ol>
  <li>Each line in <code>filter.txt</code> produces one email.</li>
  <li>Recipients are derived by applying that filter to <code>inventory.csv</code>.</li>
  <li><code>additional_to.txt</code> (if present) is merged with <strong>every</strong> email's recipient list.</li>
  <li><code>cc.txt</code> and <code>bcc.txt</code> are applied globally to all emails.</li>
  <li>In <strong>dry-run</strong>, all recipient lists are replaced with <code>approver.txt</code>.</li>
</ol>
<h4>📝 NEW Features:</h4>
<ul>
  <li><strong>Template Substitution:</strong> Use <code>field.txt</code> to define fields for placeholder replacement</li>
  <li><strong>Recipient Files:</strong> Individual recipient files are saved for each filter in <code>recipients/</code> folder</li>
  <li><strong>Comprehensive Summary:</strong> Detailed summary files with statistics and breakdowns</li>
  <li><strong>Enhanced Logging:</strong> Per-filter logging with field value extraction</li>
</ul>

<h2>📋 Template Substitution (Multi Mode)</h2>
<div class="box">
  <p><strong>NEW:</strong> Multi mode now supports template substitution using field values extracted from filters.</p>
  
  <h4>Setup:</h4>
  <ol>
    <li>Create <code>field.txt</code> with field names (one per line)</li>
    <li>Use placeholders in <code>subject.txt</code> and <code>body.html</code></li>
    <li>Filter conditions will extract values for substitution</li>
  </ol>
  
  <h4>Example field.txt:</h4>
  <pre>
department
region
status
  </pre>
  
  <h4>Example subject.txt:</h4>
  <pre>
Monthly Report for {department} - {region}
  </pre>
  
  <h4>Example filter.txt:</h4>
  <pre>
department="sales",region="north"
department="marketing",region="south"
  </pre>
  
  <p>This will generate two emails with subjects:</p>
  <ul>
    <li>"Monthly Report for sales - north"</li>
    <li>"Monthly Report for marketing - south"</li>
  </ul>
</div>

<section>
  <h2>📁 Enhanced Recipients Management</h2>
  <div class="note">
    <p><strong>NEW:</strong> NotifyBot now automatically saves recipient information for reference and auditing.</p>
    
    <h4>Single Mode:</h4>
    <ul>
      <li>Creates <code>to.txt</code> from filter results if it doesn't exist</li>
      <li>Merges <code>additional_to.txt</code> with existing recipients</li>
      <li>Detailed logging of merge operations</li>
    </ul>
    
    <h4>Multi Mode:</h4>
    <ul>
      <li>Creates <code>recipients/</code> subfolder</li>
      <li>Individual files for each filter: <code>filter_001_department_sales.txt</code></li>
      <li>Separate files for CC and BCC recipients</li>
      <li>Comprehensive summary file: <code>multi_mode_summary.txt</code></li>
      <li>Consolidated unique recipients file: <code>all_unique_recipients.txt</code></li>
    </ul>
  </div>
</section>

<section>
  <h2>🧪 Enhanced Dry-Run Mode</h2>
  <div class="note">
    <p><strong>UPDATED:</strong> Dry-run mode now provides more detailed information and better recipient file management.</p>
    
    <h4>New Features:</h4>
    <ul>
      <li><strong>Detailed Draft Info:</strong> Draft emails include comprehensive recipient breakdown</li>
      <li><strong>Filter Information:</strong> Multi-mode drafts show which filter generated the email</li>
      <li><strong>Recipient File Generation:</strong> Creates recipient files even in dry-run mode for review</li>
      <li><strong>Preservation Mode:</strong> Existing <code>to.txt</code> files are not overwritten during dry-run</li>
      <li><strong>Enhanced Statistics:</strong> More detailed logging of what would happen in live mode</li>
    </ul>
    
    <p><b>Always run dry-run first to prevent unintended mass emails.</b></p>
  </div>
</section>

<section>
  <h2>📊 Enhanced Logging</h2>
  <p><strong>UPDATED:</strong> Logs are written to <code>/notifybot/logs/notifybot.log</code> in CSV format with expanded emoji categories for quick scanning.</p>
  <pre>
ℹ️ Info, ⚠️ Warning, ❌ Error, ✅ Success, 📝 Draft, 🔧 Mode,
⏳ Processing, 💾 Backup, 📂 File, ✋ Confirmation, ✍️ Signature
  </pre>
  <p>
    📡 All logs are also forwarded in real-time to <b>Splunk</b> for auditing and long-term reference.
  </p>
  <a class="button-link" href="https://tinyurl/notifybot" target="_blank">📊 Open Splunk Dashboard</a>
</section>

<section>
  <h2>📎 Attachments & 🖼️ Images</h2>
  <ul>
    <li>📎 <strong>Attachments:</strong> Files in <code>attachment/</code> are sent as attachments (up to 15MB each)</li>
    <li>🖼️ <strong>Embedded Images:</strong> Images in <code>images/</code> are automatically embedded in HTML emails to prevent blocking</li>
    <li>🔗 <strong>Image References:</strong> Use relative paths in HTML: <code>&lt;img src="logo.png"&gt;</code></li>
    <li>⚠️ <strong>External Images:</strong> External URLs are preserved but may be blocked by email clients</li>
  </ul>
</section>

<section>
  <h2>🎯 Command Line Examples</h2>
  <div class="box">
    <h4 style="color: #8B0000;">Basic Dry-Run (Always start here):</h4>
    <pre>/notifybot/venv/bin/python notifybot.py --base-folder newsletter_august --dry-run</pre>
    
    <h4>Single Mode (Live):</h4>
    <pre>/notifybot/venv/bin/python notifybot.py --base-folder newsletter_august --mode single --batch-size 500 --delay 5.0</pre>
    
    <h4>Multi Mode (Live):</h4>
    <pre>/notifybot/venv/bin/python notifybot.py --base-folder newsletter_august --mode multi --delay 2.0</pre>
    
    <h4 style="color: #8B0000;">⚠️ Automated Script (with force - Use with extreme caution):</h4>
    <pre>/notifybot/venv/bin/python notifybot.py --base-folder newsletter_august --mode single --force</pre>
  </div>
</section>

<section>
  <h2>✅ Approval Process</h2>
  <p><strong>UPDATED:</strong> Before sending email in live mode, <code>approver.txt</code> ensures dry-run copies are reviewed and approved with enhanced draft information.</p>
  
  <h4>Draft Email Features:</h4>
  <ul>
    <li>📋 <strong>Recipient Breakdown:</strong> Shows original TO, CC, BCC counts</li>
    <li>🎯 <strong>Filter Information:</strong> Multi-mode shows which filter generated the email</li>
    <li>📊 <strong>Statistics:</strong> Total recipient counts and campaign scope</li>
    <li>🔍 <strong>Review Files:</strong> Generated recipient files for detailed review</li>
  </ul>
</section>

<section>
  <h2>🚀 Best Practices & Tips</h2>
  <div class="tip">
    <h4>🎯 Getting Started:</h4>
    <ol>
      <li>Always start with <code>--dry-run</code> to test your configuration</li>
      <li>Review generated recipient files in the <code>recipients/</code> folder</li>
      <li>Check the Splunk dashboard for detailed logs</li>
      <li>Use small batch sizes for large campaigns to avoid overwhelming the mail server</li>
    </ol>
    
    <h4>📧 Email Best Practices:</h4>
    <ul>
      <li>Embed images instead of linking to external URLs</li>
      <li>Test filter logic with a small subset first</li>
      <li>Use meaningful campaign folder names</li>
    </ul>
    
    <h4>🔧 Advanced Features:</h4>
    <ul>
      <li>Use template substitution in multi-mode for personalized campaigns</li>
      <li>Leverage <code>additional_to.txt</code> for adding VIPs to all campaigns</li>
      <li>Use regex filters for complex recipient selection</li>
      <li>Monitor logs in real-time via Splunk dashboard</li>
    </ul>
  </div>
</section>

</body>
</html>
