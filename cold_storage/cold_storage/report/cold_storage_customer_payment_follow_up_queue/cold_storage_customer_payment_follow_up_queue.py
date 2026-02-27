import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate


PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.as_on_date = filters.get("as_on_date") or nowdate()
	filters.min_overdue_days = max(cint(filters.get("min_overdue_days") or 0), 0)
	filters.limit_rows = max(cint(filters.get("limit_rows") or 500), 1)

	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = get_summary(data)
	return columns, data, None, chart, summary


def get_columns():
	return [
		{"label": _("Priority"), "fieldname": "priority", "fieldtype": "Data", "width": 100},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 220},
		{"label": _("Invoice"), "fieldname": "invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 170},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Days Overdue"), "fieldname": "days_overdue", "fieldtype": "Int", "width": 110},
		{"label": _("Outstanding Amount"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 145},
		{"label": _("Mobile"), "fieldname": "mobile_no", "fieldtype": "Data", "width": 130},
		{"label": _("Email"), "fieldname": "email_id", "fieldtype": "Data", "width": 190},
		{"label": _("Next Action"), "fieldname": "next_action", "fieldtype": "Data", "width": 260},
		{"label": _("Queue Score"), "fieldname": "queue_score", "fieldtype": "Float", "precision": 2, "width": 120},
	]


def get_data(filters):
	rows = frappe.db.sql(
		"""
		select
			si.customer,
			si.name as invoice,
			ifnull(si.due_date, si.posting_date) as due_date,
			si.outstanding_amount,
			ifnull(c.mobile_no, '') as mobile_no,
			ifnull(c.email_id, '') as email_id
		from `tabSales Invoice` si
		left join `tabCustomer` c on c.name = si.customer
		where si.docstatus = 1
			and si.outstanding_amount > 0
			and si.posting_date <= %(as_on_date)s
			and (%(company)s = '' or si.company = %(company)s)
			and (%(customer)s = '' or si.customer = %(customer)s)
		""",
		{
			"as_on_date": filters.as_on_date,
			"company": filters.get("company") or "",
			"customer": filters.get("customer") or "",
		},
		as_dict=True,
	)

	data = []
	for row in rows:
		days_overdue = max(cint(frappe.utils.date_diff(filters.as_on_date, row.get("due_date"))), 0)
		if days_overdue < filters.min_overdue_days:
			continue

		outstanding_amount = flt(row.get("outstanding_amount"))
		priority = get_priority(days_overdue, outstanding_amount)
		queue_score = get_queue_score(days_overdue, outstanding_amount)

		data.append(
			{
				"priority": priority,
				"priority_rank": PRIORITY_ORDER.get(priority, 99),
				"customer": row.get("customer"),
				"invoice": row.get("invoice"),
				"due_date": row.get("due_date"),
				"days_overdue": days_overdue,
				"outstanding_amount": outstanding_amount,
				"mobile_no": row.get("mobile_no"),
				"email_id": row.get("email_id"),
				"next_action": get_next_action(priority, days_overdue),
				"queue_score": queue_score,
			}
		)

	data.sort(key=lambda d: (d.get("priority_rank", 99), -flt(d.get("queue_score")), d.get("customer") or ""))
	for row in data:
		row.pop("priority_rank", None)

	return data[: filters.limit_rows]


def get_priority(days_overdue, outstanding_amount):
	if days_overdue >= 60 or outstanding_amount >= 500000:
		return "Critical"
	if days_overdue >= 30 or outstanding_amount >= 200000:
		return "High"
	if days_overdue >= 7 or outstanding_amount >= 50000:
		return "Medium"
	return "Low"


def get_queue_score(days_overdue, outstanding_amount):
	return flt(outstanding_amount) * (1 + flt(days_overdue) / 30.0)


def get_next_action(priority, days_overdue):
	if priority == "Critical":
		return _("Immediate escalation call and payment commitment today.")
	if priority == "High":
		return _("Follow up by call and share statement/invoice copy.")
	if priority == "Medium":
		return _("Send reminder on WhatsApp/email and schedule follow-up.")
	if days_overdue > 0:
		return _("Soft reminder with due date confirmation.")
	return _("Upcoming due: schedule proactive reminder.")


def get_chart(data):
	if not data:
		return None

	by_customer = {}
	for row in data:
		by_customer[row["customer"]] = by_customer.get(row["customer"], 0.0) + flt(row["outstanding_amount"])

	top = sorted(by_customer.items(), key=lambda d: d[1], reverse=True)[:8]
	if not top:
		return None

	return {
		"data": {
			"labels": [d[0] for d in top],
			"datasets": [{"name": _("Outstanding"), "values": [flt(d[1]) for d in top]}],
		},
		"type": "bar",
		"colors": ["#ef4444"],
	}


def get_summary(data):
	total_outstanding = sum(flt(r.get("outstanding_amount")) for r in data)
	critical = sum(1 for r in data if r.get("priority") == "Critical")
	high = sum(1 for r in data if r.get("priority") == "High")
	medium = sum(1 for r in data if r.get("priority") == "Medium")

	return [
		{"label": _("Queue Entries"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Critical"), "value": critical, "datatype": "Int", "indicator": "Red"},
		{"label": _("High"), "value": high, "datatype": "Int", "indicator": "Orange"},
		{"label": _("Medium"), "value": medium, "datatype": "Int", "indicator": "Yellow"},
		{"label": _("Outstanding in Queue"), "value": total_outstanding, "datatype": "Currency", "indicator": "Red"},
	]
