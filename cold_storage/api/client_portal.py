# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Final
from urllib.parse import quote, urlencode

import frappe
from frappe import _
from frappe.desk.query_report import run as run_query_report
from frappe.utils import add_days, cint, cstr, flt, getdate, now_datetime, nowdate
from frappe.utils.data import escape_html, format_datetime, formatdate
from frappe.utils.pdf import get_pdf

from cold_storage.setup.client_portal_user_permissions import (
	CLIENT_PORTAL_ROLE,
	get_customers_for_portal_user,
)

DEFAULT_LIMIT: Final[int] = 20
MAX_LIMIT: Final[int] = 1000
ADMIN_ROLE: Final[str] = "Cold Storage Admin"
SYSTEM_MANAGER_ROLE: Final[str] = "System Manager"
REPORTS_WITH_CUSTOMER_FILTER: Final[set[str]] = {
	"Cold Storage Inward Register",
	"Cold Storage Outward Register",
	"Cold Storage Transfer Register",
}
PORTAL_REPORT_DEFINITIONS: Final[tuple[dict[str, str], ...]] = (
	{
		"report_name": "Cold Storage Inward Register",
		"label": "Inward Register",
		"description": "Receipts and inward movement records.",
	},
	{
		"report_name": "Cold Storage Outward Register",
		"label": "Outward Register",
		"description": "Dispatch activity and outward movement records.",
	},
	{
		"report_name": "Cold Storage Transfer Register",
		"label": "Transfer Register",
		"description": "Internal and ownership transfer records.",
	},
	{
		"report_name": "Cold Storage Warehouse Occupancy Timeline",
		"label": "Warehouse Occupancy Timeline",
		"description": "Month-wise occupancy trend and capacity health across warehouses.",
	},
	{
		"report_name": "Cold Storage Warehouse Utilization",
		"label": "Warehouse Utilization",
		"description": "As-on-date warehouse utilization, remaining capacity, and status.",
	},
	{
		"report_name": "Cold Storage Yearly Inward Outward Trend",
		"label": "Yearly Inward/Outward Trend",
		"description": "Year-over-year inward vs outward movement trend by item group.",
	},

)



@frappe.whitelist()
def get_snapshot(limit: int = DEFAULT_LIMIT, customer: str | None = None) -> dict:
	"""Return customer-filtered stock, movement, invoice and report data for the portal."""
	row_limit = _sanitize_limit(limit)
	_ensure_client_portal_access()
	customers, available_customers, selected_customer = _resolve_customer_scope(customer)

	if not customers:
		return {
			"available_customers": available_customers,
			"selected_customer": selected_customer,
			"customers": [],
			"stock": [],
			"movements": [],
			"invoices": [],
			"reports": [],
			"announcement": None,
			"company_name": frappe.db.get_single_value("Cold Storage Settings", "company") or "",
			"analytics": {
				"stock_composition": [],
				"movement_trends": {"labels": [], "datasets": []}
			},
			"total_outstanding": 0.0
		}

	stock_rows = _get_stock_rows(customers, max(row_limit, 50))
	movement_rows = _get_movement_rows(customers, row_limit)
	invoice_rows = _get_invoice_rows(customers, row_limit)
	report_rows = _get_report_links(selected_customer)
	total_outstanding = _get_total_outstanding(customers)

	available_customers = _dedupe_strings(available_customers)
	customers = _dedupe_strings(customers)
	stock_rows = _dedupe_stock_rows(stock_rows)
	movement_rows = _dedupe_movement_rows(movement_rows)
	invoice_rows = _dedupe_invoice_rows(invoice_rows)
	report_rows = _dedupe_report_rows(report_rows)

	# Chart Data: Top Batches by Stock Qty
	# Aggregate by batch_no
	batch_qty_map = {}
	for r in stock_rows:
		batch = r.get("batch_no")
		if batch:
			batch_qty_map[batch] = batch_qty_map.get(batch, 0.0) + flt(r.get("qty"))
	
	stock_chart_data = sorted(
		[{"name": k, "value": v} for k, v in batch_qty_map.items()],
		key=lambda x: x["value"],
		reverse=True
	)[:10]

	# Chart Data: Movement Trends (Last 30 Days)
	trend_chart_data = _get_movement_trends(customers)

	# Fetch settings
	announcement = frappe.db.get_single_value("Cold Storage Settings", "portal_announcement")
	company_name = frappe.db.get_single_value("Cold Storage Settings", "company") or ""
	

	return {
		"available_customers": available_customers,
		"selected_customer": selected_customer,
		"customers": customers,
		"stock": stock_rows,
		"movements": movement_rows,
		"invoices": invoice_rows,
		"reports": report_rows,
		"announcement": announcement,
		"company_name": company_name,
		"analytics": {
			"stock_composition": stock_chart_data,
			"movement_trends": trend_chart_data
		},
		"total_outstanding": total_outstanding
	}




