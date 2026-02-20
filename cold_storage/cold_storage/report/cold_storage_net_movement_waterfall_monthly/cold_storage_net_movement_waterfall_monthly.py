from datetime import date

import frappe
from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
	get_default_company,
)
from frappe import _
from frappe.utils import flt, getdate, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	set_default_filters(filters)
	validate_filters(filters)
	filters.company = get_report_company(filters)

	columns = get_columns()
	months = get_months(filters.from_date, filters.to_date)
	if not months:
		return columns, [], _("No data for selected period."), None, []

	opening_net_movement = get_opening_net_movement(filters, months[0])
	monthly_movement_map = get_monthly_movement_map(filters)
	data = build_data(months, monthly_movement_map, opening_net_movement)
	chart = get_chart_data(data)
	report_summary = get_report_summary(data, opening_net_movement)

	return columns, data, None, chart, report_summary


def set_default_filters(filters):
	if not filters.get("to_date"):
		filters.to_date = nowdate()
	if not filters.get("from_date"):
		to_date = getdate(filters.to_date)
		start_year = to_date.year
		start_month = to_date.month - 11
		while start_month <= 0:
			start_month += 12
			start_year -= 1
		filters.from_date = date(start_year, start_month, 1)


def validate_filters(filters):
	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be greater than To Date"))


def get_report_company(filters):
	"""Always scope report to Cold Storage Settings company when available."""
	try:
		company = get_default_company()
	except Exception:
		company = None
	return company or filters.get("company")


def get_columns():
	return [
		{
			"label": _("Month"),
			"fieldname": "month_label",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Inward Qty"),
			"fieldname": "inward_qty",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"label": _("Outward Qty"),
			"fieldname": "outward_qty",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"label": _("Net Movement Qty"),
			"fieldname": "net_movement_qty",
			"fieldtype": "Float",
			"width": 150,
		},
		{
			"label": _("Net Closing Movement"),
			"fieldname": "net_closing_movement_qty",
			"fieldtype": "Float",
			"width": 170,
		},
	]


def get_months(from_date, to_date):
	start = getdate(from_date).replace(day=1)
	end = getdate(to_date).replace(day=1)
	months = []
	current = start
	while current <= end:
		months.append(current)
		if current.month == 12:
			current = date(current.year + 1, 1, 1)
		else:
			current = date(current.year, current.month + 1, 1)
	return months


def get_opening_net_movement(filters, first_month_start):
	params = {
		"first_month_start": first_month_start,
		"company": filters.get("company") or "",
		"customer": filters.get("customer") or "",
		"item": filters.get("item") or "",
		"warehouse": filters.get("warehouse") or "",
	}

	inward_qty = flt(
		frappe.db.sql(
			"""
			select sum(cii.qty)
			from `tabCold Storage Inward` ci
			inner join `tabCold Storage Inward Item` cii
				on cii.parent = ci.name
				and cii.parenttype = 'Cold Storage Inward'
			where ci.docstatus = 1
				and ci.posting_date is not null
				and ci.posting_date < %(first_month_start)s
				and (%(company)s = '' or ci.company = %(company)s)
				and (%(customer)s = '' or ci.customer = %(customer)s)
				and (%(item)s = '' or cii.item = %(item)s)
				and (%(warehouse)s = '' or cii.warehouse = %(warehouse)s)
			""",
			params,
		)[0][0]
	)

	outward_qty = flt(
		frappe.db.sql(
			"""
			select sum(coi.qty)
			from `tabCold Storage Outward` co
			inner join `tabCold Storage Outward Item` coi
				on coi.parent = co.name
				and coi.parenttype = 'Cold Storage Outward'
			where co.docstatus = 1
				and co.posting_date is not null
				and co.posting_date < %(first_month_start)s
				and (%(company)s = '' or co.company = %(company)s)
				and (%(customer)s = '' or co.customer = %(customer)s)
				and (%(item)s = '' or coi.item = %(item)s)
				and (%(warehouse)s = '' or coi.warehouse = %(warehouse)s)
			""",
			params,
		)[0][0]
	)

	return inward_qty - outward_qty


