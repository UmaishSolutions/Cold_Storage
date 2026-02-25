from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, nowdate

ROW_LIMIT = 1000


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("from_date"):
		filters.from_date = add_days(nowdate(), -30)
	if not filters.get("to_date"):
		filters.to_date = nowdate()

	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Login Time"),
			"fieldname": "login_time",
			"fieldtype": "Datetime",
			"width": 170,
		},
		{
			"label": _("User"),
			"fieldname": "user",
			"fieldtype": "Link",
			"options": "User",
			"width": 210,
		},
		{
			"label": _("Full Name"),
			"fieldname": "full_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("IP Address"),
			"fieldname": "ip_address",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Subject"),
			"fieldname": "subject",
			"fieldtype": "Data",
			"width": 320,
		},
	]


def get_data(filters):
	conditions = ["operation = 'Login'"]
	params = {"row_limit": ROW_LIMIT}

	if filters.get("from_date"):
		conditions.append("coalesce(communication_date, creation) >= %(from_datetime)s")
		params["from_datetime"] = f"{filters.from_date} 00:00:00"

	if filters.get("to_date"):
		conditions.append("coalesce(communication_date, creation) <= %(to_datetime)s")
		params["to_datetime"] = f"{filters.to_date} 23:59:59"

	if filters.get("user"):
		conditions.append("`user` = %(user)s")
		params["user"] = filters.user

	if filters.get("status"):
		conditions.append("status = %(status)s")
		params["status"] = filters.status

	return frappe.db.sql(
		f"""
		select
			coalesce(communication_date, creation) as login_time,
			`user`,
			full_name,
			status,
			ip_address,
			subject
		from `tabActivity Log`
		where {" and ".join(conditions)}
		order by login_time desc, creation desc
		limit %(row_limit)s
		""",
		params,
		as_dict=True,
	)
