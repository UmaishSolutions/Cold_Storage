import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

MOVEMENT_ORDER = {"Inward": 1, "Transfer": 2, "Outward": 3}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("batch_no"):
		frappe.throw(_("Batch is required for lot traceability."))

	if filters.get("from_date"):
		filters.from_date = getdate(filters.get("from_date"))
	if filters.get("to_date"):
		filters.to_date = getdate(filters.get("to_date"))
	else:
		filters.to_date = getdate(nowdate())

	if filters.get("from_date") and filters.from_date > filters.to_date:
		filters.from_date, filters.to_date = filters.to_date, filters.from_date

	columns = get_columns()
	events = get_lineage_events(filters)
	data = build_audit_rows(events)
	chart = get_chart(data)
	message = _(
		"Lineage is sequenced by posting date and document creation: Inward -> Transfer hops -> Outward. "
		"Graph payload is included in chart.custom_trace_graph for downstream visualization."
	)
	summary = get_summary(data)
	return columns, data, message, chart, summary


def get_columns():
	return [
		{"label": _("Trace Key"), "fieldname": "trace_key", "fieldtype": "Data", "width": 220},
		{"label": _("Hop #"), "fieldname": "hop_no", "fieldtype": "Int", "width": 70},
		{"label": _("Event Timestamp"), "fieldname": "event_timestamp", "fieldtype": "Datetime", "width": 170},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": _("Movement"), "fieldname": "movement_type", "fieldtype": "Data", "width": 95},
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
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 145},
		{"label": _("Batch"), "fieldname": "batch_no", "fieldtype": "Link", "options": "Batch", "width": 170},
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
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 95},
		{"label": _("Signed Qty"), "fieldname": "signed_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Running Balance"), "fieldname": "running_balance", "fieldtype": "Float", "width": 130},
		{
			"label": _("Customer Context"),
			"fieldname": "customer_context",
			"fieldtype": "Data",
			"width": 220,
		},
		{"label": _("Transfer Type"), "fieldname": "transfer_type", "fieldtype": "Data", "width": 160},
		{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 300},
	]


def get_lineage_events(filters):
	params = {
		"company": filters.get("company") or "",
		"customer": filters.get("customer") or "",
		"item": filters.get("item") or "",
		"batch_no": filters.get("batch_no"),
		"warehouse": filters.get("warehouse") or "",
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
	}

	rows = []
	rows.extend(get_inward_events(params))
	rows.extend(get_transfer_events(params))
	rows.extend(get_outward_events(params))

	rows.sort(
		key=lambda row: (
			row.get("posting_date") or getdate(nowdate()),
			row.get("event_timestamp") or "",
			MOVEMENT_ORDER.get(row.get("movement_type"), 99),
			row.get("reference_name") or "",
			row.get("line_no") or 0,
		)
	)
	return rows


def get_date_conditions(alias):
	return [
		f"(%(from_date)s is null or {alias}.posting_date >= %(from_date)s)",
		f"({alias}.posting_date <= %(to_date)s)",
	]


def get_inward_events(params):
	conditions = [
		"parent.docstatus = 1",
		"child.parenttype = 'Cold Storage Inward'",
		"child.batch_no = %(batch_no)s",
		"(%(company)s = '' or parent.company = %(company)s)",
		"(%(customer)s = '' or parent.customer = %(customer)s)",
		"(%(item)s = '' or child.item = %(item)s)",
		"(%(warehouse)s = '' or child.warehouse = %(warehouse)s)",
	]
	conditions.extend(get_date_conditions("parent"))

	return frappe.db.sql(
		f"""
		select
			concat(child.batch_no, ' :: ', child.item) as trace_key,
			parent.creation as event_timestamp,
			parent.posting_date as posting_date,
			'Inward' as movement_type,
			'Cold Storage Inward' as reference_doctype,
			parent.name as reference_name,
			child.idx as line_no,
			child.item as item,
			child.batch_no as batch_no,
			'' as from_warehouse,
			child.warehouse as to_warehouse,
			child.qty as qty,
			parent.customer as customer_context,
			'' as transfer_type,
			parent.remarks as remarks
		from `tabCold Storage Inward Item` child
		inner join `tabCold Storage Inward` parent on parent.name = child.parent
		where {' and '.join(conditions)}
		""",
		params,
		as_dict=True,
	)


def get_transfer_events(params):
	conditions = [
		"parent.docstatus = 1",
		"child.parenttype = 'Cold Storage Transfer'",
		"child.batch_no = %(batch_no)s",
		"(%(company)s = '' or parent.company = %(company)s)",
		"(%(item)s = '' or child.item = %(item)s)",
		"(%(warehouse)s = '' or child.source_warehouse = %(warehouse)s or child.target_warehouse = %(warehouse)s)",
		"(%(customer)s = '' or ifnull(parent.customer, '') = %(customer)s or ifnull(parent.from_customer, '') = %(customer)s or ifnull(parent.to_customer, '') = %(customer)s)",
	]
	conditions.extend(get_date_conditions("parent"))

	return frappe.db.sql(
		f"""
		select
			concat(child.batch_no, ' :: ', child.item) as trace_key,
			parent.creation as event_timestamp,
			parent.posting_date as posting_date,
			'Transfer' as movement_type,
			'Cold Storage Transfer' as reference_doctype,
			parent.name as reference_name,
			child.idx as line_no,
			child.item as item,
			child.batch_no as batch_no,
			ifnull(child.source_warehouse, '') as from_warehouse,
			ifnull(child.target_warehouse, '') as to_warehouse,
			child.qty as qty,
			case
				when parent.transfer_type = 'Ownership Transfer'
				then concat(ifnull(parent.from_customer, ''), ' -> ', ifnull(parent.to_customer, ''))
				else ifnull(parent.customer, '')
			end as customer_context,
			ifnull(parent.transfer_type, '') as transfer_type,
			parent.remarks as remarks
		from `tabCold Storage Transfer Item` child
		inner join `tabCold Storage Transfer` parent on parent.name = child.parent
		where {' and '.join(conditions)}
		""",
		params,
		as_dict=True,
	)