def get_monthly_movement_map(filters):
	rows = frappe.db.sql(
		"""
		select
			movement.year_num,
			movement.month_num,
			sum(movement.inward_qty) as inward_qty,
			sum(movement.outward_qty) as outward_qty
		from (
			select
				year(ci.posting_date) as year_num,
				month(ci.posting_date) as month_num,
				sum(cii.qty) as inward_qty,
				0 as outward_qty
			from `tabCold Storage Inward` ci
			inner join `tabCold Storage Inward Item` cii
				on cii.parent = ci.name
				and cii.parenttype = 'Cold Storage Inward'
			where ci.docstatus = 1
				and ci.posting_date is not null
				and ci.posting_date >= %(from_date)s
				and ci.posting_date <= %(to_date)s
				and (%(company)s = '' or ci.company = %(company)s)
				and (%(customer)s = '' or ci.customer = %(customer)s)
				and (%(item)s = '' or cii.item = %(item)s)
				and (%(warehouse)s = '' or cii.warehouse = %(warehouse)s)
			group by year(ci.posting_date), month(ci.posting_date)

			union all

			select
				year(co.posting_date) as year_num,
				month(co.posting_date) as month_num,
				0 as inward_qty,
				sum(coi.qty) as outward_qty
			from `tabCold Storage Outward` co
			inner join `tabCold Storage Outward Item` coi
				on coi.parent = co.name
				and coi.parenttype = 'Cold Storage Outward'
			where co.docstatus = 1
				and co.posting_date is not null
				and co.posting_date >= %(from_date)s
				and co.posting_date <= %(to_date)s
				and (%(company)s = '' or co.company = %(company)s)
				and (%(customer)s = '' or co.customer = %(customer)s)
				and (%(item)s = '' or coi.item = %(item)s)
				and (%(warehouse)s = '' or coi.warehouse = %(warehouse)s)
			group by year(co.posting_date), month(co.posting_date)
		) movement
		group by movement.year_num, movement.month_num
		order by movement.year_num, movement.month_num
		""",
		{
			"from_date": filters.from_date,
			"to_date": filters.to_date,
			"company": filters.get("company") or "",
			"customer": filters.get("customer") or "",
			"item": filters.get("item") or "",
			"warehouse": filters.get("warehouse") or "",
		},
		as_dict=True,
	)

	return {
		(cint_or_zero(row.year_num), cint_or_zero(row.month_num)): {
			"inward_qty": flt(row.inward_qty),
			"outward_qty": flt(row.outward_qty),
		}
		for row in rows
	}


def cint_or_zero(value):
	try:
		return int(value or 0)
	except Exception:
		return 0


def build_data(months, monthly_movement_map, opening_net_movement):
	rows = []
	running_closing = flt(opening_net_movement)

	for month_start in months:
		movement = monthly_movement_map.get((month_start.year, month_start.month), {})
		inward_qty = flt(movement.get("inward_qty"))
		outward_qty = flt(movement.get("outward_qty"))
		net_movement_qty = inward_qty - outward_qty
		running_closing += net_movement_qty

		rows.append(
			{
				"month_label": month_start.strftime("%b %Y"),
				"inward_qty": inward_qty,
				"outward_qty": outward_qty,
				"net_movement_qty": net_movement_qty,
				"net_closing_movement_qty": running_closing,
			}
		)

	return rows


def get_chart_data(data):
	if not data:
		return None

	labels = [row.get("month_label") for row in data]
	inward_values = [flt(row.get("inward_qty")) for row in data]
	outward_values = [-flt(row.get("outward_qty")) for row in data]
	net_closing_values = [flt(row.get("net_closing_movement_qty")) for row in data]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Inward Qty"), "chartType": "bar", "values": inward_values},
				{"name": _("Outward Qty"), "chartType": "bar", "values": outward_values},
				{
					"name": _("Net Closing Movement"),
					"chartType": "line",
					"values": net_closing_values,
				},
			],
		},
		"type": "axis-mixed",
		"colors": ["#16a34a", "#dc2626", "#0284c7"],
	}


def get_report_summary(data, opening_net_movement):
	total_inward = sum(flt(row.get("inward_qty")) for row in data)
	total_outward = sum(flt(row.get("outward_qty")) for row in data)
	net_movement = total_inward - total_outward
	closing_movement = flt(data[-1].get("net_closing_movement_qty")) if data else flt(opening_net_movement)

	return [
		{
			"value": flt(opening_net_movement),
			"label": _("Opening Net Movement"),
			"datatype": "Float",
			"indicator": "Blue",
		},
		{
			"value": total_inward,
			"label": _("Total Inward Qty"),
			"datatype": "Float",
			"indicator": "Green",
		},
		{
			"value": total_outward,
			"label": _("Total Outward Qty"),
			"datatype": "Float",
			"indicator": "Red",
		},
		{
			"value": net_movement,
			"label": _("Net Movement Qty"),
			"datatype": "Float",
			"indicator": "Orange",
		},
		{
			"value": closing_movement,
			"label": _("Net Closing Movement"),
			"datatype": "Float",
			"indicator": "Purple",
		},
	]
