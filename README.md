# Cold Storage Management System

A premier, service-based cold storage and warehouse operations application engineered natively for the Frappe framework and ERPNext ecosystem.

This application is purpose-built from the ground up to empower third-party logistics (3PL) businesses, deep-freeze aggregators, and large-scale warehouse operators. It provides an unbroken, end-to-end digital workflow to meticulously manage daily inward receipts, precise internal transfers, and highly validated outward dispatches, while completely automating the notoriously complex billing cycles associated with handling fees and ongoing storage services.

## Core Features & Capabilities

### 1. Advanced Operations & Total Inventory Control
The core operations are strictly governed by three primary Doctypes, each explicitly designed to capture every necessary logistical data point:

**Cold Storage Inward (Doctype)**
Formalize the receipt of inbound shipments.
* **Fields & Purpose:**
  * `naming_series` (Select): Auto-generating ID sequence.
  * `company` (Link): The legal corporate entity managing the facility.
  * `customer` (Link): Identifies the absolute legal owner of the inbound stock.
  * `posting_date` (Date) & `posting_time` (Time): Precise chronological stamping for strict billing boundaries.
  * `warehouse` (Link): The specific ERPNext `Warehouse` facility receiving the goods.
  * `items` (Table): Child table (`Cold Storage Inward Item`) detailing:
    * `item_code` (Link): Specific product SKU.
    * `qty` (Float): The receiving pallet/box/kg amount.
    * `uom` (Link): Unit of Measure.
    * `rack` (Link): The exact `Cold Storage Rack` the stock is placed into.
    * `handling_rate` & `amount` (Currency): Granular receiving fees auto-fetched per item.
  * `total_inward_charges` (Currency): Automatically aggregated sum of handling/unloading fees.
  * `remarks` (Small Text): Warehouse operator notes for damages or variances.
  * `sales_invoice` (Link): Read-only reference to the auto-generated handling bill.
  * `stock_entry` (Link): Read-only reference validating the successful ERPNext stock ledger update.
  * `amended_from` (Link): Standard system audit field.

**Cold Storage Outward (Doctype)**
Dispatch goods with strictly enforced, algorithmic batch-validation.
* **Fields & Purpose:**
  * `naming_series` (Select): Auto-generating ID sequence.
  * `company` (Link): The corporate entity.
  * `customer` (Link): The owner requesting the dispatch.
  * `posting_date` (Date) & `posting_time` (Time): Dispatch timestamps.
  * `dispatch_address` (Link): The destination warehouse/client address.
  * `driver_name` (Data) & `vehicle_no` (Data): Critical logistical data for gate verification and manifest printing.
  * `items` (Table): Child table (`Cold Storage Outward Item`) containing:
    * `item_code` (Link), `warehouse` (Link), `qty` (Float), `uom` (Link).
    * `batch_no` (Link): Strict validation field restricting selection *only* to batches where `Batch.custom_customer` matches the Outward `customer`.
    * `rack` (Link): The specific location the picker needs to retrieve the goods from.
    * `loading_rate` & `amount` (Currency): Dispatch processing fees for labor.
  * `total_outward_charges` (Currency): Final aggregated shipping/loading fees.
  * `remarks` (Small Text): Operator dispatch notes.
  * `sales_invoice` & `stock_entry` & `amended_from` (Link): Immutable transaction references.
  * `submitted_qr_code_data_uri` (Small Text): Auto-generates a Base64 QR code upon submission for printing on dispatch labels.

**Cold Storage Transfer (Doctype)**
Facilitate internal physical relocation or logical ownership transfer of stock.
* **Fields & Purpose:**
  * `naming_series` & `company`, `posting_date`.
  * `transfer_type` (Select): Vital toggle between physical ('Location to Location') and logical ('Ownership to Ownership') transfers.
  * `total_qty` (Float): Sum of all moved pallets.
  * `total_transfer_charges` (Currency): Internal operational cost mapping.
  * `from_customer` & `to_customer` (Link): Used specifically during *Ownership* transfers to securely overwrite stock liability without physical movement.
  * `customer` (Link): The owner of the goods during a *Location* transfer.
  * `items` (Table): Child table (`Cold Storage Transfer Item`) showing the exact `batch_no` and movement from `source_warehouse`/`source_rack` to `target_warehouse`/`target_rack`.
  * `remarks`, `journal_entry`, `stock_entry`, `amended_from`.

