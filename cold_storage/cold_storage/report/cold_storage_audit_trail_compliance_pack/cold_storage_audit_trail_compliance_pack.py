from __future__ import annotations

import json

import frappe
from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
	get_default_company,
)
from frappe import _
from frappe.utils import cint, flt, nowdate

DOCSTATUS_LABELS = {0: "Draft", 1: "Submitted", 2: "Cancelled"}
SYSTEM_VERSION_FIELDS = {"_assign", "_comments", "_liked_by", "_seen", "idx", "modified", "modified_by"}
MOVEMENT_DOCTYPES = ("Cold Storage Inward", "Cold Storage Outward", "Cold Storage Transfer")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	set_default_filters(filters)
	ensure_mandatory_filters(filters)
	filters.company = get_report_company(filters)

	movement_rows, document_meta = get_movement_rows(filters)
	action_rows = (
		get_user_action_rows(filters, document_meta) if cint(filters.get("include_user_actions")) else []
	)
	data = sorted(
		movement_rows + action_rows,
		key=lambda row: (
			row.get("event_timestamp") or "",
			0 if row.get("record_type") == "Movement" else 1,
			row.get("reference_doctype") or "",
			row.get("reference_name") or "",
		),
	)

	return get_columns(), data, None, get_chart_data(movement_rows), get_report_summary(movement_rows, action_rows)


def set_default_filters(filters) -> None:
	if not filters.get("to_date"):
		filters.to_date = nowdate()
	if not filters.get("from_date"):
		filters.from_date = filters.to_date
	if filters.get("include_user_actions") is None:
		filters.include_user_actions = 1


def ensure_mandatory_filters(filters) -> None:
	if not filters.get("batch_no"):
		frappe.throw(_("Batch is required to generate this compliance pack"))


def get_report_company(filters) -> str | None:
	try:
		return get_default_company() or filters.get("company")
	except Exception:
		return filters.get("company")


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_items_for_customer(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict | None = None,
):
	"""Return item options constrained to the selected customer (and company, if provided)."""
	del doctype, searchfield

	filters = frappe._dict(filters or {})
	customer = filters.get("customer")
	company = filters.get("company") or get_report_company(filters) or ""

	params = {
		"txt": f"%{(txt or '').strip()}%",
		"start": max(cint(start or 0), 0),
		"page_len": max(cint(page_len or 20), 1),
		"company": company,
	}

	if not customer:
		return frappe.db.sql(
			"""
			select i.name, i.item_name
			from `tabItem` i
			where ifnull(i.disabled, 0) = 0
				and (
					i.name like %(txt)s
					or ifnull(i.item_name, '') like %(txt)s
				)
			order by i.name
			limit %(start)s, %(page_len)s
			""",
			params,
		)

	params["customer"] = customer
	return frappe.db.sql(
		"""
		select distinct i.name, i.item_name
		from (
			select child.item as item
			from `tabCold Storage Inward Item` child
			inner join `tabCold Storage Inward` parent
				on parent.name = child.parent
				and child.parenttype = 'Cold Storage Inward'
			where parent.customer = %(customer)s
				and (%(company)s = '' or parent.company = %(company)s)

			union

			select child.item as item
			from `tabCold Storage Outward Item` child
			inner join `tabCold Storage Outward` parent
				on parent.name = child.parent
				and child.parenttype = 'Cold Storage Outward'
			where parent.customer = %(customer)s
				and (%(company)s = '' or parent.company = %(company)s)

			union

			select child.item as item
			from `tabCold Storage Transfer Item` child
			inner join `tabCold Storage Transfer` parent
				on parent.name = child.parent
				and child.parenttype = 'Cold Storage Transfer'
			where (
					ifnull(parent.customer, '') = %(customer)s
					or ifnull(parent.from_customer, '') = %(customer)s
					or ifnull(parent.to_customer, '') = %(customer)s
				)
				and (%(company)s = '' or parent.company = %(company)s)
		) movement_items
		inner join `tabItem` i
			on i.name = movement_items.item
		where ifnull(i.disabled, 0) = 0
			and (
				i.name like %(txt)s
				or ifnull(i.item_name, '') like %(txt)s
			)
		order by i.name
		limit %(start)s, %(page_len)s
		""",
		params,
	)


