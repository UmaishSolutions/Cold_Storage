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
			"width": 180,
		},
	]


def get_data(filters):
	rows = frappe.db.sql(
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

	for row in rows:
		row.available_stock_qty = flt(row.available_stock_qty)

	return rows


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
	return [
		{"value": len(data), "label": _("Customers"), "datatype": "Int", "indicator": "Blue"},
		{
			"value": total_available_stock,
			"label": _("Total Available Stock Qty"),
			"datatype": "Float",
			"indicator": "Green",
		},
	]
