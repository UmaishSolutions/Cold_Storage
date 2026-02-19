import frappe
from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
	get_default_company,
)
from erpnext.stock.doctype.batch.batch import get_batch_qty
from frappe import _
from frappe.utils import cint, date_diff, flt, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("as_on_date"):
		filters.as_on_date = nowdate()

	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	report_summary = get_report_summary(data)
	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"label": _("Batch"),
			"fieldname": "batch_no",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 140,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 190,
		},
		{
			"label": _("Item"),
			"fieldname": "item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 220},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 180,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 180,
		},
		{"label": _("Available Qty"), "fieldname": "balance_qty", "fieldtype": "Float", "width": 120},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 90},
		{
			"label": _("First Movement"),
			"fieldname": "first_movement_date",
			"fieldtype": "Date",
			"width": 125,
		},
		{
			"label": _("Last Movement"),
			"fieldname": "last_movement_date",
			"fieldtype": "Date",
			"width": 125,
		},
		{"label": _("Age (Days)"), "fieldname": "age_days", "fieldtype": "Int", "width": 95},
	]


def get_data(filters):
	report_company = get_report_company(filters)

	conditions = [
		"se.docstatus = 1",
		"ifnull(sed.batch_no, '') != ''",
		"se.posting_date <= %(as_on_date)s",
	]

	params = {
		"as_on_date": filters.as_on_date,
		"company": report_company,
		"customer": filters.get("customer"),
		"item": filters.get("item"),
		"warehouse": filters.get("warehouse"),
		"batch_no": filters.get("batch_no"),
	}

	if report_company:
		conditions.append("w.company = %(company)s")
	if filters.get("customer"):
		conditions.append("b.custom_customer = %(customer)s")
	if filters.get("item"):
		conditions.append("sed.item_code = %(item)s")
	if filters.get("warehouse"):
		conditions.append("ifnull(sed.t_warehouse, sed.s_warehouse) = %(warehouse)s")
	if filters.get("batch_no"):
		conditions.append("sed.batch_no = %(batch_no)s")

	rows = frappe.db.sql(
		f"""
		select
			sed.batch_no as batch_no,
			b.custom_customer as customer,
			sed.item_code as item,
			i.item_name as item_name,
			ifnull(sed.t_warehouse, sed.s_warehouse) as warehouse,
			w.company as company,
			i.stock_uom as uom,
			min(se.posting_date) as first_movement_date,
			max(se.posting_date) as last_movement_date
		from `tabStock Entry Detail` sed
		inner join `tabStock Entry` se on se.name = sed.parent
		left join `tabBatch` b on b.name = sed.batch_no
		left join `tabItem` i on i.name = sed.item_code
		left join `tabWarehouse` w on w.name = ifnull(sed.t_warehouse, sed.s_warehouse)
		where {" and ".join(conditions)}
		group by
			sed.batch_no,
			b.custom_customer,
			sed.item_code,
			i.item_name,
			ifnull(sed.t_warehouse, sed.s_warehouse),
			w.company,
			i.stock_uom
		order by max(se.posting_date) desc, sed.batch_no asc
		""",
		params,
		as_dict=True,
	)

	data = []
	include_zero_balance = cint(filters.get("include_zero_balance"))

	for row in rows:
		balance_qty = (
			flt(get_batch_qty(batch_no=row.batch_no, warehouse=row.warehouse))
			if row.batch_no and row.warehouse
			else 0.0
		)
		if not include_zero_balance and balance_qty <= 0:
			continue

		row.balance_qty = balance_qty
		row.age_days = (
			max(cint(date_diff(filters.as_on_date, row.first_movement_date)), 0)
			if row.first_movement_date
			else 0
		)
		data.append(row)

	return data


def get_report_company(filters):
	"""Always scope report to Cold Storage Settings company when available."""
	try:
		company = get_default_company()
	except Exception:
		company = None

	return company or filters.get("company")


def get_chart_data(data):
	if not data:
		return None

	by_customer = {}
	for row in data:
		customer = row.get("customer") or _("Unassigned")
		by_customer[customer] = flt(by_customer.get(customer)) + flt(row.get("balance_qty"))

	top_customers = sorted(by_customer.items(), key=lambda x: x[1], reverse=True)[:8]
	if not top_customers:
		return None

	return {
		"data": {
			"labels": [customer for customer, _qty in top_customers],
			"datasets": [{"name": _("Available Qty"), "values": [qty for _customer, qty in top_customers]}],
		},
		"type": "bar",
		"colors": ["#0d9488"],
	}


def get_report_summary(data):
	total_qty = sum(flt(row.get("balance_qty")) for row in data)
	unique_customers = len({row.get("customer") for row in data if row.get("customer")})
	unique_warehouses = len({row.get("warehouse") for row in data if row.get("warehouse")})

	return [
		{"value": len(data), "label": _("Batch-Location Rows"), "datatype": "Int", "indicator": "Blue"},
		{"value": total_qty, "label": _("Total Available Qty"), "datatype": "Float", "indicator": "Green"},
		{"value": unique_customers, "label": _("Customers"), "datatype": "Int", "indicator": "Orange"},
		{"value": unique_warehouses, "label": _("Warehouses"), "datatype": "Int", "indicator": "Purple"},
	]