def get_columns():
	return [
		{
			"label": _("Event Timestamp"),
			"fieldname": "event_timestamp",
			"fieldtype": "Datetime",
			"width": 170,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": _("Record Type"), "fieldname": "record_type", "fieldtype": "Data", "width": 105},
		{"label": _("Event"), "fieldname": "event_type", "fieldtype": "Data", "width": 190},
		{
			"label": _("Reference Doctype"),
			"fieldname": "reference_doctype",
			"fieldtype": "Data",
			"width": 170,
		},
		{
			"label": _("Reference Document"),
			"fieldname": "reference_name",
			"fieldtype": "Dynamic Link",
			"options": "reference_doctype",
			"width": 190,
		},
		{"label": _("Batch"), "fieldname": "batch_no", "fieldtype": "Data", "width": 180},
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 160},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 185,
		},
		{
			"label": _("From Warehouse"),
			"fieldname": "from_warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 170,
		},
		{
			"label": _("To Warehouse"),
			"fieldname": "to_warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 170,
		},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 90},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 95},
		{"label": _("Action By"), "fieldname": "user", "fieldtype": "Link", "options": "User", "width": 170},
		{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 320},
	]


def get_movement_rows(filters):
	rows = []
	document_meta = {}

	for movement_row in get_inward_rows(filters):
		append_movement_row(rows, document_meta, movement_row)

	for movement_row in get_outward_rows(filters):
		append_movement_row(rows, document_meta, movement_row)

	for movement_row in get_transfer_rows(filters):
		append_movement_row(rows, document_meta, movement_row)

	return rows, document_meta


def append_movement_row(rows: list[dict], document_meta: dict, movement_row: dict) -> None:
	reference_doctype = movement_row.get("reference_doctype")
	reference_name = movement_row.get("reference_name")
	document_key = (reference_doctype, reference_name)
	status_label = DOCSTATUS_LABELS.get(cint(movement_row.get("docstatus")), "")

	meta = document_meta.setdefault(
		document_key,
		{
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"status": status_label,
			"customer": movement_row.get("customer"),
			"owner": movement_row.get("user"),
			"creation": movement_row.get("event_timestamp"),
			"batches": set(),
		},
	)
	if movement_row.get("batch_no"):
		meta["batches"].add(movement_row.get("batch_no"))

	row = {
		"event_timestamp": movement_row.get("event_timestamp"),
		"posting_date": movement_row.get("posting_date"),
		"record_type": "Movement",
		"event_type": movement_row.get("event_type"),
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
		"batch_no": movement_row.get("batch_no"),
		"item": movement_row.get("item"),
		"customer": movement_row.get("customer"),
		"from_warehouse": movement_row.get("from_warehouse"),
		"to_warehouse": movement_row.get("to_warehouse"),
		"qty": flt(movement_row.get("qty")),
		"status": status_label,
		"user": movement_row.get("user"),
		"remarks": movement_row.get("remarks"),
	}
	rows.append(row)


def get_inward_rows(filters):
	params = get_common_query_params(filters)
	conditions = get_common_parent_conditions(filters, "inward")
	if filters.get("warehouse"):
		conditions.append("child.warehouse = %(warehouse)s")

	return frappe.db.sql(
		f"""
		select
			parent.creation as event_timestamp,
			parent.posting_date as posting_date,
			'Inward' as event_type,
			'Cold Storage Inward' as reference_doctype,
			parent.name as reference_name,
			child.batch_no as batch_no,
			child.item as item,
			parent.customer as customer,
			'' as from_warehouse,
			child.warehouse as to_warehouse,
			child.qty as qty,
			parent.docstatus as docstatus,
			parent.owner as user,
			parent.remarks as remarks
		from `tabCold Storage Inward Item` child
		inner join `tabCold Storage Inward` parent
			on parent.name = child.parent
			and child.parenttype = 'Cold Storage Inward'
		where {" and ".join(conditions)}
		order by parent.posting_date asc, parent.creation asc, child.idx asc
		""",
		params,
		as_dict=True,
	)


def get_outward_rows(filters):
	params = get_common_query_params(filters)
	conditions = get_common_parent_conditions(filters, "outward")
	if filters.get("warehouse"):
		conditions.append("child.warehouse = %(warehouse)s")

	return frappe.db.sql(
		f"""
		select
			parent.creation as event_timestamp,
			parent.posting_date as posting_date,
			'Outward' as event_type,
			'Cold Storage Outward' as reference_doctype,
			parent.name as reference_name,
			child.batch_no as batch_no,
			child.item as item,
			parent.customer as customer,
			child.warehouse as from_warehouse,
			'' as to_warehouse,
			child.qty as qty,
			parent.docstatus as docstatus,
			parent.owner as user,
			parent.remarks as remarks
		from `tabCold Storage Outward Item` child
		inner join `tabCold Storage Outward` parent
			on parent.name = child.parent
			and child.parenttype = 'Cold Storage Outward'
		where {" and ".join(conditions)}
		order by parent.posting_date asc, parent.creation asc, child.idx asc
		""",
		params,
		as_dict=True,
	)