@frappe.whitelist()
def create_service_request(request_type: str, customer: str, items: list[dict], required_date: str) -> dict:
	"""Create a Draft Inward or Outward document."""
	_ensure_client_portal_access()
	
	if request_type not in ("Inward", "Outward"):
		frappe.throw(_("Invalid request type"), frappe.ValidationError)

	if not items:
		frappe.throw(_("At least one item is required"), frappe.ValidationError)

	# Validate customer access
	_customers, _available_customers, _selected_customer = _resolve_customer_scope(customer)

	doctype = "Cold Storage Inward" if request_type == "Inward" else "Cold Storage Outward"
	
	doc = frappe.new_doc(doctype)
	doc.customer = customer
	doc.posting_date = getdate(required_date) if required_date else now_datetime().date()
	
	# Set Naming Series based on type
	if request_type == "Inward":
		doc.naming_series = "CS-IN-.YYYY.-"
	else:
		doc.naming_series = "CS-OUT-.YYYY.-"

	for item in items:
		row = doc.append("items", {})
		row.item_code = item.get("item_code")
		row.qty = flt(item.get("qty"))
		if item.get("batch_no"):
			row.batch_no = item.get("batch_no")

	doc.insert(ignore_permissions=True)
	
	return {
		"name": doc.name,
		"message": _("Request created successfully")
	}

@frappe.whitelist()
def get_document_details(doctype: str, docname: str) -> dict:
	"""Fetch details and child items for a specific document."""
	_ensure_client_portal_access()

	if doctype not in ["Cold Storage Inward", "Cold Storage Outward"]:
		frappe.throw(_("Invalid document type"))

	if not frappe.db.exists(doctype, docname):
		frappe.throw(_("Document not found"))

	doc = frappe.get_doc(doctype, docname)
	
	# Security check: Ensure user has access to this customer
	user_customers = get_customers_for_portal_user(frappe.session.user)
	if doc.customer not in user_customers:
		frappe.throw(_("You do not have permission to view this document"))

	return {
		"name": doc.name,
		"status": "Draft" if doc.docstatus == 0 else ("Submitted" if doc.docstatus == 1 else "Cancelled"),
		"posting_date": formatdate(doc.posting_date),
		"customer": doc.customer,
		"doctype": doctype, 
		"items": [
			{
				"item_code": item.item_code,
				"item_name": item.item_name,
				"qty": item.qty,
				"batch_no": item.batch_no,
				"uom": item.uom
			}
			for item in doc.items
		]
	}
@frappe.whitelist()
def get_available_items(customer: str | None = None, request_type: str = "Inward") -> list[str]:
	"""Fetch available item codes for the customer based on request type.
	
	Inward: Items the customer has batches for (their goods).
	Outward: Items the customer currently has in stock (qty > 0).
	"""
	_ensure_client_portal_access()
	
	if not customer:
		return []
	
	# Validate customer scope
	_customers, _available, _selected = _resolve_customer_scope(customer)
	if not _customers:
		return []

	if request_type == "Outward":
		# For Outward, only allow items currently in stock for this customer
		# Uses same UNION ALL pattern as _get_stock_rows to handle both
		# direct batch_no and Serial and Batch Bundle entries
		return frappe.db.sql(
			"""
			select distinct stock.item_code
			from `tabBatch` batch
			join (
				select item_code, batch_no, sum(qty) as qty
				from (
					select sle.item_code, sle.batch_no, sle.actual_qty as qty
					from `tabStock Ledger Entry` sle
					where sle.is_cancelled = 0
						and ifnull(sle.batch_no, '') != ''

					union all

					select sle.item_code, sbe.batch_no, sbe.qty as qty
					from `tabStock Ledger Entry` sle
					inner join `tabSerial and Batch Entry` sbe
						on sbe.parent = sle.serial_and_batch_bundle
					where sle.is_cancelled = 0
						and ifnull(sle.batch_no, '') = ''
						and ifnull(sle.serial_and_batch_bundle, '') != ''
						and ifnull(sbe.batch_no, '') != ''
						and ifnull(sbe.is_cancelled, 0) = 0
				) combined
				group by item_code, batch_no
			) stock on stock.batch_no = batch.name
			where batch.custom_customer = %(customer)s
				and stock.qty > 0
			order by stock.item_code
			""",
			{"customer": customer},
			pluck=True
		)

	# For Inward, return items the customer has batches for (their goods)
	customer_items = frappe.db.sql(
		"""
		select distinct batch.item
		from `tabBatch` batch
		inner join `tabItem` item on item.name = batch.item
		where batch.custom_customer = %(customer)s
			and item.disabled = 0
			and item.is_stock_item = 1
		order by batch.item
		""",
		{"customer": customer},
		pluck=True
	)

	# If customer has historical items, return those
	# Otherwise fallback to all enabled stock items so new customers can also create requests
	if customer_items:
		return customer_items

	return frappe.get_all(
		"Item",
		filters={"disabled": 0, "is_stock_item": 1, "has_batch_no": 1},
		pluck="name",
		order_by="name asc"
	)