### 2. Intelligent Space & Rack Management
* **Dynamic Storage Capacity**: The `Warehouse` doctype is extended with `custom_storage_capacity` (Float) to enforce hard volume limits.
* **Precision Floor Mapping (`Cold Storage Rack` Doctype)**: 
  * **Fields:** 
    * `rack_code` (Data): The human-readable physical label on the floor (e.g., A-14-B).
    * `warehouse` (Link): The parent temperature-controlled room.
    * `parent_rack` (Link): Allows nesting racks within logical aisles or zones.
    * `is_group` (Check): Designates if the rack is a folder (aisle) or a physical end-node.
    * `status` (Select): 'Active' or 'Maintenance'.

### 3. Automated Financials & Highly Flexible Billing
* **Dynamic Charge Configurations (`Charge Configuration` Doctype)**: 
  * **Fields:** 
    * `item_group` (Link): Broad categorizations for pricing.
    * `unloading_rate`, `handling_rate`, `loading_rate` (Currency): Discrete operational cost triggers.
    * `inter_warehouse_transfer_rate`, `intra_warehouse_transfer_rate` (Currency): Internal movement penalties or fees.
* **Simplified General Ledger Mapping (`Cold Storage Settings` Doctype)**:
  * **Fields:** `company`, `default_income_account`, `labour_account`, `labour_manager_account`, `transfer_expense_account` (Link), `charge_configurations` (Table).

### 4. Dedicated Next-Generation Client Portal
* **Real-Time Client Dashboard (`/cs-portal`)**: Elevate your customer service by providing clients with a stunning, modern, ultra-responsive Single Page Application (SPA) dashboard tailored uniquely to their daily needs.
* **Unprecedented Self-Service Visibility**: Build deep trust by allowing customers to independently monitor their available batches, view interactive item snapshots, analyze visual inventory dashboards, and review historical account statements at any hour of the day or night.
* **Actionable Remote Operations**: Empower clients to effortlessly download structured stock CSVs, generate signed statements of accounts, initiate formal new service requests, and directly retrieve invoice payment links—all without sending a single email or making a phone call to your dispatch team.
* **Zero-Touch Security Sync**: Maintain military-grade data partitioning with automated, invisible server-side scripts that transparently link external Portal Users directly to ERPNext User Permissions, rigidly filtered by Customer ID.

### 5. Multi-Channel Automated Communication
* **WhatsApp Meta API Integration**: Keep your clients continuously in the loop with zero manual effort. Configure API keys directly in `Cold Storage Settings` to trigger automated, real-time alerts dispatched directly to their WhatsApp accounts the moment critical Inward receipts or Outward dispatches are finalized on the floor.
* **Specialized Industrial Print Formats**: Equip your floor staff with highly functional, QR-code supported custom print formats engineered specifically to withstand the rigors of warehouse floors (e.g., scannable *Outward Dispatch QR*, *Inward Half A4* slips, and *Transfer QR* manifests).
* **Corporate Branding Automation**: The application automatically provisions a unified, professional `Cold Storage Branded Letter Head` from beautiful templates during the installation or database migration process, ensuring all outward-facing PDFs look immaculate.

## How it Works (The Operational Lifecycle)

1. **Phase 1: Initial Setup & Base Configuration**: The system administrator defines the fundamental `Cold Storage Settings` (financial accounts, branded letterheads), digitally maps physical capacities and racks within the Warehouses, and establishes standard pricing structures via `Charge Configuration`. Dedicated customer portal users are then minted and securely assigned the highly restricted `Cold Storage Client Portal User` role.
2. **Phase 2: Receiving Goods (The Inward Process)**: A client's freight arrives at the loading dock. A receiving operator rapidly instantiates a `Cold Storage Inward` record, meticulously documenting the specific SKUs, quantities, and their designated physical destinations (Warehouse/Rack). Instantly, the system generates new ERPNext stock batches uniquely flagged with the exact customer's ownership metadata, and automatically triggers any agreed-upon inbound processing fees into a draft Sales Invoice.
3. **Phase 3: Deep Storage & Internal Movement (The Transfer Process)**: Goods safely reside within their assigned temperature-controlled racks. Facility planners can continuously monitor the *Live Batch Stock* and *Warehouse Occupancy Timeline* dashboards. If consolidation is required to optimize freezer space, pallets can be flexibly relocated using a `Cold Storage Transfer` transaction, perfectly updating internal coordinate records without ever interrupting the customer's remote, real-time portal view.
4. **Phase 4: Fulfillment (The Outward Process)**: A client formally requests the retrieval of their goods. A `Cold Storage Outward` transaction is authorized, which activates a strict algorithmic batch-level validation—guaranteeing the warehouse picker only selects physical pallets explicitly owned by that specific customer. Once the truck is loaded and the transaction is finalized, the system generates an outward handling invoice, permanently depletes the inventory levels, and fires off a WhatsApp notification to the client confirming the successful dispatch.
5. **Phase 5: Total Transparency (The Client Experience)**: Throughout the entire lifecycle of their incredibly valuable inventory, the remote client can securely log into the `/cs-portal`. There, they experience a live, real-time snapshot of their holdings, granular transaction histories, and impending invoices, completely eliminating the need for a dedicated internal ERPNext desk user role or manual reporting runs from your busy warehouse staff.

