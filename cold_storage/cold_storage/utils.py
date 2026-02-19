# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from base64 import b64encode
from io import BytesIO

import frappe
from erpnext.stock.doctype.batch.batch import get_batch_qty
from frappe import _
from frappe.utils import cint, flt, nowdate


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
	for (warehouse,) in candidate_warehouses:
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


def _get_qr_code_data_uri(payload: str, scale: int = 4) -> str:
	"""Return an SVG data URI for a QR payload."""
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


def _unique_compact(values: list[str], limit: int = 10) -> str:
	"""Return unique non-empty values as a compact string."""
	seen = set()
	clean = []
	for value in values or []:
		text = (value or "").strip()
		if not text or text in seen:
			continue
		seen.add(text)
		clean.append(text)

	if not clean:
		return "-"

	if len(clean) <= limit:
		return ", ".join(clean)

	return f"{', '.join(clean[:limit])} (+{len(clean) - limit} more)"


def _get_posted_by_label(doc) -> str:
	user = (doc.get("owner") or doc.get("modified_by") or "").strip()
	if not user:
		return "-"
	return frappe.db.get_value("User", user, "full_name") or user


def _get_customer_label(doc, doctype: str) -> str:
	if doctype == "Cold Storage Transfer":
		if doc.get("transfer_type") == "Ownership Transfer":
			from_customer = (doc.get("from_customer") or "-").strip() or "-"
			to_customer = (doc.get("to_customer") or "-").strip() or "-"
			return f"{from_customer} -> {to_customer}"
		return (doc.get("customer") or "").strip() or "-"

	return (doc.get("customer") or "").strip() or "-"


def _get_warehouse_label(items: list, doctype: str) -> str:
	if doctype == "Cold Storage Transfer":
		return _unique_compact(
			[
				f"{(row.get('source_warehouse') or '-').strip() or '-'} -> {(row.get('target_warehouse') or '-').strip() or '-'}"
				for row in items
			]
		)

	return _unique_compact([(row.get("warehouse") or "").strip() for row in items])


def get_document_sidebar_qr_code_payload(doctype: str, docname: str) -> str:
	"""Return a detailed QR payload for Cold Storage document sidebars."""
	if not doctype or not docname:
		return ""

	if not frappe.db.exists(doctype, docname):
		return ""

	doc = frappe.get_doc(doctype, docname)
	items = list(doc.get("items") or [])

	item_label = _unique_compact([(row.get("item") or row.get("item_name") or "").strip() for row in items])
	batch_label = _unique_compact([(row.get("batch_no") or "").strip() for row in items])
	warehouse_label = _get_warehouse_label(items, doctype)
	customer_label = _get_customer_label(doc, doctype)
	posted_by = _get_posted_by_label(doc)
	remarks = " ".join((doc.get("remarks") or "").split()) or "-"

	lines = [
		f"Document: {doctype}",
		f"ID: {docname}",
		f"Receipt #: {(doc.get('receipt_no') or '-').strip() or '-'}"
		if doctype == "Cold Storage Inward"
		else None,
		f"Date: {doc.get('posting_date') or '-'}",
		f"Customer: {customer_label}",
		f"Item: {item_label}",
		f"Batch No: {batch_label}",
		f"Warehouse: {warehouse_label}",
		f"Quantity: {flt(doc.get('total_qty'))}",
		f"Remarks: {remarks}",
		f"Posted By: {posted_by}",
	]
	lines = [line for line in lines if line]

	return "\n".join(lines)


@frappe.whitelist()
def get_document_sidebar_qr_code_data_uri(doctype: str, docname: str, scale: int = 3) -> str:
	"""Return QR data URI for sidebar view with key movement details."""
	if not doctype or not docname:
		return ""

	if not frappe.has_permission(doctype=doctype, ptype="read", doc=docname):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	payload = get_document_sidebar_qr_code_payload(doctype, docname)
	return _get_qr_code_data_uri(payload, scale=scale)


def get_document_qr_code_data_uri(
	doctype: str,
	docname: str,
	scale: int = 4,
	prefer_submitted_payload: int = 0,
) -> str:
	"""Return an SVG data URI for a document QR code, suitable for print formats.

	If ``prefer_submitted_payload`` is enabled and the document is submitted, use the
	detailed submitted-document QR payload.
	"""
	payload = ""
	if prefer_submitted_payload and doctype and docname and frappe.db.exists(doctype, docname):
		if cint(frappe.db.get_value(doctype, docname, "docstatus")) == 1:
			payload = get_document_sidebar_qr_code_payload(doctype, docname)

	if not payload:
		payload = get_document_qr_code_payload(doctype, docname)

	return _get_qr_code_data_uri(payload, scale=scale)
