# Cold Storage

Cold Storage is a Frappe/ERPNext app for service-based warehouse operations where goods are stored for customers and billed for storage handling services.

## What the App Includes

- End-to-end transaction flows:
  - `Cold Storage Inward` (receipt)
  - `Cold Storage Outward` (dispatch)
  - `Cold Storage Transfer` (ownership and location transfers)
- Automated posting:
  - Stock Entries for movement
  - Sales Invoices for chargeable services
  - Journal Entries for labor/transfer accounting flows
- Strict customer ownership enforcement on `Batch` via `Batch.custom_customer`
- Company-scoped validation for warehouses/accounts/cost centers
- Company abbreviation based naming series for operational and accounting documents
- Modern full-width client portal at `/client-portal`
- Report exports from portal (CSV and PDF for selected reports)
- Workspace with grouped sidebar sections, charts, number cards, and report links
- Role/Role Profile/DocType permission sync automation
- Automatic customer-based `User Permission` provisioning for portal users

## Core DocTypes

- `Cold Storage Settings` (Single)
- `Charge Configuration` (Child table in settings)
- `Cold Storage Inward` + `Cold Storage Inward Item`
- `Cold Storage Outward` + `Cold Storage Outward Item`
- `Cold Storage Transfer` + `Cold Storage Transfer Item`

## Reports

- `Cold Storage Inward Register`
- `Cold Storage Outward Register`
- `Cold Storage Transfer Register`
- `Cold Storage Customer Register`
- `Cold Storage Warehouse Utilization`
- `Cold Storage Warehouse Occupancy Timeline`
- `Cold Storage Yearly Inward Outward Trend`

## Print Formats

- `Cold Storage Inward Receipt QR`
- `Cold Storage Outward Dispatch QR`
- `Cold Storage Transfer QR`

## Roles and Access

Managed by code (`cold_storage.setup.role_based_access.sync_role_based_access`):

- `Cold Storage Admin`
- `Cold Storage Warehouse Manager`
- `Cold Storage Inbound Operator`
- `Cold Storage Dispatch Operator`
- `Cold Storage Inventory Controller`
- `Cold Storage Billing Executive`
- `Cold Storage Client Portal User`
- `Cold Storage Quality Inspector`
- `Cold Storage Maintenance Technician`

Client portal access:

- Allowed: `Cold Storage Client Portal User`, `Cold Storage Admin`, `System Manager`
- Customer users are customer-scoped through `User Permission` records on `Customer`
- Admin/System Manager can view global scope and filter by customer in portal

## Requirements

- Frappe Bench
- ERPNext (required app)
- Python `3.14+` (from `pyproject.toml`)

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/UmaishSolutions/Cold_Storage.git
bench --site <site-name> install-app cold_storage
bench --site <site-name> migrate
bench --site <site-name> clear-cache
```

## Post-Install Checklist

1. Open `Cold Storage Settings` and configure:
   - Default Company
   - Default Income Account
   - Labour Account (Debit)
   - Labour Manager Account (Credit)
   - Transfer Expense Account
   - Charge Configurations per Item Group
2. Confirm `Warehouse.custom_storage_capacity` values for utilization/occupancy analytics.
3. Assign relevant Cold Storage Role Profiles to users.
4. For portal users, map customer(s) through:
   - `Customer > portal_users`, or
   - customer email/contact mapping

## Operational Sync Commands

If you need to re-apply security and portal mappings:

```bash
cd $PATH_TO_YOUR_BENCH
bench --site <site-name> execute cold_storage.setup.role_based_access.sync_role_based_access
bench --site <site-name> execute cold_storage.setup.client_portal_user_permissions.sync_customer_user_permissions_for_client_portal_users
bench --site <site-name> clear-cache
```

## Local Development

```bash
cd apps/cold_storage
pre-commit install
pre-commit run --all-files
```

Run tests:

```bash
cd $PATH_TO_YOUR_BENCH
bench --site <site-name> set-config allow_tests true
bench --site <site-name> run-tests --app cold_storage
```

## Troubleshooting

- Install error: `Could not find Default UOM: Nos`
  - Run `bench --site <site-name> migrate` to apply current post-install/migration handlers.
  - Ensure at least one enabled UOM exists.
- Portal user cannot see records:
  - Verify user has `Cold Storage Client Portal User`.
  - Verify user has Customer `User Permission` records.
  - Re-run the sync commands above.
- Permission matrix drift after manual permission edits:
  - Re-run `sync_role_based_access` command above.

## CI Workflows

- `ci.yml`: installs app on a fresh bench and runs tests
- `linter.yml`: pre-commit, Semgrep, and dependency audit checks

## License

MIT. See `LICENSE` and `license.txt`.
