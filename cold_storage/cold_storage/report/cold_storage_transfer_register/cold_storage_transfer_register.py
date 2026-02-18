import frappe
from frappe import _
from frappe.utils import flt

DOCSTATUS_LABELS = {0: "Draft", 1: "Submitted", 2: "Cancelled"}


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
			"label": _("Transfer"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Cold Storage Transfer",
			"width": 180,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": _("Transfer Type"), "fieldname": "transfer_type", "fieldtype": "Data", "width": 180},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 160,
		},
		{
			"label": _("From Customer"),
			"fieldname": "from_customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 160,
		},
		{
			"label": _("To Customer"),
			"fieldname": "to_customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 160,
		},
		{"label": _("Total Qty"), "fieldname": "total_qty", "fieldtype": "Float", "width": 110},
		{
			"label": _("Transfer Charges"),
			"fieldname": "total_transfer_charges",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Stock Entry"),
			"fieldname": "stock_entry",
			"fieldtype": "Link",
			"options": "Stock Entry",
			"width": 170,
		},
		{
			"label": _("Journal Entry"),
			"fieldname": "journal_entry",
			"fieldtype": "Link",
			"options": "Journal Entry",
			"width": 170,
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
	]


def get_data(filters):
	db_filters = {}
	if filters.get("company"):
		db_filters["company"] = filters.company
	if filters.get("transfer_type"):
		db_filters["transfer_type"] = filters.transfer_type
	if filters.get("customer"):
		db_filters["customer"] = filters.customer
	if filters.get("from_customer"):
		db_filters["from_customer"] = filters.from_customer
	if filters.get("to_customer"):
		db_filters["to_customer"] = filters.to_customer
	if filters.get("status"):
		docstatus_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
		db_filters["docstatus"] = docstatus_map.get(filters.status)

	if filters.get("from_date") and filters.get("to_date"):
		db_filters["posting_date"] = ["between", [filters.from_date, filters.to_date]]
	elif filters.get("from_date"):
		db_filters["posting_date"] = [">=", filters.from_date]
	elif filters.get("to_date"):
		db_filters["posting_date"] = ["<=", filters.to_date]

	rows = frappe.get_all(
		"Cold Storage Transfer",
		fields=[
			"name",
			"posting_date",
			"transfer_type",
			"customer",
			"from_customer",
			"to_customer",
			"total_qty",
			"total_transfer_charges",
			"stock_entry",
			"journal_entry",
			"docstatus",
		],
		filters=db_filters,
		order_by="posting_date desc, creation desc",
	)

	for row in rows:
		row["status"] = DOCSTATUS_LABELS.get(row.pop("docstatus"), "")
	return rows


def get_chart_data(data):
	if not data:
		return None

	by_type = {}
	for row in data:
		transfer_type = row.get("transfer_type") or _("Unknown")
		by_type[transfer_type] = flt(by_type.get(transfer_type)) + flt(row.get("total_qty"))

	labels = list(by_type.keys())
	values = [by_type[label] for label in labels]
	if not values:
		return None

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Qty"), "values": values}],
		},
		"type": "bar",
		"colors": ["#2563eb"],
	}


def get_report_summary(data):
	total_qty = sum(flt(row.get("total_qty")) for row in data)
	total_charges = sum(flt(row.get("total_transfer_charges")) for row in data)
	return [
		{"value": len(data), "label": _("Transfers"), "datatype": "Int", "indicator": "Blue"},
		{"value": total_qty, "label": _("Total Transfer Qty"), "datatype": "Float", "indicator": "Green"},
		{
			"value": total_charges,
			"label": _("Total Transfer Charges"),
			"datatype": "Currency",
			"indicator": "Orange",
		},
	]