@frappe.whitelist()
def get_available_batches(customer: str, item_code: str, request_type: str = "Inward") -> list[dict]:
	"""Fetch available batches for the customer and item combination.
	
	Inward: All batches the customer owns for the item.
	Outward: Only batches with positive stock (qty > 0).
	
	Returns list of dicts: [{batch_no, qty}]
	"""
	_ensure_client_portal_access()
	
	if not customer or not item_code:
		return []
	
	# Validate customer scope
	_customers, _available, _selected = _resolve_customer_scope(customer)
	if not _customers:
		return []

	if request_type == "Outward":
		# Only batches with positive stock
		return frappe.db.sql(
			"""
			select batch.name as batch_no, stock.qty
			from `tabBatch` batch
			join (
				select batch_no, sum(qty) as qty
				from (
					select sle.batch_no, sle.actual_qty as qty
					from `tabStock Ledger Entry` sle
					where sle.is_cancelled = 0
						and sle.item_code = %(item_code)s
						and ifnull(sle.batch_no, '') != ''

					union all

					select sbe.batch_no, sbe.qty as qty
					from `tabStock Ledger Entry` sle
					inner join `tabSerial and Batch Entry` sbe
						on sbe.parent = sle.serial_and_batch_bundle
					where sle.is_cancelled = 0
						and sle.item_code = %(item_code)s
						and ifnull(sle.batch_no, '') = ''
						and ifnull(sle.serial_and_batch_bundle, '') != ''
						and ifnull(sbe.batch_no, '') != ''
						and ifnull(sbe.is_cancelled, 0) = 0
				) combined
				group by batch_no
				having sum(qty) > 0
			) stock on stock.batch_no = batch.name
			where batch.custom_customer = %(customer)s
				and batch.item = %(item_code)s
			order by batch.name
			""",
			{"customer": customer, "item_code": item_code},
			as_dict=True
		)

	# For Inward, all batches the customer owns for this item
	return frappe.db.sql(
		"""
		select batch.name as batch_no, ifnull(stock.qty, 0) as qty
		from `tabBatch` batch
		left join (
			select batch_no, sum(qty) as qty
			from (
				select sle.batch_no, sle.actual_qty as qty
				from `tabStock Ledger Entry` sle
				where sle.is_cancelled = 0
					and sle.item_code = %(item_code)s
					and ifnull(sle.batch_no, '') != ''

				union all

				select sbe.batch_no, sbe.qty as qty
				from `tabStock Ledger Entry` sle
				inner join `tabSerial and Batch Entry` sbe
					on sbe.parent = sle.serial_and_batch_bundle
				where sle.is_cancelled = 0
					and sle.item_code = %(item_code)s
					and ifnull(sle.batch_no, '') = ''
					and ifnull(sle.serial_and_batch_bundle, '') != ''
					and ifnull(sbe.batch_no, '') != ''
					and ifnull(sbe.is_cancelled, 0) = 0
			) combined
			group by batch_no
		) stock on stock.batch_no = batch.name
		where batch.custom_customer = %(customer)s
			and batch.item = %(item_code)s
		order by batch.name
		""",
		{"customer": customer, "item_code": item_code},
		as_dict=True
	)

@frappe.whitelist()
def get_item_details(item_code: str) -> dict:
	"""Fetch item name and details."""
	_ensure_client_portal_access()
	return frappe.db.get_value("Item", item_code, ["item_name", "stock_uom", "description"], as_dict=True) or {}

@frappe.whitelist()
def download_stock_csv(customer: str | None = None) -> None:
	"""Download customer-filtered stock snapshot as CSV."""
	_ensure_client_portal_access()
	customers, _available_customers, _selected_customer = _resolve_customer_scope(customer)
	rows = _get_stock_rows(customers, MAX_LIMIT * 2) if customers else []
	_download_csv(
		filename="cold_storage_stock.csv",
		fieldnames=[
			"customer",
			"item_code",
			"item_name",
			"batch_no",
			"warehouse",
			"qty",
			"expiry_date",
		],
		rows=rows,
	)


@frappe.whitelist()
def download_movements_csv(customer: str | None = None) -> None:
	"""Download customer-filtered movement data as CSV."""
	_ensure_client_portal_access()
	customers, _available_customers, _selected_customer = _resolve_customer_scope(customer)
	rows = _get_movement_rows(customers, MAX_LIMIT * 2) if customers else []
	_download_csv(
		filename="cold_storage_movements.csv",
		fieldnames=[
			"movement_type",
			"document_name",
			"posting_date",
			"customer",
			"qty",
			"reference",
		],
		rows=rows,
	)


@frappe.whitelist()
def download_invoices_csv(customer: str | None = None) -> None:
	"""Download customer-filtered invoice data as CSV."""
	_ensure_client_portal_access()
	customers, _available_customers, _selected_customer = _resolve_customer_scope(customer)
	rows = _get_invoice_rows(customers, MAX_LIMIT * 2) if customers else []
	_download_csv(
		filename="cold_storage_invoices.csv",
		fieldnames=[
			"name",
			"posting_date",
			"due_date",
			"customer",
			"currency",
			"grand_total",
			"outstanding_amount",
			"status",
		],
		rows=rows,
	)


