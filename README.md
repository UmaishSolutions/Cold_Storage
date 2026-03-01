# Cold Storage

Service-based cold storage operations app for Frappe/ERPNext.

This app is built for warehouses that store goods on behalf of customers, run inward/outward/transfer operations, and bill for storage/handling services.

## Features

### 1. Operations & Inventory Management
* **Cold Storage Inward**: Formalize the receipt of customer-owned goods into specific warehouses and racks.
* **Cold Storage Outward**: Dispatch goods, strictly checking batch availability for the respective customer.
* **Cold Storage Transfer**: Internal movement of stock between warehouses or racks.
* **Granular Ownership Control**: ERPNext batch masters are heavily utilized; `Batch.custom_customer` ensures absolute isolation of client stock.

### 2. Space & Rack Management
* **Storage Capacity**: Track storage limits at the warehouse level (`Warehouse.custom_storage_capacity`).
* **Rack Tracking**: Hierarchical rack allocation per warehouse via the `Cold Storage Rack` doctype. Allocate precise rack locations for stored items in inward transactions.

### 3. Automated Billing & Pricing
* **Charge Configurations**: Define item-group level service/storage rates using the `Charge Configuration` table.
* **Automated Invoicing**: Generation of ERPNext Sales Invoices dynamically calculated against Inward, Outward or ongoing storage services.
* **Payment Link Generation**: Built-in support to extract and send payment links for linked Sales Invoices directly to clients.
* **Financial Settings**: Configurable default income, labour, and transfer expense accounts in `Cold Storage Settings`.

### 4. Client Portal
* **Dedicated SPA Portal (`/cs-portal`)**: Real-time read-only view tailored for clients.
* **Visibility**: Customers can view available batches, item snapshots, dashboards, statements and invoices.
* **Actionable**: Option to download stock CSVs, statement of accounts, create service requests, and retrieve invoice payment links.
* **Permission Sync**: Seamless server-side script linking Portal Users directly to ERPNext User Permissions by Customer.

### 5. Multi-Channel Communication
* **WhatsApp Meta API Integration**: Automated alerts to clients for Inward/Outward state changes.
* **Specialized Print Formats**: QR-code supported custom print formats (e.g., *Outward Dispatch QR*, *Inward Half A4*, *Transfer QR*).
* provisions `Cold Storage Branded Letter Head` from templates during install/migrate.

## How it Works (Workflow)

1. **Initial Setup**: Administrator sets up `Cold Storage Settings` (accounts, templates), configures capacities and racks in Warehouses, and establishes standard `Charge Configuration` pricing structures. Customer portal users are generated and assigned the `Cold Storage Client Portal User` role.
2. **Receiving Stock (Inward)**: Customer delivers goods. An operator creates a `Cold Storage Inward` record documenting item, quantity, and designated destination (Warehouse/Rack). System creates the stock batches flagged with the exact customer's ownership details, and triggers any setup inward processing charges into a new Sales Invoice.
3. **Tracking & Movement (Transfer)**: Stock safely sits in racks. Planners can review the *Live Batch Stock* and *Warehouse Occupancy Timeline*. Using `Cold Storage Transfer`, stock can be flexibly relocated within the premises without interrupting the customer's remote view.
4. **Dispatching Stock (Outward)**: Customer requests items out. A `Cold Storage Outward` requires batch-level validation ensuring the agent only selects goods owned by that specific customer. Once completed, it generates an outward handling invoice, reduces the stock levels, and optionally WhatsApp-notifies the client.
5. **Transparency & Portals**: Throughout the lifecycle, the remote client logs into `/cs-portal`, seeing their real-time snapshot and transaction history without needing an internal ERPNext desk user role.

## Dashboard (Cold Storage workspace)

Current workspace dashboard includes number cards and charts, including:

- Top Customers
- Inward Quantity Trend
- Outward Quantity Trend
- Transfer Type Distribution
- Stock Flow Sankey
- Net Movement Waterfall (Monthly)
- Warehouse Occupancy Timeline
- Warehouse Utilization
- Yearly Inward Outward Trend
- Receivables Aging Waterfall
- Client Portal Views
- Login Activity

Current default state: shortcut tiles for
`Cold Storage Login Activity Log`,
`Cold Storage Client Portal Access Log`,
`Cold Storage Live Batch Stock`,
`Cold Storage Lot Traceability Graph`
are removed from the workspace dashboard content.

## Reports

The app currently ships **19** standard reports:

