import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.as_on_date = filters.get("as_on_date") or nowdate()

	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = get_summary(data)
	return columns, data, None, chart, summary


def get_columns():
	return [
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 240},
		{"label": _("Invoices"), "fieldname": "invoice_count", "fieldtype": "Int", "width": 90},
		{"label": _("Total Outstanding"), "fieldname": "total_outstanding", "fieldtype": "Currency", "width": 160},
		{"label": _("Current"), "fieldname": "bucket_current", "fieldtype": "Currency", "width": 130},
		{"label": _("1-30 Days"), "fieldname": "bucket_1_30", "fieldtype": "Currency", "width": 130},
		{"label": _("31-60 Days"), "fieldname": "bucket_31_60", "fieldtype": "Currency", "width": 130},
		{"label": _("61-90 Days"), "fieldname": "bucket_61_90", "fieldtype": "Currency", "width": 130},
		{"label": _("90+ Days"), "fieldname": "bucket_90_plus", "fieldtype": "Currency", "width": 130},
	]


def get_data(filters):
	rows = frappe.db.sql(
		"""
		select
			customer,
			name,
			ifnull(due_date, posting_date) as due_date,
			outstanding_amount
		from `tabSales Invoice`
		where docstatus = 1
			and outstanding_amount > 0
			and posting_date <= %(as_on_date)s
			and (%(company)s = '' or company = %(company)s)
			and (%(customer)s = '' or customer = %(customer)s)
		""",
		{
			"as_on_date": filters.as_on_date,
			"company": filters.get("company") or "",
			"customer": filters.get("customer") or "",
		},
		as_dict=True,
	)

	customer_map = {}
	for row in rows:
		customer = row.get("customer")
		if customer not in customer_map:
			customer_map[customer] = {
				"customer": customer,
				"invoice_count": 0,
				"total_outstanding": 0.0,
				"bucket_current": 0.0,
				"bucket_1_30": 0.0,
				"bucket_31_60": 0.0,
				"bucket_61_90": 0.0,
				"bucket_90_plus": 0.0,
			}

		age_days = cint(frappe.utils.date_diff(filters.as_on_date, row.get("due_date")))
		amount = flt(row.get("outstanding_amount"))
		rec = customer_map[customer]
		rec["invoice_count"] += 1
		rec["total_outstanding"] += amount

		if age_days <= 0:
			rec["bucket_current"] += amount
		elif age_days <= 30:
			rec["bucket_1_30"] += amount
		elif age_days <= 60:
			rec["bucket_31_60"] += amount
		elif age_days <= 90:
			rec["bucket_61_90"] += amount
		else:
			rec["bucket_90_plus"] += amount

	return sorted(customer_map.values(), key=lambda d: d.get("total_outstanding", 0), reverse=True)


def get_chart(data):
	if not data:
		return None

	top = data[:8]
	return {
		"data": {
			"labels": [r["customer"] for r in top],
			"datasets": [{"name": _("Outstanding"), "values": [flt(r["total_outstanding"]) for r in top]}],
		},
		"type": "bar",
		"colors": ["#ef4444"],
	}


def get_summary(data):
	total_outstanding = sum(flt(r.get("total_outstanding")) for r in data)
	total_invoices = sum(cint(r.get("invoice_count")) for r in data)
	return [
		{"label": _("Customers"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Outstanding Invoices"), "value": total_invoices, "datatype": "Int", "indicator": "Orange"},
		{"label": _("Total Outstanding"), "value": total_outstanding, "datatype": "Currency", "indicator": "Red"},
	]
