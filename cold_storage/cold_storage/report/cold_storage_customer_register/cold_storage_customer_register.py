import frappe
from frappe import _
from frappe.utils import flt

DOCSTATUS_MAP = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
TABLE_BY_DOCTYPE = {
	"Cold Storage Inward": "`tabCold Storage Inward`",
	"Cold Storage Outward": "`tabCold Storage Outward`",
	"Cold Storage Transfer": "`tabCold Storage Transfer`",
}
ALLOWED_FILTER_FIELDS = {"company", "docstatus", "posting_date", "customer", "from_customer", "to_customer"}
ALLOWED_CUSTOMER_FIELDS = {"customer", "from_customer", "to_customer"}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	report_summary = get_report_summary(data)
	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 220,
		},
		{"label": _("Inward Qty"), "fieldname": "inward_qty", "fieldtype": "Float", "width": 120},
		{"label": _("Outward Qty"), "fieldname": "outward_qty", "fieldtype": "Float", "width": 120},
		{"label": _("Transfer In Qty"), "fieldname": "transfer_in_qty", "fieldtype": "Float", "width": 140},
		{"label": _("Transfer Out Qty"), "fieldname": "transfer_out_qty", "fieldtype": "Float", "width": 140},
		{
			"label": _("Internal Transfer Qty"),
			"fieldname": "transfer_internal_qty",
			"fieldtype": "Float",
			"width": 160,
		},
		{
			"label": _("Total Transfer Qty"),
			"fieldname": "total_transfer_qty",
			"fieldtype": "Float",
			"width": 150,
		},
		{"label": _("Net Qty"), "fieldname": "net_qty", "fieldtype": "Float", "width": 120},
		{"label": _("Total Movement Qty"), "fieldname": "movement_qty", "fieldtype": "Float", "width": 150},
	]


def get_data(filters):
	common_filters = get_common_filters(filters)
	customer_filter = (filters.get("customer") or "").strip()

	customer_map = {}

	inward_filters = dict(common_filters)
	if customer_filter:
		inward_filters["customer"] = customer_filter
	add_grouped_rows(
		customer_map,
		"Cold Storage Inward",
		inward_filters,
		"customer",
		"inward_qty",
	)

	outward_filters = dict(common_filters)
	if customer_filter:
		outward_filters["customer"] = customer_filter
	add_grouped_rows(
		customer_map,
		"Cold Storage Outward",
		outward_filters,
		"customer",
		"outward_qty",
	)

	transfer_internal_filters = dict(common_filters)
	transfer_internal_filters["customer"] = customer_filter or ["!=", ""]
	add_grouped_rows(
		customer_map,
		"Cold Storage Transfer",
		transfer_internal_filters,
		"customer",
		"transfer_internal_qty",
	)

	transfer_out_filters = dict(common_filters)
	transfer_out_filters["from_customer"] = customer_filter or ["!=", ""]
	add_grouped_rows(
		customer_map,
		"Cold Storage Transfer",
		transfer_out_filters,
		"from_customer",
		"transfer_out_qty",
	)

	transfer_in_filters = dict(common_filters)
	transfer_in_filters["to_customer"] = customer_filter or ["!=", ""]
	add_grouped_rows(
		customer_map,
		"Cold Storage Transfer",
		transfer_in_filters,
		"to_customer",
		"transfer_in_qty",
	)

	data = []
	for row in customer_map.values():
		row["total_transfer_qty"] = (
			flt(row.get("transfer_in_qty"))
			+ flt(row.get("transfer_out_qty"))
			+ flt(row.get("transfer_internal_qty"))
		)
		row["net_qty"] = (
			flt(row.get("inward_qty"))
			+ flt(row.get("transfer_in_qty"))
			- flt(row.get("outward_qty"))
			- flt(row.get("transfer_out_qty"))
		)
		row["movement_qty"] = (
			flt(row.get("inward_qty")) + flt(row.get("outward_qty")) + flt(row.get("total_transfer_qty"))
		)
		data.append(row)

	data.sort(key=lambda row: (-flt(row.get("movement_qty")), row.get("customer") or ""))
	return data


