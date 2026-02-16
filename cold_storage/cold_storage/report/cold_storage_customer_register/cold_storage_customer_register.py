import frappe
from frappe import _
from frappe.utils import flt, nowdate


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
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 260,
		},
		{
			"label": _("Available Stock Qty"),
			"fieldname": "available_stock_qty",
			"fieldtype": "Float",
			"width": 170,
		},
		{"label": _("Inward Qty"), "fieldname": "inward_qty", "fieldtype": "Float", "width": 130},
		{"label": _("Outward Qty"), "fieldname": "outward_qty", "fieldtype": "Float", "width": 130},
		{"label": _("Transfer Qty"), "fieldname": "transfer_qty", "fieldtype": "Float", "width": 130},
	]


def get_data(filters):
	available_rows = frappe.db.sql(
		"""
		select
			batch.custom_customer as customer,
			round(sum(stock.qty), 3) as available_stock_qty
		from (
			select
				sle.batch_no,
				sle.actual_qty as qty,
				sle.warehouse
			from `tabStock Ledger Entry` sle
			where ifnull(sle.is_cancelled, 0) = 0
				and ifnull(sle.batch_no, '') != ''
				and sle.posting_date <= %(as_on_date)s

			union all

			select
				sbe.batch_no,
				sbe.qty as qty,
				sle.warehouse
			from `tabStock Ledger Entry` sle
			inner join `tabSerial and Batch Entry` sbe
				on sbe.parent = sle.serial_and_batch_bundle
			where ifnull(sle.is_cancelled, 0) = 0
				and ifnull(sle.batch_no, '') = ''
				and ifnull(sle.serial_and_batch_bundle, '') != ''
				and ifnull(sbe.batch_no, '') != ''
				and ifnull(sbe.is_cancelled, 0) = 0
				and sle.posting_date <= %(as_on_date)s
		) stock
		inner join `tabBatch` batch on batch.name = stock.batch_no
		inner join `tabWarehouse` wh on wh.name = stock.warehouse
		where ifnull(batch.custom_customer, '') != ''
			and ifnull(batch.disabled, 0) = 0
			and (%(company)s = '' or wh.company = %(company)s)
			and (%(customer)s = '' or batch.custom_customer = %(customer)s)
		group by batch.custom_customer
		having round(sum(stock.qty), 3) > 0
		order by available_stock_qty desc, customer asc
		""",
		{
			"as_on_date": filters.as_on_date,
			"company": filters.get("company") or "",
			"customer": filters.get("customer") or "",
		},
		as_dict=True,
	)

	customer_map = {}
	for row in available_rows:
		customer = (row.get("customer") or "").strip()
		if not customer:
			continue
		customer_map[customer] = frappe._dict(
			{
				"customer": customer,
					"available_stock_qty": flt(row.available_stock_qty),
					"inward_qty": 0.0,
					"outward_qty": 0.0,
					"transfer_qty": 0.0,
				}
			)

	if not customer_map:
		return []

	inward_qty_map = get_submitted_qty_map("Cold Storage Inward", "customer", filters)
	outward_qty_map = get_submitted_qty_map("Cold Storage Outward", "customer", filters)
	transfer_qty_map = get_transfer_submitted_qty_map(filters)

	for customer, row in customer_map.items():
		row.inward_qty = flt(inward_qty_map.get(customer))
		row.outward_qty = flt(outward_qty_map.get(customer))
		row.transfer_qty = flt(transfer_qty_map.get(customer))

	return sorted(
		customer_map.values(),
		key=lambda row: (-flt(row.get("available_stock_qty")), row.get("customer") or ""),
	)


def get_submitted_qty_map(doctype, customer_field, filters):
	rows = frappe.db.sql(
		f"""
		select
			{customer_field} as customer,
			sum(total_qty) as qty
		from `tab{doctype}`
		where docstatus = 1
			and posting_date <= %(as_on_date)s
			and ifnull({customer_field}, '') != ''
			and (%(company)s = '' or company = %(company)s)
			and (%(customer)s = '' or {customer_field} = %(customer)s)
		group by {customer_field}
		""",
		{
			"as_on_date": filters.as_on_date,
			"company": filters.get("company") or "",
			"customer": filters.get("customer") or "",
		},
		as_dict=True,
	)
	return {(row.get("customer") or "").strip(): flt(row.get("qty")) for row in rows if row.get("customer")}


def get_transfer_submitted_qty_map(filters):
	params = {
		"as_on_date": filters.as_on_date,
		"company": filters.get("company") or "",
		"customer": filters.get("customer") or "",
	}
	qty_map = {}

	for customer_field, extra_condition in (
		("customer", "and ifnull(transfer_type, '') != 'Ownership Transfer'"),
		("from_customer", "and ifnull(transfer_type, '') = 'Ownership Transfer'"),
		("to_customer", "and ifnull(transfer_type, '') = 'Ownership Transfer'"),
	):
		rows = frappe.db.sql(
			f"""
			select
				{customer_field} as customer,
				sum(total_qty) as qty
			from `tabCold Storage Transfer`
			where docstatus = 1
				and posting_date <= %(as_on_date)s
				and ifnull({customer_field}, '') != ''
				{extra_condition}
				and (%(company)s = '' or company = %(company)s)
				and (%(customer)s = '' or {customer_field} = %(customer)s)
			group by {customer_field}
			""",
			params,
			as_dict=True,
		)
		for row in rows:
			customer = (row.get("customer") or "").strip()
			if not customer:
				continue
			qty_map[customer] = flt(qty_map.get(customer)) + flt(row.get("qty"))

	return qty_map


def get_chart_data(data):
	if not data:
		return None

	top_rows = sorted(data, key=lambda row: flt(row.get("available_stock_qty")), reverse=True)[:8]
	if not top_rows:
		return None

	return {
		"data": {
			"labels": [row.get("customer") for row in top_rows],
			"datasets": [
				{
					"name": _("Available Stock Qty"),
					"values": [flt(row.get("available_stock_qty")) for row in top_rows],
				}
			],
		},
		"type": "bar",
		"colors": ["#16a34a"],
	}


def get_report_summary(data):
	total_available_stock = sum(flt(row.get("available_stock_qty")) for row in data)
	total_inward_qty = sum(flt(row.get("inward_qty")) for row in data)
	total_outward_qty = sum(flt(row.get("outward_qty")) for row in data)
	total_transfer_qty = sum(flt(row.get("transfer_qty")) for row in data)

	return [
		{"value": len(data), "label": _("Customers"), "datatype": "Int", "indicator": "Blue"},
		{
			"value": total_available_stock,
			"label": _("Total Available Stock Qty"),
			"datatype": "Float",
			"indicator": "Green",
		},
		{"value": total_inward_qty, "label": _("Total Inward Qty"), "datatype": "Float", "indicator": "Green"},
		{"value": total_outward_qty, "label": _("Total Outward Qty"), "datatype": "Float", "indicator": "Orange"},
		{
			"value": total_transfer_qty,
			"label": _("Total Transfer Qty"),
			"datatype": "Float",
			"indicator": "Blue",
		},
	]
