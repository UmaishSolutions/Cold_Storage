# Cold Storage Management System

A premier, service-based cold storage and warehouse operations application engineered natively for the Frappe framework and ERPNext ecosystem.

This application is purpose-built from the ground up to empower third-party logistics (3PL) businesses, deep-freeze aggregators, and large-scale warehouse operators. It provides an unbroken, end-to-end digital workflow to meticulously manage daily inward receipts, precise internal transfers, and highly validated outward dispatches, while completely automating the notoriously complex billing cycles associated with handling fees and ongoing storage services.

## Core Features & Capabilities

### 1. Advanced Operations & Total Inventory Control
* **Cold Storage Inward**: Formalize and accelerate the receipt of massive inbound shipments. Swiftly document arriving items, assess quantities, and instantly allocate them to designated physical warehouses and specific, highly-optimized rack locations to maximize spatial efficiency.
* **Cold Storage Outward**: Dispatch goods with zero margin for error. The outward process utilizes a strict, system-enforced batch-level validation matrix, absolutely ensuring that your floor staff only picks, packs, and dispatches inventory that definitively belongs to the requesting customer.
* **Cold Storage Transfer**: Facilitate the seamless internal relocation of stock. Swiftly pivot operations by moving items between varying temperature zones, different warehouses, or strategic rack locations without ever losing the audit trail or disrupting your client's real-time visibility.
* **Uncompromising Ownership Tracking**: Leveraging ERPNext's robust batch masters, the app introduces an ironclad ownership paradigm. By rigidly linking `Batch.custom_customer` at the database level, it guarantees total isolation of client stock, completely eliminating the catastrophic risk of accidentally mixing or misdispatching neighboring clients' inventory.

### 2. Intelligent Space & Rack Management
* **Dynamic Storage Capacity Tracking**: Gain unprecedented, real-time visibility into your facility's physical utilization. Define, monitor, and strictly enforce storage volume limits at the individual warehouse level using the native `Warehouse.custom_storage_capacity` integration.
* **Precision Floor Mapping & Rack Tracking**: Digitally map your entire warehouse floor with intuitive, hierarchical rack allocations via the `Cold Storage Rack` architecture. To maintain absolute operational integrity and picking speed, accurate rack selection is strictly mandated across all Inward, Outward, and Transfer item rows.

### 3. Automated Financials & Highly Flexible Billing
* **Dynamic Charge Configurations**: Empower your sales team to negotiate diverse contracts. Define highly adaptable, item-group level service rates and recurring storage fees using the versatile `Charge Configuration` engine.
* **Frictionless Invoicing Engine**: Eliminate days of manual data entry and human mathematical errors. The system dynamically generates native ERPNext Sales Invoices, calculating exact totals for point-in-time transaction handling (Inward/Outward movements) and recurring, time-based storage services.
* **Integrated Payment Acceleration**: Dramatically accelerate your revenue cycle. The app features built-in support to instantly extract and seamlessly dispatch secure payment links for generated Sales Invoices directly to your clients' inboxes or phones.
* **Simplified General Ledger Mapping**: Maintain pristine accounting records by centrally configuring default income streams, direct labour costs, and internal transfer expense mapping directly within the `Cold Storage Settings` console.

### 4. Dedicated Next-Generation Client Portal
* **Real-Time Client Dashboard (`/cs-portal`)**: Elevate your customer service by providing clients with a stunning, modern, ultra-responsive Single Page Application (SPA) dashboard tailored uniquely to their daily needs.
* **Unprecedented Self-Service Visibility**: Build deep trust by allowing customers to independently monitor their available batches, view interactive item snapshots, analyze visual inventory dashboards, and review historical account statements at any hour of the day or night.
* **Actionable Remote Operations**: Empower clients to effortlessly download structured stock CSVs, generate signed statements of accounts, initiate formal new service requests, and directly retrieve invoice payment links—all without sending a single email or making a phone call to your dispatch team.
* **Zero-Touch Security Sync**: Maintain military-grade data partitioning with automated, invisible server-side scripts that transparently link external Portal Users directly to ERPNext User Permissions, rigidly filtered by Customer ID.