@frappe.whitelist()
def download_report_pdf(report_name: str, customer: str | None = None) -> None:
	"""Download a customer-scoped portal report as PDF."""
	_ensure_client_portal_access()
	report_name = cstr(report_name).strip()
	if not report_name:
		frappe.throw(_("Report is required"), frappe.ValidationError)

	if report_name not in _get_portal_report_names():
		frappe.throw(_("You are not allowed to export this report"), frappe.PermissionError)
	if not frappe.db.exists("Report", report_name):
		frappe.throw(_("Report is not available"), frappe.DoesNotExistError)

	roles = set(frappe.get_roles())
	if not _has_report_access(report_name, roles):
		frappe.throw(_("You are not allowed to export this report"), frappe.PermissionError)

	_customers, _available_customers, selected_customer = _resolve_customer_scope(customer)
	filters = _get_report_filters(report_name, selected_customer)
	report_data = run_query_report(report_name=report_name, filters=filters or None)
	html = _render_portal_report_pdf_html(
		report_name=report_name,
		selected_customer=selected_customer,
		report_data=report_data,
	)
	pdf_content = get_pdf(
		html,
		{
			"page-size": "A4",
			"encoding": "UTF-8",
			"print-media-type": "",
			"margin-top": "8mm",
			"margin-bottom": "10mm",
			"margin-left": "8mm",
			"margin-right": "8mm",
		},
	)
	frappe.response.filename = _get_report_pdf_filename(report_name, selected_customer)
	frappe.response.filecontent = pdf_content
	frappe.response.type = "pdf"


def _sanitize_limit(limit: int | str | None) -> int:
	row_limit = cint(limit or DEFAULT_LIMIT)
	if row_limit < 1:
		return DEFAULT_LIMIT
	return min(row_limit, MAX_LIMIT)


def _ensure_client_portal_access() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to access the client portal"), frappe.PermissionError)

	roles = set(frappe.get_roles())
	if SYSTEM_MANAGER_ROLE in roles:
		return
	if CLIENT_PORTAL_ROLE not in roles and ADMIN_ROLE not in roles:
		frappe.throw(_("You are not allowed to access the client portal"), frappe.PermissionError)


def _get_scoped_customers_for_session() -> list[str]:
	customers = get_customers_for_portal_user()
	if customers:
		return customers

	roles = set(frappe.get_roles())
	if _has_global_portal_scope(roles):
		return frappe.get_all("Customer", pluck="name")

	return []


def _get_movement_trends(customers: list[str], days: int = 30) -> dict:
	"""Fetch aggregated Inward/Outward quantities per day for the last N days."""
	if not customers:
		return {"labels": [], "datasets": []}

	start_date = add_days(nowdate(), -days)
	
	# Fetch aggregated data via SQL for performance and correctness
	data = frappe.db.sql(
		"""
		select posting_date, movement_type, sum(qty) as qty
		from (
			-- Inward
			select posting_date, 'Inward' as movement_type, sum(total_qty) as qty
			from `tabCold Storage Inward`
			where docstatus = 1 and customer in %(customers)s and posting_date >= %(start_date)s
			group by posting_date
			
			union all
			
			-- Outward
			select posting_date, 'Outward' as movement_type, sum(total_qty) as qty
			from `tabCold Storage Outward`
			where docstatus = 1 and customer in %(customers)s and posting_date >= %(start_date)s
			group by posting_date

			union all

			-- Transfer In (treated as Inward for this customer)
			select posting_date, 'Inward' as movement_type, sum(total_qty) as qty
			from `tabCold Storage Transfer`
			where docstatus = 1 and to_customer in %(customers)s and posting_date >= %(start_date)s
			group by posting_date

			union all

			-- Transfer Out (treated as Outward for this customer)
			select posting_date, 'Outward' as movement_type, sum(total_qty) as qty
			from `tabCold Storage Transfer`
			where docstatus = 1 and from_customer in %(customers)s and posting_date >= %(start_date)s
			group by posting_date
		) combined
		group by posting_date, movement_type
		order by posting_date asc
		""",
		{"customers": customers, "start_date": start_date},
		as_dict=True
	)

	# Initialize map for all dates in range to ensure continuity? 
	# Or just present dates with activity? 
	# Presenting dates with activity is usually consistent with previous logic.
	# But let's fill gaps if needed? The previous logic didn't fill gaps.
	# So we just process the results.

	stats = {}
	for row in data:
		d = getdate(row.posting_date)
		if d not in stats:
			stats[d] = {"Inward": 0.0, "Outward": 0.0}
		stats[d][row.movement_type] += flt(row.qty)

	sorted_dates = sorted(stats.keys())
	# Limit to last N days strictly in case of clock skew, though SQL filter handles it.
	# formatted dates
	labels = [d.strftime("%d %b") for d in sorted_dates]
	inward_vals = [stats[d]["Inward"] for d in sorted_dates]
	outward_vals = [stats[d]["Outward"] for d in sorted_dates]

	return {
		"labels": labels,
		"datasets": [
			{"name": "Inward", "values": inward_vals},
			{"name": "Outward", "values": outward_vals}
		]
	}


