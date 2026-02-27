import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

BUCKETS = [
	("Current", "Current"),
	("1-30", "1-30 Days"),
	("31-60", "31-60 Days"),
	("61-90", "61-90 Days"),
	("90-120", "90-120 Days"),
	("120-150", "120-150 Days"),
	("150-180", "150-180 Days"),
	("180+", "180+ Days"),
]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.from_date = getdate(filters.get("from_date") or nowdate())
	filters.to_date = getdate(filters.get("to_date") or nowdate())

	if filters.from_date > filters.to_date:
		filters.from_date, filters.to_date = filters.to_date, filters.from_date

	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	message = _(
		"Formula applied per bucket: Opening AR + New Bills - Collections = Closing AR. "
		"Collections are payments allocated in selected period."
	)
	summary = get_summary(data)
	return columns, data, message, chart, summary


def get_columns():
	return [
		{"label": _("Aging Bucket"), "fieldname": "aging_bucket", "fieldtype": "Data", "width": 160},
		{"label": _("Opening AR"), "fieldname": "opening_ar", "fieldtype": "Currency", "width": 150},
		{"label": _("New Bills"), "fieldname": "new_bills", "fieldtype": "Currency", "width": 150},
		{"label": _("Collections"), "fieldname": "collections", "fieldtype": "Currency", "width": 150},
		{"label": _("Closing AR"), "fieldname": "closing_ar", "fieldtype": "Currency", "width": 150},
		{"label": _("Closing Actual"), "fieldname": "closing_actual", "fieldtype": "Currency", "width": 160},
		{"label": _("Variance"), "fieldname": "variance", "fieldtype": "Currency", "width": 130},
	]


def get_bucket_key(as_on_date, due_date):
	age_days = cint(frappe.utils.date_diff(as_on_date, due_date))
	if age_days <= 0:
		return "Current"
	if age_days <= 30:
		return "1-30"
	if age_days <= 60:
		return "31-60"
	if age_days <= 90:
		return "61-90"
	if age_days <= 120:
		return "90-120"
	if age_days <= 150:
		return "120-150"
	if age_days <= 180:
		return "150-180"
	return "180+"


def get_data(filters):
	invoice_rows = frappe.db.sql(
		"""
		select
			si.name,
			si.customer,
			si.posting_date,
			ifnull(si.due_date, si.posting_date) as due_date,
			si.grand_total,
			si.outstanding_amount
		from `tabSales Invoice` si
		where si.docstatus = 1
			and si.posting_date <= %(to_date)s
			and (%(company)s = '' or si.company = %(company)s)
			and (%(customer)s = '' or si.customer = %(customer)s)
		""",
		{
			"to_date": filters.to_date,
			"company": filters.get("company") or "",
			"customer": filters.get("customer") or "",
		},
		as_dict=True,
	)

	collections_map = {
		row.reference_name: flt(row.collected_amount)
		for row in frappe.db.sql(
			"""
			select
				per.reference_name,
				sum(per.allocated_amount) as collected_amount
			from `tabPayment Entry Reference` per
			inner join `tabPayment Entry` pe on pe.name = per.parent
			where pe.docstatus = 1
				and per.reference_doctype = 'Sales Invoice'
				and pe.posting_date between %(from_date)s and %(to_date)s
			group by per.reference_name
			""",
			{"from_date": filters.from_date, "to_date": filters.to_date},
			as_dict=True,
		)
	}

	bucket_map = {
		key: {
			"aging_bucket": label,
			"opening_ar": 0.0,
			"new_bills": 0.0,
			"collections": 0.0,
			"closing_ar": 0.0,
			"closing_actual": 0.0,
			"variance": 0.0,
		}
		for key, label in BUCKETS
	}

	for row in invoice_rows:
		bucket = get_bucket_key(filters.to_date, row.get("due_date"))
		rec = bucket_map[bucket]
		collected_in_period = flt(collections_map.get(row.get("name"), 0.0))
		outstanding_now = flt(row.get("outstanding_amount"))
		grand_total = flt(row.get("grand_total"))

		rec["collections"] += collected_in_period
		rec["closing_actual"] += outstanding_now

		if row.get("posting_date") < filters.from_date:
			rec["opening_ar"] += outstanding_now + collected_in_period
		elif row.get("posting_date") <= filters.to_date:
			rec["new_bills"] += grand_total

	for key, _bucket_label in BUCKETS:
		rec = bucket_map[key]
		rec["closing_ar"] = rec["opening_ar"] + rec["new_bills"] - rec["collections"]
		rec["variance"] = rec["closing_actual"] - rec["closing_ar"]

	return [bucket_map[key] for key, _bucket_label in BUCKETS]


def get_chart(data):
	labels = [row["aging_bucket"] for row in data]
	opening = [flt(row["opening_ar"]) for row in data]
	new_bills = [flt(row["new_bills"]) for row in data]
	collections = [flt(row["collections"]) * -1 for row in data]
	closing = [flt(row["closing_ar"]) for row in data]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Opening AR"), "chartType": "bar", "values": opening},
				{"name": _("New Bills"), "chartType": "bar", "values": new_bills},
				{"name": _("Collections (-)"), "chartType": "bar", "values": collections},
				{"name": _("Closing AR"), "chartType": "line", "values": closing},
			],
		},
		"type": "axis-mixed",
		"colors": ["#2563eb", "#16a34a", "#ef4444", "#9333ea"],
	}


def get_summary(data):
	total_opening = sum(flt(row.get("opening_ar")) for row in data)
	total_new = sum(flt(row.get("new_bills")) for row in data)
	total_collections = sum(flt(row.get("collections")) for row in data)
	total_closing = sum(flt(row.get("closing_ar")) for row in data)
	total_variance = sum(flt(row.get("variance")) for row in data)

	return [
		{"label": _("Opening AR"), "value": total_opening, "datatype": "Currency", "indicator": "Blue"},
		{"label": _("New Bills"), "value": total_new, "datatype": "Currency", "indicator": "Green"},
		{"label": _("Collections"), "value": total_collections, "datatype": "Currency", "indicator": "Red"},
		{"label": _("Closing AR"), "value": total_closing, "datatype": "Currency", "indicator": "Orange"},
		{"label": _("Variance"), "value": total_variance, "datatype": "Currency", "indicator": "Purple"},
	]