def get_outward_events(params):
	conditions = [
		"parent.docstatus = 1",
		"child.parenttype = 'Cold Storage Outward'",
		"child.batch_no = %(batch_no)s",
		"(%(company)s = '' or parent.company = %(company)s)",
		"(%(customer)s = '' or parent.customer = %(customer)s)",
		"(%(item)s = '' or child.item = %(item)s)",
		"(%(warehouse)s = '' or child.warehouse = %(warehouse)s)",
	]
	conditions.extend(get_date_conditions("parent"))

	return frappe.db.sql(
		f"""
		select
			concat(child.batch_no, ' :: ', child.item) as trace_key,
			parent.creation as event_timestamp,
			parent.posting_date as posting_date,
			'Outward' as movement_type,
			'Cold Storage Outward' as reference_doctype,
			parent.name as reference_name,
			child.idx as line_no,
			child.item as item,
			child.batch_no as batch_no,
			child.warehouse as from_warehouse,
			'' as to_warehouse,
			child.qty as qty,
			parent.customer as customer_context,
			'' as transfer_type,
			parent.remarks as remarks
		from `tabCold Storage Outward Item` child
		inner join `tabCold Storage Outward` parent on parent.name = child.parent
		where {' and '.join(conditions)}
		""",
		params,
		as_dict=True,
	)


def build_audit_rows(events):
	grouped = {}
	for row in events:
		grouped.setdefault(row.get("trace_key"), []).append(row)

	result = []
	for trace_key in sorted(grouped):
		running_balance = 0.0
		hop_no = 0
		for row in grouped[trace_key]:
			hop_no += 1
			qty = flt(row.get("qty"))
			signed_qty = qty
			if row.get("movement_type") == "Outward":
				signed_qty = -qty
			elif row.get("movement_type") == "Transfer":
				signed_qty = 0.0

			running_balance = running_balance + signed_qty
			result.append(
				{
					**row,
					"hop_no": hop_no,
					"qty": qty,
					"signed_qty": signed_qty,
					"running_balance": running_balance,
				}
			)

	return result


def get_chart(data):
	if not data:
		return None

	labels = [f"H{row.get('hop_no')} {row.get('movement_type')}" for row in data[:40]]
	qty_values = [flt(row.get("qty")) for row in data[:40]]
	running_values = [flt(row.get("running_balance")) for row in data[:40]]

	chart = {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Movement Qty"), "chartType": "bar", "values": qty_values},
				{"name": _("Running Balance"), "chartType": "line", "values": running_values},
			],
		},
		"type": "axis-mixed",
		"colors": ["#0ea5e9", "#f97316"],
	}

	chart["custom_trace_graph"] = build_trace_graph_payload(data)
	return chart


def build_trace_graph_payload(data):
	nodes = {}
	links = []

	grouped = {}
	for row in data:
		grouped.setdefault(row.get("trace_key"), []).append(row)

	for trace_key, rows in grouped.items():
		for row in rows:
			node_name = f"{row.get('movement_type')} | {row.get('reference_name')}"
			nodes[node_name] = {
				"name": node_name,
				"movement_type": row.get("movement_type"),
				"trace_key": trace_key,
			}

		for index in range(1, len(rows)):
			source = f"{rows[index - 1].get('movement_type')} | {rows[index - 1].get('reference_name')}"
			target = f"{rows[index].get('movement_type')} | {rows[index].get('reference_name')}"
			links.append(
				{
					"source": source,
					"target": target,
					"value": max(flt(rows[index - 1].get("qty")), flt(rows[index].get("qty"))),
					"trace_key": trace_key,
				}
			)

	return {"nodes": list(nodes.values()), "links": links}


def get_summary(data):
	inward_qty = sum(flt(row.get("qty")) for row in data if row.get("movement_type") == "Inward")
	outward_qty = sum(flt(row.get("qty")) for row in data if row.get("movement_type") == "Outward")
	transfer_hops = sum(1 for row in data if row.get("movement_type") == "Transfer")
	trace_keys = {row.get("trace_key") for row in data if row.get("trace_key")}
	closing_balance = sum(flt(row.get("signed_qty")) for row in data)

	return [
		{"label": _("Trace Keys"), "value": len(trace_keys), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Total Inward Qty"), "value": inward_qty, "datatype": "Float", "indicator": "Green"},
		{"label": _("Transfer Hops"), "value": transfer_hops, "datatype": "Int", "indicator": "Orange"},
		{"label": _("Total Outward Qty"), "value": outward_qty, "datatype": "Float", "indicator": "Red"},
		{"label": _("Net Qty Balance"), "value": closing_balance, "datatype": "Float", "indicator": "Purple"},
	]
