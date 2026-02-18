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
			"label": _("Outward"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Cold Storage Outward",
			"width": 180,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 180,
		},
		{"label": _("Total Qty"), "fieldname": "total_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Total Charges"), "fieldname": "total_charges", "fieldtype": "Currency", "width": 130},
		{
			"label": _("Stock Entry"),
			"fieldname": "stock_entry",
			"fieldtype": "Link",
			"options": "Stock Entry",
			"width": 170,
		},
		{
			"label": _("Sales Invoice"),
			"fieldname": "sales_invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 170,
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
	]


def get_data(filters):
	db_filters = {}
	if filters.get("company"):
		db_filters["company"] = filters.company
	if filters.get("customer"):
		db_filters["customer"] = filters.customer
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
		"Cold Storage Outward",
		fields=[
			"name",
			"posting_date",
			"customer",
			"total_qty",
			"total_charges",
			"stock_entry",
			"sales_invoice",
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

	by_customer = {}
	for row in data:
		customer = row.get("customer") or _("Unknown")
		by_customer[customer] = flt(by_customer.get(customer)) + flt(row.get("total_qty"))

	top_customers = sorted(by_customer.items(), key=lambda x: x[1], reverse=True)[:8]
	if not top_customers:
		return None

	return {
		"data": {
			"labels": [c for c, _v in top_customers],
			"datasets": [{"name": _("Qty"), "values": [v for _c, v in top_customers]}],
		},
		"type": "bar",
		"colors": ["#ef4444"],
	}


def get_report_summary(data):
	total_qty = sum(flt(row.get("total_qty")) for row in data)
	total_charges = sum(flt(row.get("total_charges")) for row in data)
	return [
		{"value": len(data), "label": _("Outward Dispatches"), "datatype": "Int", "indicator": "Blue"},
		{"value": total_qty, "label": _("Total Outward Qty"), "datatype": "Float", "indicator": "Red"},
		{
			"value": total_charges,
			"label": _("Total Outward Charges"),
			"datatype": "Currency",
			"indicator": "Orange",
		},
	]