def _has_global_portal_scope(roles: set[str]) -> bool:
	return SYSTEM_MANAGER_ROLE in roles or ADMIN_ROLE in roles


def _resolve_customer_scope(customer: str | None = None) -> tuple[list[str], list[str], str]:
	available_customers = _get_scoped_customers_for_session()
	selected_customer = cstr(customer).strip()
	if not selected_customer:
		return available_customers, available_customers, ""

	if selected_customer not in set(available_customers):
		frappe.throw(_("You are not allowed to access this customer's data"), frappe.PermissionError)

	return [selected_customer], available_customers, selected_customer


def _get_stock_rows(customers: list[str], row_limit: int) -> list[dict]:
	if not customers:
		return []

	rows = frappe.db.sql(
		"""
		select
			batch.custom_customer as customer,
			stock.item_code,
			item.item_name,
			stock.batch_no,
			stock.warehouse,
			round(sum(stock.qty), 3) as qty,
			batch.expiry_date
		from (
			select
				sle.item_code,
				sle.batch_no,
				sle.warehouse,
				sle.actual_qty as qty
			from `tabStock Ledger Entry` sle
			where sle.is_cancelled = 0
				and ifnull(sle.batch_no, '') != ''

			union all

			select
				sle.item_code,
				sbe.batch_no,
				sle.warehouse,
				sbe.qty as qty
			from `tabStock Ledger Entry` sle
			inner join `tabSerial and Batch Entry` sbe
				on sbe.parent = sle.serial_and_batch_bundle
			where sle.is_cancelled = 0
				and ifnull(sle.batch_no, '') = ''
				and ifnull(sle.serial_and_batch_bundle, '') != ''
				and ifnull(sbe.batch_no, '') != ''
				and ifnull(sbe.is_cancelled, 0) = 0
		) stock
		inner join `tabBatch` batch on batch.name = stock.batch_no
		left join `tabItem` item on item.name = stock.item_code
		where 1=1
			and batch.custom_customer in %(customers)s
		group by
			batch.custom_customer,
			stock.item_code,
			item.item_name,
			stock.batch_no,
			stock.warehouse,
			batch.expiry_date
		having round(sum(stock.qty), 3) > 0
		order by qty desc, stock.item_code asc
		limit %(row_limit)s
		""",
		{
			"customers": tuple(customers),
			"row_limit": cint(row_limit),
		},
		as_dict=True,
	)

	for row in rows:
		row["qty"] = flt(row.get("qty"), 3)

	return rows


def _dedupe_strings(values: list[str]) -> list[str]:
	seen: set[str] = set()
	unique_values: list[str] = []
	for value in values:
		clean_value = cstr(value).strip()
		if not clean_value:
			continue
		if clean_value in seen:
			continue
		seen.add(clean_value)
		unique_values.append(clean_value)
	return unique_values


def _dedupe_stock_rows(rows: list[dict]) -> list[dict]:
	seen: set[tuple[str, str, str, str, str]] = set()
	unique_rows: list[dict] = []
	for row in rows:
		key = (
			cstr(row.get("customer")),
			cstr(row.get("item_code")),
			cstr(row.get("batch_no")),
			cstr(row.get("warehouse")),
			cstr(row.get("expiry_date")),
		)
		if key in seen:
			continue
		seen.add(key)
		unique_rows.append(row)
	return unique_rows


def _dedupe_movement_rows(rows: list[dict]) -> list[dict]:
	# Since SLE are unique per Voucher+Item+Batch+Creation, we just pass through
	# Or enforce uniqueness if needed. SLE IDs are unique.
	# But we are returning dicts.
	# Let's assume unique enough for now or dedupe by all fields?
    # Actually, for portal view duplication is unlikely unless join issues.
	return rows


def _dedupe_invoice_rows(rows: list[dict]) -> list[dict]:
	seen: set[str] = set()
	unique_rows: list[dict] = []
	for row in rows:
		key = cstr(row.get("name"))
		if not key:
			continue
		if key in seen:
			continue
		seen.add(key)
		unique_rows.append(row)
	return unique_rows


def _dedupe_report_rows(rows: list[dict]) -> list[dict]:
	seen: set[str] = set()
	unique_rows: list[dict] = []
	for row in rows:
		key = cstr(row.get("report_name")).strip()
		if not key:
			continue
		if key in seen:
			continue
		seen.add(key)
		unique_rows.append(row)
	return unique_rows


