from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, nowdate

from cold_storage.client_portal_views import CLIENT_PORTAL_VIEW_PATH_FILTER

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
			"label": _("Access Time"),
			"fieldname": "access_time",
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
			"label": _("Source"),
			"fieldname": "source",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Path"),
			"fieldname": "path",
			"fieldtype": "Data",
			"width": 190,
		},
		{
			"label": _("Referrer"),
			"fieldname": "referrer",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": _("User Agent"),
			"fieldname": "user_agent",
			"fieldtype": "Data",
			"width": 320,
		},
	]


def get_data(filters):
	conditions = ["path like %(path_like)s"]
	params = {
		"path_like": CLIENT_PORTAL_VIEW_PATH_FILTER,
		"row_limit": ROW_LIMIT,
	}

	if filters.get("from_date"):
		conditions.append("creation >= %(from_datetime)s")
		params["from_datetime"] = f"{filters.from_date} 00:00:00"

	if filters.get("to_date"):
		conditions.append("creation <= %(to_datetime)s")
		params["to_datetime"] = f"{filters.to_date} 23:59:59"

	if filters.get("user"):
		conditions.append("owner = %(user)s")
		params["user"] = filters.user

	if filters.get("source"):
		conditions.append("source = %(source)s")
		params["source"] = filters.source

	return frappe.db.sql(
		f"""
		select
			creation as access_time,
			owner as `user`,
			source,
			path,
			referrer,
			user_agent
		from `tabWeb Page View`
		where {" and ".join(conditions)}
		order by creation desc
		limit %(row_limit)s
		""",
		params,
		as_dict=True,
	)