## Command Center (Cold Storage Workspace Dashboard)

Transform raw operational data into actionable, high-level intelligence with the rich **Cold Storage Workspace Dashboard**. This intuitive interface provides executives and warehouse managers a literal bird's-eye view of both operational tempo and financial health through a suite of dynamic metrics and visualizations:

- **Top Customers Analytics**: Instantly identify and pamper your most valuable clients who are actively holding the largest inventory footprints in your facility.
- **Inward & Outward Velocity Trends**: Closely monitor the daily, weekly, and monthly flow of physical goods to proactively anticipate future staffing, forklift, and equipment requirements.
- **Internal Transfer Type Distribution**: Track the internal reorganizations and space optimizations occurring across your warehouse floor.
- **Stock Flow Sankey Diagram**: Visually map the complex, end-to-end volumetric journey of items flowing into, resting around, and eventually exiting your facility.
- **Net Movement Waterfall (Monthly)**: Graphically dissect month-over-month inventory growth or depletion to predict revenue shifts.
- **Warehouse Occupancy & Physical Utilization**: Understand exactly what percentage of your total cubic capacity is actively yielding revenue, allowing you to accurately predict when you will reach maximum operational density.
- **Receivables Aging Waterfall**: Keep a strict, visual eye on outstanding payments and billing cycles to ensure predictable and consistent cash flow.
- **Yearly Macro Inward & Outward Trend**: A sweeping 12-month trailing view analyzing your facility's annual throughput and identifying highly profitable seasonal spikes.
- **Digital Engagement Tracking**: Track detailed client login activity on the portal to gauge customer satisfaction and monitor internal system access for absolute security.

*(Note: Certain hyper-detailed analytical shortcut tiles, such as the `Cold Storage Lot Traceability Graph` and `Cold Storage Live Batch Stock`, are intentionally minimized from the default executive dashboard to keep the primary view clean, but remain immediately accessible via quick-links when granular deep dives are actively required.)*

## Comprehensive Intelligence Reports

Empower management decision-making and ensure total operational transparency with a robust suite of **19 meticulously crafted standard reports**. To provide absolute clarity on analytical capabilities, the exact filtering parameters and structural data columns generated by each report are fully detailed below:

### Core Operational Registers
1. **Cold Storage Inward Register**
   * *Purpose:* Granular logs capturing all historical receiving documents.
   * *Filters:* `company`, `customer`, `from_date`, `to_date`, `status`
   * *Columns Output:* Matches filter criteria to display chronological receipt lines.
2. **Cold Storage Outward Register**
   * *Purpose:* An irrefutable, time-stamped record of all final dispatch documents.
   * *Filters:* `company`, `customer`, `from_date`, `to_date`, `status`
   * *Columns Output:* Outputs dispatched line items matching the parameters.
3. **Cold Storage Transfer Register**
   * *Purpose:* Complete internal audit trail logging physical relocations and logical ownership swaps.
   * *Filters:* `company`, `transfer_type`, `customer` (Location transfers), `from_customer`, `to_customer` (Ownership transfers), `from_date`, `to_date`, `status`
   * *Columns Output:* Corresponds to the filtered internal movement documents.
4. **Cold Storage Customer Register**
   * *Purpose:* A centralized list of active clients managing inventory within the specified timeframe.
   * *Filters:* `company`, `customer`, `as_on_date`
   * *Columns Output:* Active client directory as of the specified date.