def _get_movement_rows(customers: list[str], row_limit: int) -> list[dict]:
	if not customers:
		return []

	# Query Cold Storage Inward/Outward/Transfer child tables directly
	# (Stock Ledger Entries use voucher_type='Stock Entry' and won't match)
	return frappe.db.sql(
		"""
		(
			select
				p.posting_date,
				p.name as document_name,
				p.customer,
				ci.item as item_code,
				ci.batch_no,
				ci.qty as qty,
				ci.uom as stock_uom,
				'Inward' as movement_type
			from `tabCold Storage Inward` p
			join `tabCold Storage Inward Item` ci on ci.parent = p.name
			where p.docstatus = 1 and p.customer in %(customers)s
		)
		union all
		(
			select
				p.posting_date,
				p.name as document_name,
				p.customer,
				ci.item as item_code,
				ci.batch_no,
				ci.qty as qty,
				ci.uom as stock_uom,
				'Outward' as movement_type
			from `tabCold Storage Outward` p
			join `tabCold Storage Outward Item` ci on ci.parent = p.name
			where p.docstatus = 1 and p.customer in %(customers)s
		)
		union all
		(
			select
				p.posting_date,
				p.name as document_name,
				ifnull(p.from_customer, p.customer) as customer,
				ci.item as item_code,
				ci.batch_no,
				ci.qty as qty,
				ci.uom as stock_uom,
				'Transfer' as movement_type
			from `tabCold Storage Transfer` p
			join `tabCold Storage Transfer Item` ci on ci.parent = p.name
			where p.docstatus = 1
				and (p.customer in %(customers)s
					or p.from_customer in %(customers)s
					or p.to_customer in %(customers)s)
		)
		order by posting_date desc
		limit %(row_limit)s
		""",
		{
			"customers": tuple(customers),
			"row_limit": cint(row_limit),
		},
		as_dict=True,
	)



def _resolve_transfer_customer(row: frappe._dict) -> str:
	if row.get("transfer_type") == "Ownership Transfer":
		return f"{row.get('from_customer') or ''} -> {row.get('to_customer') or ''}".strip(" ->")
	return cstr(row.get("customer") or "")


def _get_invoice_rows(customers: list[str], row_limit: int) -> list[dict]:
	if not customers:
		return []

	# Fetch all submitted Sales Invoices for these customers
	rows = frappe.db.sql(
		"""
		select
			name,
			posting_date,
			due_date,
			customer,
			currency,
			grand_total,
			outstanding_amount,
			status
		from `tabSales Invoice`
		where docstatus = 1
			and customer in %(customers)s
		order by posting_date desc, modified desc
		limit %(row_limit)s
		""",
		{
			"customers": tuple(customers),
			"row_limit": cint(row_limit),
		},
		as_dict=True,
	)
	
	for row in rows:
		row["route"] = _to_invoice_route(row.get("name"))
	return rows


def _get_total_outstanding(customers: list[str]) -> float:
	if not customers:
		return 0.0
	
	total = frappe.db.sql(
		"""
		select sum(outstanding_amount)
		from `tabSales Invoice`
		where docstatus = 1
			and customer in %(customers)s
		""",
		{"customers": tuple(customers)}
	)[0][0]
	
	return flt(total or 0.0)


def _get_report_links(selected_customer: str = "") -> list[dict]:
	roles = set(frappe.get_roles())
	links: list[dict] = []

	for report_definition in PORTAL_REPORT_DEFINITIONS:
		report_name = report_definition["report_name"]
		if not frappe.db.exists("Report", report_name):
			continue
		if not _has_report_access(report_name, roles):
			continue
		links.append(
			{
				"report_name": report_name,
				"label": report_definition["label"],
				"description": report_definition["description"],
				"route": _get_report_route(report_name, selected_customer),
				"pdf_route": _get_report_pdf_route(report_name, selected_customer),
			}
		)

	return links


def _get_portal_report_names() -> set[str]:
	return {report["report_name"] for report in PORTAL_REPORT_DEFINITIONS}


def _has_report_access(report_name: str, roles: set[str]) -> bool:
	if SYSTEM_MANAGER_ROLE in roles:
		return True

	report = frappe.get_cached_doc("Report", report_name)
	report_roles = {row.role for row in report.get("roles", []) if row.role}
	return bool(report_roles.intersection(roles))


def _get_report_route(report_name: str, selected_customer: str = "") -> str:
	base_route = f"/app/query-report/{quote(report_name, safe='')}"
	if not selected_customer or report_name not in REPORTS_WITH_CUSTOMER_FILTER:
		return base_route

	filters = {"customer": selected_customer}
	query = urlencode(
		{
			"customer": selected_customer,
			"filters": json.dumps(filters, separators=(",", ":")),
		}
	)
	return f"{base_route}?{query}"


def _get_report_pdf_route(report_name: str, selected_customer: str = "") -> str:
	base_route = "/api/method/cold_storage.api.client_portal.download_report_pdf"
	query_args = {"report_name": report_name}
	if selected_customer:
		query_args["customer"] = selected_customer
	return f"{base_route}?{urlencode(query_args)}"


def _get_report_filters(report_name: str, selected_customer: str = "") -> dict:
	filters: dict[str, str] = {}
	if selected_customer and report_name in REPORTS_WITH_CUSTOMER_FILTER:
		filters["customer"] = selected_customer
	return filters