### 5. Multi-Channel Automated Communication
* **WhatsApp Meta API Integration**: Keep your clients continuously in the loop with zero manual effort. The system triggers automated, real-time alerts dispatched directly to their WhatsApp accounts the moment critical Inward receipts or Outward dispatches are finalized on the floor.
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

Empower your management decision-making, survive rigorous compliance auditing, and guarantee total operational transparency with a robust suite of **19 meticulously crafted standard reports**. These are specifically designed from the ground up to address the unique logistical, trace-and-track, and financial needs of modern 3PL and cold storage operators:

### Core Operational Registers
1. **Cold Storage Inward Register**: Highly detailed, granular logs of absolutely all received goods, permanently capturing arrival timestamps, handling quantities, and immutable client associations.
2. **Cold Storage Outward Register**: An irrefutable, time-stamped record of all final dispatches, legally proving exactly what left the building, when, and for whom.
3. **Cold Storage Transfer Register**: A complete internal audit trail logging the exact physical relocation of pallets between different racks and separate warehouses.
4. **Cold Storage Customer Register**: A centralized, easily searchable directory of the active clients you securely manage inventory for.

### Deep Inventory & Space Analytics
5. **Cold Storage Live Batch Stock**: An up-to-the-millisecond, real-time snapshot of precisely what inventory is presently sitting in which exact rack, partitioned aggressively by client ownership.
6. **Cold Storage Warehouse Utilization**: Intelligently analyze how effectively your physical, temperature-controlled volume is actually being monetized.
7. **Cold Storage Warehouse Occupancy Timeline**: Track historical capacity and space trends to proactively prepare your sales staff for impending seasonal surges.
8. **Cold Storage Item Movement Summary**: High-level aggregate reporting analyzing the velocity and rapid turnover rates of specific, highly volatile item groups.
9. **Cold Storage Net Movement Waterfall Monthly**: A sequential, highly visual analysis of monthly inventory accumulation changes and overarching stock flow dynamics.
10. **Cold Storage Stock Flow Sankey**: Trace the sprawling, overarching movement dynamics of your stock from end to end across your entire enterprise.
11. **Cold Storage Yearly Inward Outward Trend**: A smooth, 12-month trailing view highlighting your overarching operational tempo and identifying long-term business growth.

### Complete Traceability, Food Safety Compliance & Auditing
12. **Cold Storage Lot Traceability Graph**: A profoundly powerful visual tool engineered to trace the complete, unbroken lineage and physical journey of a specific batch from the moment it arrived at the dock to its final outbound dispatch.
13. **Cold Storage Audit Trail Compliance Pack**: Critical, automated heavy-duty reporting designed specifically to satisfy incredibly strict government regulatory bodies, food safety inspectors, and internal compliance officers.
14. **Cold Storage Client Portal Access Log**: An irrefutable, timestamped log proving precisely when and how frequently specific clients are actively reviewing their holdings online.
15. **Cold Storage Login Activity Log**: Monitor broader, enterprise-wide system access for comprehensive IT security, user auditing, and internal accountability.

### Precision Financials & Billing Management
16. **Cold Storage Customer Billing Summary**: A flawlessly clean aggregation of all handling, cross-docking, tracking, and deep-storage fees accrued by individual clients during any specified fiscal period.
17. **Cold Storage Receivables Aging Waterfall**: Visually highlight severely overdue payments across specific time buckets to drastically accelerate your finance team's cash recovery efforts.
18. **Cold Storage Customer Outstanding Aging**: Exhaustively detailed, client-by-client breakdowns of all unpaid invoices distinctly categorized by the exact age of the debt.
19. **Cold Storage Customer Payment Follow-up Queue**: Highly actionable, prioritized lists directly guiding your accounts receivable team on exactly who to contact today regarding critically outstanding balances.

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