### Deep Inventory & Space Analytics
5. **Cold Storage Live Batch Stock**
   * *Purpose:* Up-to-the-millisecond snapshot of exact inventory residing in specific racks, partitioned aggressively by client.
   * *Filters:* `company`, `as_on_date`, `customer`, `item`, `batch_no`, `warehouse`, Toggle: `include_zero_balance`
   * *Columns Output:* Generates immediate ledger balances matching the filter matrix.
6. **Cold Storage Warehouse Utilization**
   * *Purpose:* Intelligently analyze monetized physical volume against configured capacities.
   * *Filters:* `company`, `warehouse`, `as_on_date`
   * *Columns Output:* Total utilized spatial capacity per warehouse node.
7. **Cold Storage Warehouse Occupancy Timeline**
   * *Purpose:* Track historical capacity and space trends to proactively prepare for seasonal surges.
   * *Filters:* `company`, `warehouse`, `from_date`, `to_date`
   * *Columns Output:* Time-series data of space utilization over the selected period.
8. **Cold Storage Item Movement Summary**
   * *Purpose:* Aggregate reporting analyzing velocity and turnover rates of specific items.
   * *Filters:* `company`, `item`, `from_date`, `to_date`
   * *Columns Output:* Net movement totals for the specific SKUs.
9. **Cold Storage Net Movement Waterfall Monthly**
   * *Purpose:* Sequential, highly visual analysis of monthly inventory accumulation changes.
   * *Filters:* `company`, `from_date`, `to_date`, `customer`, `item`, `warehouse`
   * *Columns Output:* Month-by-month cascading volume changes.
10. **Cold Storage Stock Flow Sankey**
    * *Purpose:* Traces overarching stock movement dynamics across the enterprise over time.
    * *Filters:* `company`, `item_group`, `from_date`, `to_date`, `top_n_groups`
    * *Columns Output:* Nodes and volumetric link strengths for the interactive visual chart.
11. **Cold Storage Yearly Inward Outward Trend**
    * *Purpose:* Trailing macro-view highlighting long-term business growth and operational tempo.
    * *Filters:* `company`, `item_group`, `from_year`, `to_year`
    * *Columns Output:* Year-over-year aggregate comparison data.

### Complete Traceability, Food Safety Compliance & Auditing
12. **Cold Storage Lot Traceability Graph**
    * *Purpose:* Visually maps the complete, unbroken physical journey of specific batches.
    * *Filters:* `company`, `customer`, `item`
    * *Columns Output:* Recursive mapping nodes bridging: `batch_no`, `warehouse`, from/to dates.
13. **Cold Storage Audit Trail Compliance Pack**
    * *Purpose:* Automated heavy-duty reporting of modified transaction records designed to satisfy safety inspectors.
    * *Filters:* None (Fixed scope, wide extraction)
    * *Columns Output:* `company`, `from_date`, `to_date`, `customer`, `item`, `batch_no`, `warehouse`, `status`, `include_user_actions`
14. **Cold Storage Client Portal Access Log**
    * *Purpose:* Irrefutable analytics proving when clients review their holdings online.
    * *Filters:* `from_date`, `to_date`, `user`, `source`
    * *Columns Output:* Access timestamps matching filter constraints.
15. **Cold Storage Login Activity Log**
    * *Purpose:* Monitor broader enterprise-wide system access for internal accountability.
    * *Filters:* `from_date`, `to_date`, `user`, `status`
    * *Columns Output:* Chronological login success/failure rows.

### Precision Financials & Billing Management
16. **Cold Storage Customer Billing Summary**
    * *Purpose:* Flawless aggregation of all handling, tracking, and deep-storage fees accrued.
    * *Filters:* `company`, `customer`, `from_date`, `to_date`
    * *Columns Output:* Period billing totals by client.
17. **Cold Storage Receivables Aging Waterfall**
    * *Purpose:* Visually highlight overdue payments across specific time buckets for cash recovery.
    * *Filters:* `company`, `customer`, `from_date`, `to_date`
    * *Columns Output:* Filtered invoice amounts cascaded by aging brackets.
18. **Cold Storage Customer Outstanding Aging**
    * *Purpose:* Exhaustively detailed breakdowns of all unpaid invoices categorized by debt age.
    * *Filters:* `company`, `customer`, `as_on_date`
    * *Columns Output:* Unpaid balances aging buckets calculated against the specified date.