def get_transfer_rows(filters):
	params = get_common_query_params(filters)
	conditions = get_common_parent_conditions(filters, "transfer")
	if filters.get("warehouse"):
		conditions.append(
			"(ifnull(child.source_warehouse, '') = %(warehouse)s or ifnull(child.target_warehouse, '') = %(warehouse)s)"
		)

	return frappe.db.sql(
		f"""
		select
			parent.creation as event_timestamp,
			parent.posting_date as posting_date,
			concat('Transfer (', parent.transfer_type, ')') as event_type,
			'Cold Storage Transfer' as reference_doctype,
			parent.name as reference_name,
			child.batch_no as batch_no,
			child.item as item,
			coalesce(parent.customer, parent.to_customer, parent.from_customer) as customer,
			child.source_warehouse as from_warehouse,
			child.target_warehouse as to_warehouse,
			child.qty as qty,
			parent.docstatus as docstatus,
			parent.owner as user,
			parent.remarks as remarks
		from `tabCold Storage Transfer Item` child
		inner join `tabCold Storage Transfer` parent
			on parent.name = child.parent
			and child.parenttype = 'Cold Storage Transfer'
		where {" and ".join(conditions)}
		order by parent.posting_date asc, parent.creation asc, child.idx asc
		""",
		params,
		as_dict=True,
	)


def get_common_query_params(filters):
	status_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
	return {
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
		"company": filters.get("company"),
		"customer": filters.get("customer"),
		"item": filters.get("item"),
		"warehouse": filters.get("warehouse"),
		"batch_no": filters.get("batch_no"),
		"docstatus": status_map.get(filters.get("status")),
	}


def get_common_parent_conditions(filters, doctype_key: str):
	conditions = [
		"parent.posting_date >= %(from_date)s",
		"parent.posting_date <= %(to_date)s",
		"ifnull(child.batch_no, '') != ''",
		"child.batch_no = %(batch_no)s",
	]
	if filters.get("company"):
		conditions.append("parent.company = %(company)s")
	if filters.get("item"):
		conditions.append("child.item = %(item)s")
	if filters.get("status"):
		conditions.append("parent.docstatus = %(docstatus)s")

	if filters.get("customer"):
		if doctype_key == "transfer":
			conditions.append(
				"""(
					ifnull(parent.customer, '') = %(customer)s
					or ifnull(parent.from_customer, '') = %(customer)s
					or ifnull(parent.to_customer, '') = %(customer)s
				)"""
			)
		else:
			conditions.append("parent.customer = %(customer)s")

	return conditions


def get_user_action_rows(filters, document_meta):
	if not document_meta:
		return []

	action_rows = []
	for key, meta in document_meta.items():
		action_rows.append(
			{
				"event_timestamp": meta.get("creation"),
				"posting_date": None,
				"record_type": "User Action",
				"event_type": "Created",
				"reference_doctype": key[0],
				"reference_name": key[1],
				"batch_no": ", ".join(sorted(meta.get("batches") or [])),
				"item": "",
				"customer": meta.get("customer"),
				"from_warehouse": "",
				"to_warehouse": "",
				"qty": None,
				"status": meta.get("status"),
				"user": meta.get("owner"),
				"remarks": _("Document created"),
			}
		)

	docname_map = {}
	for doctype, docname in document_meta:
		docname_map.setdefault(doctype, set()).add(docname)

	for doctype in MOVEMENT_DOCTYPES:
		docnames = sorted(docname_map.get(doctype) or [])
		if not docnames:
			continue

		version_rows = frappe.get_all(
			"Version",
			filters={
				"ref_doctype": doctype,
				"docname": ["in", docnames],
			},
			fields=["docname", "owner", "creation", "data"],
			order_by="creation asc",
			limit_page_length=0,
		)

		for version_row in version_rows:
			meta = document_meta.get((doctype, version_row.docname), {})
			action_type, action_remarks = parse_version_payload(version_row.data)
			action_rows.append(
				{
					"event_timestamp": version_row.creation,
					"posting_date": None,
					"record_type": "User Action",
					"event_type": action_type,
					"reference_doctype": doctype,
					"reference_name": version_row.docname,
					"batch_no": ", ".join(sorted(meta.get("batches") or [])),
					"item": "",
					"customer": meta.get("customer"),
					"from_warehouse": "",
					"to_warehouse": "",
					"qty": None,
					"status": meta.get("status"),
					"user": version_row.owner,
					"remarks": action_remarks,
				}
			)

	return action_rows