def _render_portal_report_pdf_html(
	*,
	report_name: str,
	selected_customer: str,
	report_data: dict,
) -> str:
	columns = _normalize_report_columns(report_data.get("columns") or [])
	rows = report_data.get("result") or []
	report_summary = report_data.get("report_summary") or []
	scope_label = selected_customer or _("All Customers in Scope")

	summary_html = "".join(
		(
			"<div class='summary-card'>"
			f"<div class='summary-label'>{escape_html(cstr(item.get('label') or 'Metric'))}</div>"
			f"<div class='summary-value'>{escape_html(_format_report_cell(item.get('value'), cstr(item.get('datatype') or 'Data')))}</div>"
			"</div>"
		)
		for item in report_summary
	)

	header_cells = "".join(f"<th>{escape_html(cstr(column['label']))}</th>" for column in columns)

	body_rows = []
	for row in rows:
		row_cells = "".join(
			f"<td>{escape_html(_get_report_cell_value(row, column))}</td>" for column in columns
		)
		body_rows.append(f"<tr>{row_cells}</tr>")

	if not body_rows:
		empty_colspan = max(len(columns), 1)
		body_rows.append(
			f"<tr><td colspan='{empty_colspan}' class='empty'>{escape_html(_('No records found'))}</td></tr>"
		)

	table_html = (
		"<table>"
		f"<thead><tr>{header_cells or '<th>Data</th>'}</tr></thead>"
		f"<tbody>{''.join(body_rows)}</tbody>"
		"</table>"
	)

	return f"""
	<!doctype html>
	<html>
	<head>
		<meta charset="utf-8">
		<style>
			* {{ box-sizing: border-box; }}
			body {{
				font-family: "Segoe UI", "Inter", Arial, sans-serif;
				color: #163830;
				margin: 0;
				padding: 0;
				font-size: 11px;
				background: #f5faf8;
			}}
			.wrap {{ padding: 14px; }}
			.hero {{
				background: linear-gradient(130deg, #1f8a70, #166b58);
				color: #fff;
				border-radius: 12px;
				padding: 14px 16px;
				margin-bottom: 10px;
			}}
			.title {{
				font-size: 18px;
				font-weight: 700;
				margin: 0;
			}}
			.subtitle {{
				font-size: 12px;
				margin-top: 4px;
				opacity: 0.95;
			}}
			.meta {{
				display: grid;
				grid-template-columns: repeat(3, minmax(0, 1fr));
				gap: 8px;
				margin: 10px 0;
			}}
			.meta-card {{
				background: #ffffff;
				border: 1px solid #d5e8e2;
				border-radius: 10px;
				padding: 8px 10px;
			}}
			.meta-label {{
				font-size: 9px;
				text-transform: uppercase;
				letter-spacing: 0.08em;
				color: #5d7e75;
				margin-bottom: 3px;
			}}
			.meta-value {{
				font-size: 12px;
				font-weight: 600;
				color: #1d463d;
			}}
			.summary {{
				display: grid;
				grid-template-columns: repeat(4, minmax(0, 1fr));
				gap: 8px;
				margin-bottom: 10px;
			}}
			.summary-card {{
				background: #ffffff;
				border: 1px solid #d8ebe5;
				border-radius: 10px;
				padding: 8px 10px;
			}}
			.summary-label {{
				font-size: 9px;
				text-transform: uppercase;
				letter-spacing: 0.08em;
				color: #5f8177;
			}}
			.summary-value {{
				margin-top: 4px;
				font-size: 13px;
				font-weight: 700;
				color: #1b463c;
			}}
			table {{
				width: 100%;
				border-collapse: collapse;
				background: #ffffff;
				border-radius: 10px;
				overflow: hidden;
				border: 1px solid #d5e8e2;
			}}
			thead th {{
				background: #ebf5f2;
				color: #476d63;
				text-transform: uppercase;
				letter-spacing: 0.05em;
				font-size: 9px;
				font-weight: 700;
				padding: 8px 7px;
				text-align: left;
				border-bottom: 1px solid #d5e8e2;
			}}
			tbody td {{
				padding: 7px;
				border-top: 1px solid #e6f1ed;
				vertical-align: top;
				color: #1f4b41;
				font-size: 10px;
			}}
			tbody tr:nth-child(even) td {{
				background: #fbfdfc;
			}}
			td.empty {{
				text-align: center;
				color: #6d8d84;
				padding: 14px 8px;
			}}
		</style>
	</head>
	<body>
		<div class="wrap">
			<div class="hero">
				<div class="title">{escape_html(report_name)}</div>
				<div class="subtitle">Cold Storage Client Portal Report Export</div>
			</div>
			<div class="meta">
				<div class="meta-card">
					<div class="meta-label">Customer Scope</div>
					<div class="meta-value">{escape_html(scope_label)}</div>
				</div>
				<div class="meta-card">
					<div class="meta-label">Rows</div>
					<div class="meta-value">{len(rows)}</div>
				</div>
					<div class="meta-card">
						<div class="meta-label">Generated At</div>
						<div class="meta-value">{escape_html(format_datetime(now_datetime()))}</div>
					</div>
				</div>
			{f"<div class='summary'>{summary_html}</div>" if summary_html else ""}
			{table_html}
		</div>
	</body>
	</html>
	"""