19. **Cold Storage Customer Payment Follow-up Queue**
    * *Purpose:* Highly actionable, prioritized lists guiding AR teams on critical outstanding balances.
    * *Filters:* `company`, `customer`, `as_on_date`, `min_overdue_days`, `limit_rows`
    * *Columns Output:* Prioritized contact/queue rows exceeding the specified overdue limits.

## Industrial-Grade Print Formats

Streamline your physical warehouse floor operations, increase picking accuracy, and maintain a highly professional corporate appearance with custom print formats engineered specifically for heavy industrial and logistical use:
- **Cold Storage Inward Half A4**: Highly optimized, easily scannable paper receipts instantly generated for inbound truckers and clients making complex pallet deliveries.
- **Cold Storage Outward Half A4**: Crystal clear, highly legible delivery notes and outbound manifests securely handed off alongside dispatched goods.
- **Cold Storage Outward Dispatch QR & Transfer QR**: Modern, compact, dense QR-code enabled slips designed expressly for rapid, error-free physical verification by floor staff heavily utilizing rugged handheld scanners.
- **Automated Professional Branding**: The application natively provisions a unified, beautiful `Cold Storage Branded Letter Head` directly from HTML templates during the software installation or migration process, ensuring all inherently generated PDFs look completely pristine to your end customer.

## Hardened Secure Client Portal API (Whitelisted)

A phenomenally secure, tightly-controlled server-side API (`cold_storage/api/client_portal.py`) serves as the robust digital backbone for the dedicated Client Portal. It enables blisteringly fast, exclusively read-only data extraction and broad self-service capabilities without ever risking the exposure of the highly sensitive core ERPNext backend logic to the public internet:

- **Lighting-Fast Data Visibility Endpoints**: Keep the frontend SPA updated via highly-optimized calls such as `get_snapshot`, `get_available_items`, `get_available_batches`, `get_item_details`, and `get_document_details`.
- **Integrated Self-Service Actions**: Seamlessly allows clients to intuitively raise internal operational requests via `create_service_request`.
- **Heavy Data & File Download Automation**: Provides total self-service with one-click access to massive dynamic CSV exports and custom PDF document generation utilizing `download_stock_csv`, `download_movements_csv`, `download_invoices_csv`, `download_customer_statement`, `download_report_pdf`, and `download_dashboard_report`.
- **Seamless Financial Integration**: Securely retrieves Stripe or Razorpay integrated invoice URLs directly via `get_invoice_payment_link`.
- **Public Marketing Assets**: Permits unauthenticated guest downloads for general facility marketing materials via `download_brochure`.

## Uncompromising Granular Role-Based Access Control (RBAC)

Ensure absolutely strict operational accountability, limit employee liability, and enforce zero-trust security with a beautifully structured, highly granular Role-Based Access Control system. The application automatically provisions these perfectly tailored roles upon initial installation, allowing administrators to immediately assign appropriate and highly limited permissions to the warehouse workforce:

- **Cold Storage Admin**: Grants full, unrestricted God-mode administrative access to all underlying operations, system settings, global configurations, and highly sensitive financial data across the entire facility.
- **Cold Storage Warehouse Manager**: Provides intense, high-level operational oversight meant for facility directors doing capacity planning, overriding daily processes, and authorizing large-scale inter-warehouse transfers.
- **Cold Storage Inventory Controller**: Built for the masters of the real-time stock matrix; staff capable of managing internal floor transfers, updating physical location mapping, and legally reconciling stock discrepancies.
- **Cold Storage Inbound Operator**: A rigidly scoped role focused exclusively on safely executing, meticulously classifying, and accurately recording massive incoming client shipments at the receiving docks.
- **Cold Storage Dispatch Operator**: Dedicated entirely to the strict algorithmic validation, physical checking, and final dispatching of outbound goods into waiting trucks.
- **Cold Storage Billing Executive**: Financial personnel tasked specifically and solely with mapping complex charge configurations, algorithmically processing the thousands of invoices, and relentlessly managing payment follow-ups.
- **Cold Storage Quality Inspector**: A crucial role responsible for independently verifying the objective standard, holding temperature, and overall safety of goods moving through the vital inspection checkpoints of the facility.
- **Cold Storage Maintenance Technician**: Distinct facility staff tasked explicitly with the physical upkeep of the heavy racks, forklifts, machinery, and life-critical refrigeration units.
- **Cold Storage Client Portal User**: Expected to be the most widely utilized role by far—an incredibly restricted, highly customized permission level permanently assigned exclusively to external customers solely for remote portal access.

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