def parse_version_payload(payload_text: str | None) -> tuple[str, str]:
	if not payload_text:
		return "Updated", _("Change captured in Version")

	try:
		payload = payload_text if isinstance(payload_text, dict) else json.loads(payload_text)
	except (TypeError, ValueError, json.JSONDecodeError):
		return "Updated", _("Version payload could not be parsed")

	changed_entries = payload.get("changed") or []
	added_entries = payload.get("added") or []
	removed_entries = payload.get("removed") or []
	row_changed_entries = payload.get("row_changed") or []

	docstatus_transition = None
	amend_detected = False
	changed_fields = []

	for entry in changed_entries:
		if not isinstance(entry, (list, tuple)) or len(entry) < 3:
			continue
		fieldname, old_value, new_value = entry[0], entry[1], entry[2]
		if fieldname == "docstatus":
			docstatus_transition = normalize_status(old_value), normalize_status(new_value)
		elif fieldname == "amended_from" and new_value:
			amend_detected = True

		if fieldname not in SYSTEM_VERSION_FIELDS:
			changed_fields.append(fieldname)

	action_type = classify_action(docstatus_transition, amend_detected, added_entries, removed_entries, row_changed_entries)
	action_remarks = build_action_remarks(changed_fields, added_entries, removed_entries, row_changed_entries)
	return action_type, action_remarks


def normalize_status(value) -> int | None:
	try:
		return int(value)
	except Exception:
		return None


def classify_action(docstatus_transition, amend_detected, added_entries, removed_entries, row_changed_entries) -> str:
	if docstatus_transition == (0, 1):
		return "Submitted"
	if docstatus_transition == (1, 2):
		return "Cancelled"
	if docstatus_transition == (2, 0) or amend_detected:
		return "Amended"
	if added_entries or removed_entries or row_changed_entries:
		return "Row Update"
	return "Updated"


def build_action_remarks(changed_fields, added_entries, removed_entries, row_changed_entries) -> str:
	parts = []
	unique_fields = []
	for fieldname in changed_fields:
		if fieldname not in unique_fields:
			unique_fields.append(fieldname)
	if unique_fields:
		parts.append(_("Changed fields: {0}").format(", ".join(unique_fields[:8])))
	if added_entries:
		parts.append(_("Rows added: {0}").format(len(added_entries)))
	if removed_entries:
		parts.append(_("Rows removed: {0}").format(len(removed_entries)))
	if row_changed_entries:
		parts.append(_("Rows changed: {0}").format(len(row_changed_entries)))
	return " | ".join(parts) if parts else _("Change captured in Version")


def get_chart_data(movement_rows):
	if not movement_rows:
		return None

	movement_qty = {"Inward": 0.0, "Outward": 0.0, "Transfer": 0.0}
	for row in movement_rows:
		event_type = row.get("event_type") or ""
		qty = flt(row.get("qty"))
		if event_type.startswith("Inward"):
			movement_qty["Inward"] += qty
		elif event_type.startswith("Outward"):
			movement_qty["Outward"] += qty
		elif event_type.startswith("Transfer"):
			movement_qty["Transfer"] += qty

	return {
		"data": {
			"labels": ["Inward", "Outward", "Transfer"],
			"datasets": [
				{
					"name": _("Qty"),
					"values": [
						movement_qty["Inward"],
						movement_qty["Outward"],
						movement_qty["Transfer"],
					],
				}
			],
		},
		"type": "bar",
		"colors": ["#0ea5e9"],
	}


def get_report_summary(movement_rows, action_rows):
	total_inward = sum(flt(row.get("qty")) for row in movement_rows if (row.get("event_type") or "").startswith("Inward"))
	total_outward = sum(
		flt(row.get("qty")) for row in movement_rows if (row.get("event_type") or "").startswith("Outward")
	)
	total_transfer = sum(
		flt(row.get("qty")) for row in movement_rows if (row.get("event_type") or "").startswith("Transfer")
	)
	unique_documents = len({(row.get("reference_doctype"), row.get("reference_name")) for row in movement_rows})

	return [
		{
			"value": len(movement_rows),
			"label": _("Movement Entries"),
			"datatype": "Int",
			"indicator": "Blue",
		},
		{
			"value": len(action_rows),
			"label": _("User Actions"),
			"datatype": "Int",
			"indicator": "Purple",
		},
		{
			"value": unique_documents,
			"label": _("Documents"),
			"datatype": "Int",
			"indicator": "Orange",
		},
		{
			"value": total_inward,
			"label": _("Inward Qty"),
			"datatype": "Float",
			"indicator": "Green",
		},
		{
			"value": total_outward,
			"label": _("Outward Qty"),
			"datatype": "Float",
			"indicator": "Red",
		},
		{
			"value": total_transfer,
			"label": _("Transfer Qty"),
			"datatype": "Float",
			"indicator": "Teal",
		},
	]