def get_common_filters(filters):
	db_filters = {}
	if filters.get("company"):
		db_filters["company"] = filters.company

	status = DOCSTATUS_MAP.get(filters.get("status"))
	if status is not None:
		db_filters["docstatus"] = status

	if filters.get("from_date") and filters.get("to_date"):
		db_filters["posting_date"] = ["between", [filters.from_date, filters.to_date]]
	elif filters.get("from_date"):
		db_filters["posting_date"] = [">=", filters.from_date]
	elif filters.get("to_date"):
		db_filters["posting_date"] = ["<=", filters.to_date]

	return db_filters


def add_grouped_rows(customer_map, doctype, db_filters, customer_field, qty_field):
	if doctype not in TABLE_BY_DOCTYPE or customer_field not in ALLOWED_CUSTOMER_FIELDS:
		return

	where_clauses = [f"ifnull(`{customer_field}`, '') != ''"]
	params = {}

	for idx, (fieldname, value) in enumerate(db_filters.items(), start=1):
		if fieldname not in ALLOWED_FILTER_FIELDS:
			continue

		param_key = f"p{idx}"
		if isinstance(value, (list, tuple)) and len(value) == 2:
			operator = (value[0] or "").lower()
			operand = value[1]

			if operator == "between" and isinstance(operand, (list, tuple)) and len(operand) == 2:
				start_key = f"{param_key}_start"
				end_key = f"{param_key}_end"
				where_clauses.append(f"`{fieldname}` between %({start_key})s and %({end_key})s")
				params[start_key] = operand[0]
				params[end_key] = operand[1]
				continue

			if operator in {">=", "<=", "!="}:
				if operator == "!=" and operand == "":
					where_clauses.append(f"ifnull(`{fieldname}`, '') != %({param_key})s")
				else:
					where_clauses.append(f"`{fieldname}` {operator} %({param_key})s")
				params[param_key] = operand
				continue

		where_clauses.append(f"`{fieldname}` = %({param_key})s")
		params[param_key] = value

	rows = frappe.db.sql(
		f"""
		select
			`{customer_field}` as customer,
			sum(`total_qty`) as qty
		from {TABLE_BY_DOCTYPE[doctype]}
		where {" and ".join(where_clauses)}
		group by `{customer_field}`
		""",
		params,
		as_dict=True,
	)

	for row in rows:
		customer = (row.get("customer") or "").strip()
		if not customer:
			continue

		if customer not in customer_map:
			customer_map[customer] = frappe._dict(
				{
					"customer": customer,
					"inward_qty": 0.0,
					"outward_qty": 0.0,
					"transfer_in_qty": 0.0,
					"transfer_out_qty": 0.0,
					"transfer_internal_qty": 0.0,
					"total_transfer_qty": 0.0,
					"net_qty": 0.0,
					"movement_qty": 0.0,
				}
			)

		customer_map[customer][qty_field] = flt(customer_map[customer].get(qty_field)) + flt(row.get("qty"))


def get_chart_data(data):
	if not data:
		return None

	top_rows = sorted(data, key=lambda row: flt(row.get("movement_qty")), reverse=True)[:8]
	if not top_rows:
		return None

	return {
		"data": {
			"labels": [row.get("customer") for row in top_rows],
			"datasets": [
				{"name": _("Inward Qty"), "values": [flt(row.get("inward_qty")) for row in top_rows]},
				{"name": _("Outward Qty"), "values": [flt(row.get("outward_qty")) for row in top_rows]},
				{
					"name": _("Transfer Qty"),
					"values": [flt(row.get("total_transfer_qty")) for row in top_rows],
				},
			],
		},
		"type": "bar",
		"colors": ["#16a34a", "#ef4444", "#2563eb"],
	}


def get_report_summary(data):
	total_inward = sum(flt(row.get("inward_qty")) for row in data)
	total_outward = sum(flt(row.get("outward_qty")) for row in data)
	total_transfer = sum(flt(row.get("total_transfer_qty")) for row in data)
	total_net = sum(flt(row.get("net_qty")) for row in data)

	return [
		{"value": len(data), "label": _("Customers"), "datatype": "Int", "indicator": "Blue"},
		{"value": total_inward, "label": _("Total Inward Qty"), "datatype": "Float", "indicator": "Green"},
		{"value": total_outward, "label": _("Total Outward Qty"), "datatype": "Float", "indicator": "Red"},
		{"value": total_transfer, "label": _("Total Transfer Qty"), "datatype": "Float", "indicator": "Blue"},
		{
			"value": total_net,
			"label": _("Net Qty"),
			"datatype": "Float",
			"indicator": "Green" if total_net >= 0 else "Orange",
		},
	]
