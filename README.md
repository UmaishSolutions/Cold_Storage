# Cold Storage

A comprehensive, service-based cold storage and warehouse operations application built natively for the Frappe and ERPNext ecosystem.

This application is purpose-built for third-party logistics (3PL) businesses and warehouse operators who store goods securely on behalf of multiple clients. It provides a seamless, end-to-end workflow to manage daily inward, outward, and transfer movements, while effortlessly automating the complex billing cycles associated with handling and ongoing storage services.

## Core Features

### 1. Advanced Operations & Inventory Management
* **Cold Storage Inward**: Formalize and streamline the receipt of customer-owned goods. Easily record incoming items, quantities, and precisely assign them to designated warehouses and specific physical racks.
* **Cold Storage Outward**: Dispatch goods with absolute confidence. The outward process enforces strict, automated batch-level validation, ensuring that dispatchers only select and move inventory that definitively belongs to the requesting customer.
* **Cold Storage Transfer**: Facilitate the internal relocation of stock. Move items smoothly between different warehouses or specific rack locations without losing tracking history or disrupting client visibility.
* **Granular Ownership Control**: Leveraging ERPNext's robust batch masters, the app introduces rigid ownership tracking. The custom `Batch.custom_customer` link ensures absolute isolation of client stock, preventing the accidental mixing or dispatching of other clients' goods.

### 2. Intelligent Space & Rack Management
* **Storage Capacity Tracking**: Gain real-time visibility into your facility's utilization. Set, monitor, and enforce physical storage limits at the individual warehouse level using `Warehouse.custom_storage_capacity`.
* **Precision Rack Tracking**: Organize your floor space logically with hierarchical rack allocation via the `Cold Storage Rack` doctype. To maintain absolute operational accuracy, precise rack selection is mandatory across all Inward, Outward, and Transfer item rows.

### 3. Automated Billing & Flexible Pricing
* **Charge Configurations**: Define highly adaptable, item-group level service and storage rates using the `Charge Configuration` table, catering to diverse client agreements.
* **Automated Invoicing**: Eliminate manual data entry. The system dynamically generates and calculates ERPNext Sales Invoices for transaction handling (Inward/Outward) and recurring ongoing storage services.
* **Integrated Payment Links**: Accelerate your revenue cycle with built-in support to extract and seamlessly send payment links for linked Sales Invoices directly to your clients.
* **Financial Settings**: Simplify accounting by configuring default income, labour, and transfer expense accounts directly within `Cold Storage Settings`.

### 4. Dedicated Client Portal
* **Real-Time Client Dashboard (`/cs-portal`)**: Provide your customers with a modern, read-only Single Page Application (SPA) tailored specifically for their needs.
* **Unprecedented Visibility**: Allow customers to independently view available batches, item snapshots, visual dashboards, account statements, and past invoices at any time.
* **Self-Service Actions**: Empower clients to download stock CSVs, generate statement of accounts, initiate new service requests, and directly retrieve invoice payment links.
* **Seamless Permission Sync**: Maintain strict data security with automated, server-side scripts that transparently link Portal Users directly to ERPNext User Permissions filtered by Customer.

### 5. Multi-Channel Communication
* **WhatsApp Meta API Integration**: Keep your clients informed with automated, real-time alerts dispatched directly to their WhatsApp for critical Inward and Outward state changes.
* **Specialized Print Formats**: Utilize highly functional, QR-code supported custom print formats engineered for warehouse floors (e.g., *Outward Dispatch QR*, *Inward Half A4*, *Transfer QR*).
* **Professional Branding**: Automatically provisions a `Cold Storage Branded Letter Head` from beautiful templates during the installation or migration process.

## How it Works (The Operational Workflow)

1. **Initial Setup & Configuration**: The system administrator defines `Cold Storage Settings` (accounts, letterheads), configures physical capacities and racks within Warehouses, and establishes standard pricing structures via `Charge Configuration`. Dedicated customer portal users are then generated and securely assigned the `Cold Storage Client Portal User` role.
2. **Receiving Stock (The Inward Process)**: A customer delivers goods to the facility. An operator rapidly creates a `Cold Storage Inward` record, documenting the specific items, quantities, and their designated physical destination (Warehouse/Rack). The system automatically generates new stock batches flagged with the exact customer's ownership details, and instantly triggers any agreed-upon inward processing charges into a new Sales Invoice.
3. **Tracking & Movement (The Transfer Process)**: Stock is safely stored within its assigned racks. Facility planners can continuously review the *Live Batch Stock* and *Warehouse Occupancy Timeline*. If reorganization is needed, stock can be flexibly relocated within the premises using `Cold Storage Transfer`, updating internal records without interrupting the customer's remote, real-time view.
4. **Dispatching Stock (The Outward Process)**: A customer requests the retrieval of their items. A `Cold Storage Outward` transaction is initiated, which mandates strict batch-level validation—guaranteeing the local agent only selects goods owned by that specific customer. Once completed and verified, it generates an outward handling invoice, permanently reduces the stock levels, and optionally sends a WhatsApp notification to the client confirming the dispatch.
5. **Transparency & Portals (The Client Experience)**: Throughout the entire lifecycle of their inventory, the remote client can securely log into `/cs-portal`. Here, they experience a real-time snapshot of their holdings and full transaction history, all without requiring a dedicated internal ERPNext desk user role or manual reporting from the warehouse staff.

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