def _normalize_report_columns(columns: list) -> list[dict]:
	normalized: list[dict] = []
	for index, column in enumerate(columns):
		if isinstance(column, dict):
			normalized.append(
				{
					"index": index,
					"fieldname": cstr(column.get("fieldname") or f"column_{index}"),
					"label": cstr(column.get("label") or column.get("fieldname") or f"Column {index + 1}"),
					"fieldtype": cstr(column.get("fieldtype") or "Data"),
				}
			)
			continue

		column_text = cstr(column)
		label = column_text.split(":")[0] if column_text else f"Column {index + 1}"
		normalized.append(
			{
				"index": index,
				"fieldname": f"column_{index}",
				"label": label,
				"fieldtype": "Data",
			}
		)
	return normalized


def _get_report_cell_value(row: dict | list | tuple, column: dict) -> str:
	value = None
	if isinstance(row, dict):
		value = row.get(column["fieldname"])
	elif isinstance(row, (list, tuple)):
		index = cint(column.get("index"))
		value = row[index] if 0 <= index < len(row) else None
	return _format_report_cell(value, cstr(column.get("fieldtype") or "Data"))


def _format_report_cell(value, fieldtype: str) -> str:
	if value is None or value == "":
		return ""

	if fieldtype in {"Float"}:
		return f"{flt(value):,.3f}"
	if fieldtype in {"Currency"}:
		return f"{flt(value):,.2f}"
	if fieldtype in {"Percent"}:
		return f"{flt(value):,.2f}%"
	if fieldtype in {"Int", "Check"}:
		return cstr(value)
	if fieldtype in {"Date"}:
		return cstr(formatdate(value))
	if fieldtype in {"Datetime"}:
		return cstr(format_datetime(value))
	return cstr(value)


def _get_report_pdf_filename(report_name: str, selected_customer: str = "") -> str:
	base = frappe.scrub(report_name).replace("_", "-")
	if selected_customer:
		customer_part = frappe.scrub(selected_customer).replace("_", "-")
		return f"{base}-{customer_part}.pdf"
	return f"{base}.pdf"


def _to_invoice_route(docname: str | None) -> str:
	if not docname:
		return ""
	return f"/invoices/{docname}"


def _download_csv(filename: str, fieldnames: list[str], rows: list[dict]) -> None:
	output = StringIO()
	writer = csv.DictWriter(output, fieldnames=fieldnames)
	writer.writeheader()
	for row in rows:
		writer.writerow({field: row.get(field, "") for field in fieldnames})

	frappe.response["type"] = "download"
	frappe.response["filename"] = filename
	frappe.response["filecontent"] = output.getvalue()


@frappe.whitelist()
def download_dashboard_report(customer: str | None = None) -> None:
	"""Generate and download a comprehensive dashboard PDF report."""
	_ensure_client_portal_access()
	
	# Reuse existing snapshot logic to fetch all data
	# Fetch basic snapshot first
	data = get_snapshot(limit=100, customer=customer)
	
	# Override movements with a larger limit for the report to ensure completeness
	data["movements"] = _get_movement_rows(data["customers"], row_limit=5000)

	
	# Add derived metrics for the report
	data["total_stock_value"] = sum(flt(row.get("qty")) * flt(row.get("valuation_rate", 0)) for row in data["stock"])
	data["max_stock_value"] = max([d["value"] for d in data["analytics"]["stock_composition"]] or [1])
	
	# Calculate 30-day inward volume from analytics data
	total_inward = 0.0
	trend_data = data["analytics"]["movement_trends"]
	if trend_data and "datasets" in trend_data and len(trend_data["datasets"]) > 0:
		# dataset 0 is Inward based on _get_movement_trends implementation
		inward_ds = next((ds for ds in trend_data["datasets"] if ds["name"] == "Inward"), None)
		if inward_ds:
			total_inward = sum(flt(v) for v in inward_ds["values"])
			
	data["total_inward_30_days"] = total_inward

	# Render Template
	html = frappe.render_template("cold_storage/templates/pages/dashboard_report.html", data)

	# Generate PDF
	pdf_content = get_pdf(
		html,
		{
			"page-size": "A4",
			"margin-top": "0mm",
			"margin-right": "0mm",
			"margin-bottom": "0mm",
			"margin-left": "0mm",
			"encoding": "UTF-8",
			"no-outline": None,
			"disable-smart-shrinking": "true"
		}
	)

	frappe.response.filename = f"Executive_Report_{data.get('selected_customer') or 'All'}_{nowdate()}.pdf"
	frappe.response.filecontent = pdf_content
	frappe.response.type = "pdf"
