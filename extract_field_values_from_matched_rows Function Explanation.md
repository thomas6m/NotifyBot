# extract_field_values_from_matched_rows Function Explanation

## Overview
This function extracts actual field values from CSV inventory data for rows that match a specific filter condition. It's used in multi-mode operations to personalize email templates by substituting placeholders with real data from matched records.

## Function Signature
```python
def extract_field_values_from_matched_rows(filter_line: str, field_names: List[str], inventory_path: Path, base_folder: Path) -> Dict[str, str]:
```

## Parameters
- **`filter_line`**: A single filter condition (e.g., "sector=banking,region=asia")
- **`field_names`**: List of field names to extract values for (from field.txt)
- **`inventory_path`**: Path to the global inventory.csv file
- **`base_folder`**: Base folder path (used to check for local field-inventory.csv)

## Return Value
Returns a dictionary mapping field names to comma-separated string values extracted from matching rows.

## Key Features

### 1. Priority-Based Inventory Selection
```python
# Priority 1: Check for local field-inventory.csv 
if local_field_inventory_path.exists():
    actual_inventory_path = local_field_inventory_path
    inventory_source = "local field-inventory.csv"
else:
    actual_inventory_path = inventory_path  # Use the global inventory
    inventory_source = "global inventory.csv"
```

The function implements a priority system:
- **Priority 1**: Use local `field-inventory.csv` if it exists in the base folder
- **Priority 2**: Fall back to global `inventory.csv`

### 2. Header Cleaning and Validation
```python
# Get headers and strip whitespace - CRITICAL FIX
raw_headers = reader.fieldnames or []
clean_headers = [header.strip() for header in raw_headers]

# Verify that all requested field names exist in CSV headers
available_fields = set(clean_headers)
missing_fields = [field for field in field_names if field not in available_fields]
```

The function handles common CSV issues:
- Strips whitespace from header names
- Validates that requested fields exist in the CSV
- Reports missing fields with helpful error messages

### 3. Row Matching and Data Extraction
```python
for row in reader:
    total_rows_processed += 1
    
    # Create cleaned row for filter matching
    cleaned_row = {}
    for raw_header, raw_value in row.items():
        clean_header = raw_header.strip() if raw_header else raw_header
        clean_value = raw_value.strip() if raw_value else raw_value
        cleaned_row[clean_header] = clean_value
    
    # Check if this row matches the filter condition
    if matches_filter_conditions(cleaned_row, [filter_line]):
        matched_rows_count += 1
        matched_rows_data.append(cleaned_row)
```

For each CSV row:
1. Cleans both headers and values by stripping whitespace
2. Tests if the row matches the filter condition using `matches_filter_conditions()`
3. Stores matched rows for further processing

### 4. Value Aggregation and Deduplication
```python
# Extract ACTUAL values from this matched row
for field in field_names:
    if field in cleaned_row:
        raw_value = cleaned_row[field]
        if raw_value:
            raw_value_str = str(raw_value).strip()
            if raw_value_str:
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
```

The function handles complex value aggregation:
- Collects all unique values for each field across matched rows
- Handles comma-separated values within individual CSV cells
- Uses Python sets to automatically deduplicate values
- Preserves empty fields as empty strings (not None)

### 5. Special HTML Table Generation
```python
# NEW: Generate HTML table rows for microservices data
if matched_rows_data:
    table_rows_html = ""
    for row in matched_rows_data:
        # Extract specific fields for the table
        sector = row.get('sector', '')
        region = row.get('region', '')
        clustername = row.get('clustername', '')
        namespace = row.get('namespace', '')
        microservicename = row.get('microservicename', '')
        replicacount = row.get('replicacount', '')
        
        # Generate HTML table row
        table_rows_html += f"""        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">{sector}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{region}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{clustername}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{namespace}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{microservicename}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{replicacount}</td>
        </tr>
"""
    
    # Add the table rows as a special field
    field_values['microservice_table_rows'] = table_rows_html.rstrip('\n')
```

A special feature generates HTML table rows for microservice data, creating a formatted table that can be embedded in email templates.

### 6. Result Formatting and Logging
```python
# Convert sets to comma-separated strings, sorted for consistency
for field in field_names:
    if field_unique_values[field]:
        # Sort values for consistent output
        sorted_values = sorted(list(field_unique_values[field]))
        field_values[field] = ",".join(sorted_values)
    else:
        # Keep empty string for fields with no values
        field_values[field] = ""
```

Final processing:
- Converts sets to sorted, comma-separated strings
- Ensures consistent output ordering
- Provides detailed logging for debugging

## Example Usage Scenario

Given:
- **Filter**: `sector=banking,region=asia`
- **Fields**: `['microservicename', 'clustername', 'replicacount']`
- **Matched rows**: 3 rows with microservices data

The function might return:
```python
{
    'microservicename': 'auth-service,payment-api,user-mgmt',
    'clustername': 'prod-asia-1,prod-asia-2', 
    'replicacount': '3,5,2',
    'microservice_table_rows': '<tr><td>banking</td><td>asia</td>...</tr>...'
}
```

These values can then be used in email templates with placeholders like `{microservicename}` or `{microservice_table_rows}`.

## Error Handling

The function includes comprehensive error handling:
- **Missing inventory files**: Logs warnings and returns empty values
- **Missing fields**: Reports which fields weren't found in CSV headers
- **Empty results**: Warns when no rows match the filter
- **CSV parsing errors**: Catches and logs exceptions with context
- **Debug information**: Provides detailed logging for troubleshooting

## Integration with Template System

The extracted field values integrate with the template substitution system:
1. Values are extracted by this function for each filter condition
2. The `substitute_placeholders()` function replaces `{fieldname}` placeholders
3. Personalized emails are generated for each unique filter/recipient combination

This enables powerful personalization where each email can contain specific data relevant to the recipients matched by each filter condition.