1. Cold Storage Inward Register
2. Cold Storage Outward Register
3. Cold Storage Transfer Register
4. Cold Storage Customer Register
5. Cold Storage Warehouse Utilization
6. Cold Storage Warehouse Occupancy Timeline
7. Cold Storage Yearly Inward Outward Trend
8. Cold Storage Live Batch Stock
9. Cold Storage Net Movement Waterfall Monthly
10. Cold Storage Audit Trail Compliance Pack
11. Cold Storage Client Portal Access Log
12. Cold Storage Login Activity Log
13. Cold Storage Lot Traceability Graph
14. Cold Storage Stock Flow Sankey
15. Cold Storage Receivables Aging Waterfall
16. Cold Storage Customer Billing Summary
17. Cold Storage Customer Outstanding Aging
18. Cold Storage Customer Payment Follow-up Queue
19. Cold Storage Item Movement Summary

## Print formats

- Cold Storage Inward Half A4
- Cold Storage Outward Half A4
- Cold Storage Outward Dispatch QR
- Cold Storage Transfer QR

The app also provisions `Cold Storage Branded Letter Head` from templates during install/migrate.

## Client portal API (whitelisted)

From `cold_storage/api/client_portal.py`:

- `get_snapshot`
- `create_service_request`
- `get_document_details`
- `get_available_items`
- `get_available_batches`
- `get_item_details`
- `download_stock_csv`
- `download_movements_csv`
- `download_invoices_csv`
- `download_customer_statement`
- `get_invoice_payment_link`
- `download_report_pdf`
- `download_dashboard_report`
- `download_brochure` (guest allowed)

## Roles

Standard Cold Storage roles in fixtures:

- Cold Storage Admin
- Cold Storage Warehouse Manager
- Cold Storage Inbound Operator
- Cold Storage Dispatch Operator
- Cold Storage Inventory Controller
- Cold Storage Billing Executive
- Cold Storage Client Portal User
- Cold Storage Quality Inspector
- Cold Storage Maintenance Technician

## Installation

Prerequisites:

- Frappe Bench
- ERPNext installed on the site
- Python `>=3.14`

Install:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/UmaishSolutions/Cold_Storage.git
bench --site <site-name> install-app cold_storage
bench --site <site-name> migrate
bench --site <site-name> clear-cache
```

## Post-install checklist

1. Configure `Cold Storage Settings`:
   - Company
   - Default Income Account
   - Labour and Labour Manager Accounts
   - Transfer Expense Account
   - Charge configurations
2. Set `Warehouse.custom_storage_capacity` for active warehouses.
3. Create racks per warehouse from Warehouse form:
   - **Create Cold Storage Rack** (single rack)
   - **Create Cold Storage Racks** (bulk creation)
   - Rack master is for in-warehouse location mapping only.
   - Warehouse utilization and storage-capacity math remain unchanged.
4. Assign Cold Storage role profiles to users.
5. Configure portal users (customer-linked users/permissions).
6. Optional: configure WhatsApp credentials and templates in settings.

## Operations commands

Re-sync roles and portal mappings:

```bash
bench --site <site-name> execute cold_storage.setup.role_based_access.sync_role_based_access
bench --site <site-name> execute cold_storage.setup.client_portal_user_permissions.sync_customer_user_permissions_for_client_portal_users
bench --site <site-name> clear-cache
```

## Migrations and patches

`patches.txt` currently contains **8** post-model-sync patch entries (`v0_0_2` to `v0_0_9`).

## Development

```bash
cd apps/cold_storage
pre-commit install
pre-commit run --all-files
```

If `pre-commit` fails while creating the Node hook environment, install Node first and re-run:

```bash
nvm install --lts
nvm use --lts
pre-commit clean
pre-commit run --all-files
```

Run tests:

```bash
bench --site <site-name> set-config allow_tests true
bench --site <site-name> run-tests --app cold_storage
```

## Project structure

```text
cold_storage/
├── cold_storage/
│   ├── api/                         # portal + export APIs
│   ├── cold_storage/
│   │   ├── doctype/
│   │   ├── dashboard_chart/
│   │   ├── number_card/
│   │   ├── page/
│   │   ├── print_format/
│   │   ├── report/
│   │   └── workspace/
│   ├── config/
│   ├── events/
│   ├── fixtures/
│   ├── patches/
│   ├── public/
│   ├── setup/
│   ├── templates/
│   ├── workspace_sidebar/
│   └── www/
├── pyproject.toml
└── README.md
```

## License

MIT

## GitHub Publishing Checklist

Use this when publishing or transferring the repository:

1. Push the default branch and set it in GitHub repository settings (`main` or `develop`).
2. Enable branch protection for the default branch:
   - require pull request before merge
   - require status checks (`CI`, `Linters`)
   - block force pushes and deletions
3. Enable Dependabot alerts and Dependabot security updates.
4. Enable secret scanning and push protection (if available on your plan).
5. Add repository topics and a short description so the project is discoverable.
6. Confirm these community files are visible in GitHub:
   - `README.md`
   - `LICENSE`
   - `CONTRIBUTING.md`
   - `SECURITY.md`
   - `CODE_OF_CONDUCT.md`
