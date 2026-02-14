# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from base64 import b64encode
from io import BytesIO

import frappe
from erpnext.stock.doctype.batch.batch import get_batch_qty
from frappe import _
from frappe.utils import flt, nowdate


@frappe.whitelist()
def get_batch_balance(
	batch_no: str,
	warehouse: str | None = None,
	item_code: str | None = None,
) -> float:
	"""Return available quantity for a batch from ERPNext stock logic."""
	if not batch_no or not warehouse:
		return 0.0

	# Use ERPNext stock API so v17 serial/batch bundle paths are respected.
	qty = get_batch_qty(batch_no=batch_no, warehouse=warehouse)
	return flt(qty)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def search_batches_for_customer_warehouse(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict | None = None,
) -> list[tuple]:
	"""Search batches filtered by customer + warehouse (+ optional item) with positive balance."""
	del doctype, searchfield

	filters = filters or {}
	customer = filters.get("customer")
	warehouse = filters.get("warehouse")
	item = filters.get("item")

	if not customer or not warehouse:
		return []

	params = {
		"customer": customer,
		"warehouse": warehouse,
		"txt": f"%{txt or ''}%",
		"start": int(start or 0),
		"page_len": int(page_len or 20),
	}

	item_condition = ""
	if item:
		item_condition = " and b.item = %(item)s"
		params["item"] = item

	return frappe.db.sql(
		f"""
		select b.name
		from `tabBatch` b
		inner join `tabStock Ledger Entry` sle on sle.batch_no = b.name
		where b.custom_customer = %(customer)s
			and sle.warehouse = %(warehouse)s
			and ifnull(sle.is_cancelled, 0) = 0
			and (
				b.name like %(txt)s
				or ifnull(b.batch_id, '') like %(txt)s
			)
			{item_condition}
		group by b.name
		having sum(sle.actual_qty) > 0
		order by b.name
		limit %(start)s, %(page_len)s
		""",
		params,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def search_warehouses_for_customer(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict | None = None,
) -> list[tuple]:
	"""Search warehouses where customer has positive batch stock."""
	del doctype, searchfield

	filters = filters or {}
	customer = filters.get("customer")
	company = filters.get("company")
	item = filters.get("item")

	if not customer:
		return []

	params = {
		"customer": customer,
		"company": company or "",
		"txt": f"%{txt or ''}%",
		"start": int(start or 0),
		"page_len": int(page_len or 20),
	}

	item_condition = ""
	if item:
		item_condition = " and sle.item_code = %(item)s"
		params["item"] = item

	return frappe.db.sql(
		f"""
		select sle.warehouse
		from `tabStock Ledger Entry` sle
		inner join `tabBatch` b on b.name = sle.batch_no
		inner join `tabWarehouse` w on w.name = sle.warehouse
		where b.custom_customer = %(customer)s
			and ifnull(sle.is_cancelled, 0) = 0
			and sle.warehouse like %(txt)s
			and (%(company)s = '' or w.company = %(company)s)
			{item_condition}
		group by sle.warehouse
		having sum(sle.actual_qty) > 0
		order by sle.warehouse
		limit %(start)s, %(page_len)s
		""",
		params,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def search_items_for_customer_stock(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict | None = None,
) -> list[tuple]:
	"""Search items that have positive stock for the selected customer."""
	del doctype, searchfield

	filters = filters or {}
	customer = filters.get("customer")
	company = filters.get("company")
	warehouse = filters.get("warehouse")

	if not customer:
		return []

	params = {
		"customer": customer,
		"company": company or "",
		"warehouse": warehouse or "",
		"txt": f"%{txt or ''}%",
		"start": int(start or 0),
		"page_len": int(page_len or 20),
	}

	return frappe.db.sql(
		"""
		select sle.item_code, i.item_name
		from `tabStock Ledger Entry` sle
		inner join `tabBatch` b on b.name = sle.batch_no
		inner join `tabWarehouse` w on w.name = sle.warehouse
		inner join `tabItem` i on i.name = sle.item_code
		where b.custom_customer = %(customer)s
			and ifnull(sle.is_cancelled, 0) = 0
			and (%(company)s = '' or w.company = %(company)s)
			and (%(warehouse)s = '' or sle.warehouse = %(warehouse)s)
			and (
				sle.item_code like %(txt)s
				or ifnull(i.item_name, '') like %(txt)s
			)
		group by sle.item_code, i.item_name
		having sum(sle.actual_qty) > 0
		order by sle.item_code
		limit %(start)s, %(page_len)s
		""",
		params,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def search_warehouses_for_batch(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict | None = None,
) -> list[tuple]:
	"""Search warehouses where a selected batch has positive stock."""
	del doctype, searchfield

	filters = filters or {}
	batch_no = filters.get("batch_no")
	company = filters.get("company")
	customer = filters.get("customer")
	item = filters.get("item")

	if not batch_no:
		return []

	batch_details = frappe.db.get_value(
		"Batch",
		batch_no,
		["custom_customer", "item"],
		as_dict=True,
	)
	if not batch_details:
		return []

	if customer and batch_details.get("custom_customer") != customer:
		return []

	if item and batch_details.get("item") != item:
		return []

	start = int(start or 0)
	page_len = int(page_len or 20)
	scan_limit = max((start + page_len) * 5, 100)

	params = {
		"company": company or "",
		"txt": f"%{txt or ''}%",
		"scan_limit": scan_limit,
	}

	candidate_warehouses = frappe.db.sql(
		"""
		select w.name
		from `tabWarehouse` w
		where w.name like %(txt)s
			and (%(company)s = '' or w.company = %(company)s)
		order by w.name
		limit %(scan_limit)s
		""",
		params,
	)

	matching_warehouses = []
	for warehouse, in candidate_warehouses:
		qty = flt(get_batch_qty(batch_no=batch_no, warehouse=warehouse))
		if qty > 0:
			matching_warehouses.append((warehouse,))

	return matching_warehouses[start : start + page_len]


def create_stock_entry_for_cold_storage(
	*,
	company: str,
	posting_date: str | None,
	purpose: str,
	items: list[dict],
	reference_doctype: str,
	reference_name: str,
) -> str:
	"""Create and submit Stock Entry for a Cold Storage transaction."""
	from cold_storage.cold_storage.naming import get_series_for_company

	cost_center = frappe.get_cached_value("Company", company, "cost_center")
	expense_account = frappe.get_cached_value("Company", company, "stock_adjustment_account")

	se = frappe.new_doc("Stock Entry")
	se.naming_series = get_series_for_company("stock_entry", company)
	se.company = company
	se.purpose = purpose
	se.posting_date = posting_date or nowdate()
	se.set_posting_time = 1
	se.remarks = _("Auto-created from {0} {1}").format(reference_doctype, reference_name)

	for row in items:
		se_item = {
			"item_code": row.get("item_code"),
			"qty": flt(row.get("qty")),
			"uom": row.get("uom"),
			"conversion_factor": 1,
			"transfer_qty": flt(row.get("qty")),
			"batch_no": row.get("batch_no"),
			"use_serial_batch_fields": 1,
			"allow_zero_valuation_rate": 1,
			"cost_center": cost_center,
			"expense_account": expense_account,
		}
		if row.get("s_warehouse"):
			se_item["s_warehouse"] = row.get("s_warehouse")
		if row.get("t_warehouse"):
			se_item["t_warehouse"] = row.get("t_warehouse")
		se.append("items", se_item)

	se.set_stock_entry_type()
	se.flags.ignore_permissions = True
	se.insert()
	se.submit()
	return se.name


def cancel_stock_entry_if_submitted(stock_entry_name: str | None) -> bool:
	"""Cancel submitted Stock Entry by name."""
	if not stock_entry_name:
		return False

	se = frappe.get_doc("Stock Entry", stock_entry_name)
	if se.docstatus == 1:
		se.flags.ignore_permissions = True
		se.cancel()
		return True
	return False


def get_document_qr_code_payload(doctype: str, docname: str) -> str:
	"""Return the URL payload encoded inside document QR codes."""
	if not doctype or not docname:
		return ""
	return frappe.utils.get_url_to_form(doctype, docname)


def get_document_qr_code_data_uri(doctype: str, docname: str, scale: int = 4) -> str:
	"""Return an SVG data URI for a document QR code, suitable for print formats."""
	payload = get_document_qr_code_payload(doctype, docname)
	if not payload:
		return ""

	try:
		from pyqrcode import create as qr_create
	except Exception:
		return ""

	stream = BytesIO()
	try:
		qr_create(payload).svg(
			stream,
			scale=max(int(scale or 1), 1),
			background="#ffffff",
			module_color="#111827",
		)
		encoded_svg = b64encode(stream.getvalue()).decode()
	finally:
		stream.close()

	return f"data:image/svg+xml;base64,{encoded_svg}"
