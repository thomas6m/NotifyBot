import csv
# Field values
# region:North,East,West,South
# env:prod,dev,test
# department:IT,HR,Finance,Sales
# role:Developer,Manager,Analyst,SalesRep,SysAdmin,Assistant,CFO
# clustername:
# Sample data for inventory with multiple emails per row, using semicolons as separators
inventory_data = [
    ["region", "env", "clustername", "department", "role", "email"],
    ["North", "prod", "cluster-a", "IT", "Developer", 'john.doe@email.com;jane.smith@email.com;bob.white@email.com'],
    ["East", "dev", "cluster-b", "HR", "Manager", 'jane.smith@email.com;alice.jones@email.com'],
    ["West", "test", "cluster-c", "Finance", "Analyst", 'john.doe@email.com;bob.white@email.com'],
    ["South", "prod", "cluster-d", "Sales", "SalesRep", 'alice.jones@email.com;john.doe@email.com'],
    ["North", "dev", "cluster-e", "IT", "Developer", 'bob.white@email.com;jane.smith@email.com'],
    ["East", "test", "cluster-f", "HR", "Assistant", 'jane.smith@email.com;alice.jones@email.com'],
    ["West", "prod", "cluster-g", "Finance", "CFO", 'charles.lee@email.com;john.doe@email.com'],
    ["South", "test", "cluster-h", "Sales", "SalesRep", 'bob.white@email.com;alice.jones@email.com'],
    ["North", "prod", "cluster-i", "IT", "SysAdmin", 'john.doe@email.com;bob.white@email.com'],
    ["East", "dev", "cluster-j", "HR", "Manager", 'jane.smith@email.com;john.doe@email.com'],
    ["West", "test", "cluster-k", "Finance", "Analyst", 'john.doe@email.com;jane.smith@email.com'],
    ["South", "prod", "cluster-l", "Sales", "SalesRep", 'alice.jones@email.com;bob.white@email.com'],
    ["North", "dev", "cluster-m", "IT", "Developer", 'bob.white@email.com;jane.smith@email.com'],
    ["East", "test", "cluster-n", "HR", "Assistant", 'jane.smith@email.com;alice.jones@email.com'],
    ["West", "prod", "cluster-o", "Finance", "CFO", 'charles.lee@email.com;john.doe@email.com'],
    ["South", "test", "cluster-p", "Sales", "SalesRep", 'bob.white@email.com;alice.jones@email.com'],
    ["North", "prod", "cluster-q", "IT", "SysAdmin", 'john.doe@email.com;bob.white@email.com'],
    ["East", "dev", "cluster-r", "HR", "Manager", 'jane.smith@email.com;john.doe@email.com'],
    ["West", "test", "cluster-s", "Finance", "Analyst", 'john.doe@email.com;bob.white@email.com'],
    ["South", "prod", "cluster-t", "Sales", "SalesRep", 'alice.jones@email.com;jane.smith@email.com'],
    ["North", "dev", "cluster-u", "IT", "Developer", 'bob.white@email.com;john.doe@email.com'],
    ["East", "test", "cluster-v", "HR", "Assistant", 'jane.smith@email.com;alice.jones@email.com'],
    ["West", "prod", "cluster-w", "Finance", "CFO", 'charles.lee@email.com;bob.white@email.com'],
    ["South", "test", "cluster-x", "Sales", "SalesRep", 'bob.white@email.com;jane.smith@email.com'],
    ["North", "prod", "cluster-y", "IT", "SysAdmin", 'john.doe@email.com;bob.white@email.com'],
    ["East", "dev", "cluster-z", "HR", "Manager", 'jane.smith@email.com;alice.jones@email.com'],
    ["West", "test", "cluster-aa", "Finance", "Analyst", 'john.doe@email.com;jane.smith@email.com'],
    ["South", "prod", "cluster-ab", "Sales", "SalesRep", 'alice.jones@email.com;bob.white@email.com'],
    ["North", "dev", "cluster-ac", "IT", "Developer", 'bob.white@email.com;john.doe@email.com'],
    ["East", "test", "cluster-ad", "HR", "Assistant", 'jane.smith@email.com;alice.jones@email.com'],
    ["West", "prod", "cluster-ae", "Finance", "CFO", 'charles.lee@email.com;bob.white@email.com'],
    ["South", "test", "cluster-af", "Sales", "SalesRep", 'bob.white@email.com;jane.smith@email.com']
]

# Writing to CSV file with semicolon-separated emails
with open('inventory_multiple_emails_semi_colon.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(inventory_data)

print("CSV file 'inventory_multiple_emails_semi_colon.csv' has been generated successfully.")
