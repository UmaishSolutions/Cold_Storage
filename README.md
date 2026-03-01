# Cold Storage

Service-based cold storage operations app for Frappe/ERPNext.

This app is built for warehouses that store goods on behalf of customers, run inward/outward/transfer operations, and bill for storage/handling services.

## What the app currently includes

- Core transactions:
  - `Cold Storage Inward`
  - `Cold Storage Outward`
  - `Cold Storage Transfer`
- Settings and pricing:
  - `Cold Storage Settings` (company, accounts, WhatsApp, portal announcement, terms)
  - `Charge Configuration` child table for item-group rates
- Ownership and capacity controls:
  - `Batch.custom_customer`
  - `Warehouse.custom_storage_capacity`
  - Rack master support through `Cold Storage Rack` linked to each warehouse
  - Inward rows can select rack only from the selected warehouse
- Portal:
  - `/cs-portal` single-page portal UI
  - Server API in `cold_storage/api/client_portal.py`
- Role and access sync:
  - code-managed roles + role profiles
  - client portal customer user-permission sync
- Print and communication:
  - 4 standard print formats (QR-focused)
  - branded letterhead setup during install/migrate
  - Meta WhatsApp integration for Inward/Outward notifications

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
