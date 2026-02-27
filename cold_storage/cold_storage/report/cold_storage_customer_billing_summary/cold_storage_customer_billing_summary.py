import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.from_date = filters.get("from_date") or nowdate()
	filters.to_date = filters.get("to_date") or nowdate()

	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = get_summary(data)
	return columns, data, None, chart, summary


def get_columns():
	return [
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 230},
		{"label": _("Invoices"), "fieldname": "invoice_count", "fieldtype": "Int", "width": 100},
		{"label": _("Invoiced Amount"), "fieldname": "invoiced_amount", "fieldtype": "Currency", "width": 150},
		{"label": _("Outstanding Amount"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 150},
		{"label": _("Collected Amount"), "fieldname": "collected_amount", "fieldtype": "Currency", "width": 150},
		{"label": _("Collection %"), "fieldname": "collection_pct", "fieldtype": "Percent", "width": 120},
	]


def get_data(filters):
	rows = frappe.db.sql(
		"""
		select
			customer,
			count(name) as invoice_count,
			sum(grand_total) as invoiced_amount,
			sum(outstanding_amount) as outstanding_amount
		from `tabSales Invoice`
		where docstatus = 1
			and posting_date between %(from_date)s and %(to_date)s
			and (%(company)s = '' or company = %(company)s)
			and (%(customer)s = '' or customer = %(customer)s)
		group by customer
		order by sum(grand_total) desc, customer asc
		""",
		{
			"from_date": filters.from_date,
			"to_date": filters.to_date,
			"company": filters.get("company") or "",
			"customer": filters.get("customer") or "",
		},
		as_dict=True,
	)

	for row in rows:
		invoiced = flt(row.get("invoiced_amount"))
		outstanding = flt(row.get("outstanding_amount"))
		collected = max(invoiced - outstanding, 0)
		row["invoiced_amount"] = invoiced
		row["outstanding_amount"] = outstanding
		row["collected_amount"] = collected
		row["collection_pct"] = (collected / invoiced * 100.0) if invoiced else 0.0
		row["invoice_count"] = cint(row.get("invoice_count"))

	return rows


def get_chart(data):
	if not data:
		return None

	top = data[:8]
	return {
		"data": {
			"labels": [r["customer"] for r in top],
			"datasets": [
				{"name": _("Invoiced"), "values": [flt(r["invoiced_amount"]) for r in top]},
				{"name": _("Collected"), "values": [flt(r["collected_amount"]) for r in top]},
			],
		},
		"type": "bar",
		"colors": ["#0ea5e9", "#16a34a"],
	}


def get_summary(data):
	total_invoiced = sum(flt(r.get("invoiced_amount")) for r in data)
	total_outstanding = sum(flt(r.get("outstanding_amount")) for r in data)
	total_collected = sum(flt(r.get("collected_amount")) for r in data)
	total_invoices = sum(cint(r.get("invoice_count")) for r in data)

	return [
		{"label": _("Customers"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Invoices"), "value": total_invoices, "datatype": "Int", "indicator": "Blue"},
		{"label": _("Invoiced"), "value": total_invoiced, "datatype": "Currency", "indicator": "Green"},
		{"label": _("Collected"), "value": total_collected, "datatype": "Currency", "indicator": "Green"},
		{"label": _("Outstanding"), "value": total_outstanding, "datatype": "Currency", "indicator": "Orange"},
	]
