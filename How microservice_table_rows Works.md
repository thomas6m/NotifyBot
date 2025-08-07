How microservice_table_rows Works
Overview
The microservice_table_rows feature is a specialized functionality in the NotifyBot system that automatically generates HTML table rows containing microservice data from matched inventory records. This feature is particularly useful for creating structured email reports about microservices across different sectors, regions, and clusters.
How It Works
1. Data Extraction Process
When the system processes filter conditions in multi-mode, it performs the following steps:
python# Extract field values from matched rows
field_values = extract_field_values_from_matched_rows(filter_line, field_names, INVENTORY_PATH, base_folder)
2. Automatic Table Generation
If the filter matches any rows in the inventory, the system automatically:

Collects matched rows: Stores all rows that match the current filter condition
Extracts microservice fields: Pulls specific columns from each matched row:

sector
region
clustername
namespace
microservicename
replicacount


Generates HTML table rows: Creates properly formatted HTML table rows for each matched record

3. HTML Table Row Format
Each matched microservice record becomes an HTML table row:
html<tr>
    <td style="padding: 8px; border: 1px solid #ddd;">{sector}</td>
    <td style="padding: 8px; border: 1px solid #ddd;">{region}</td>
    <td style="padding: 8px; border: 1px solid #ddd;">{clustername}</td>
    <td style="padding: 8px; border: 1px solid #ddd;">{namespace}</td>
    <td style="padding: 8px; border: 1px solid #ddd;">{microservicename}</td>
    <td style="padding: 8px; border: 1px solid #ddd;">{replicacount}</td>
</tr>
4. Template Substitution
The generated table rows are stored as a special field called microservice_table_rows that can be used in email templates:
html<!-- In your body.html template -->
<table style="border-collapse: collapse; width: 100%;">
    <thead>
        <tr style="background-color: #f5f5f5;">
            <th style="padding: 8px; border: 1px solid #ddd;">Sector</th>
            <th style="padding: 8px; border: 1px solid #ddd;">Region</th>
            <th style="padding: 8px; border: 1px solid #ddd;">Cluster</th>
            <th style="padding: 8px; border: 1px solid #ddd;">Namespace</th>
            <th style="padding: 8px; border: 1px solid #ddd;">Microservice</th>
            <th style="padding: 8px; border: 1px solid #ddd;">Replicas</th>
        </tr>
    </thead>
    <tbody>
        {microservice_table_rows}
    </tbody>
</table>
Example Workflow
Input Data (inventory.csv)
csvsector,region,clustername,namespace,microservicename,replicacount,email
prod,us-east,cluster-1,payments,payment-api,3,team-payments@company.com
prod,us-east,cluster-1,orders,order-service,2,team-payments@company.com
test,eu-west,cluster-2,payments,payment-api,1,team-payments@company.com
Filter Condition
sector=prod,region=us-east
Generated Output
The system would generate these table rows:
html<tr>
    <td style="padding: 8px; border: 1px solid #ddd;">prod</td>
    <td style="padding: 8px; border: 1px solid #ddd;">us-east</td>
    <td style="padding: 8px; border: 1px solid #ddd;">cluster-1</td>
    <td style="padding: 8px; border: 1px solid #ddd;">payments</td>
    <td style="padding: 8px; border: 1px solid #ddd;">payment-api</td>
    <td style="padding: 8px; border: 1px solid #ddd;">3</td>
</tr>
<tr>
    <td style="padding: 8px; border: 1px solid #ddd;">prod</td>
    <td style="padding: 8px; border: 1px solid #ddd;">us-east</td>
    <td style="padding: 8px; border: 1px solid #ddd;">cluster-1</td>
    <td style="padding: 8px; border: 1px solid #ddd;">orders</td>
    <td style="padding: 8px; border: 1px solid #ddd;">order-service</td>
    <td style="padding: 8px; border: 1px solid #ddd;">2</td>
</tr>
Key Features
Automatic Generation

No manual setup required: The table rows are automatically generated for any matched records
Real-time data: Always reflects the current state of the inventory

Styling

Consistent formatting: All table cells have uniform padding and borders
Email-friendly: Uses inline CSS styles for maximum email client compatibility

Integration with Multi-Mode

Per-filter tables: Each filter condition gets its own customized table
Template substitution: Works seamlessly with the placeholder system

Logging
The system provides detailed logging about table generation:
✅ Generated HTML table with 2 rows for microservices data
ℹ️ Generated microservice table with 2 rows
Use Cases

Infrastructure Reports: Show which microservices are running in specific environments
Deployment Summaries: List services that were recently deployed or updated
Resource Monitoring: Display replica counts and resource allocation across clusters
Team Notifications: Send targeted updates to teams about their specific services

Important Notes

The table rows are generated only when there are matched records
The feature specifically looks for these exact column names in the inventory
Empty fields in the inventory will appear as empty cells in the table
The table structure is fixed but can be styled through the HTML template

This feature makes it easy to create professional, structured email reports containing detailed microservice information without manual formatting.
