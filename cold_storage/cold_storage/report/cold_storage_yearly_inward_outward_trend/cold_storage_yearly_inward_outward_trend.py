import frappe
from frappe import _
from frappe.utils import cint, flt, getdate
from datetime import date


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	columns = get_columns()
	data, months, item_groups = get_data(filters)
	chart = get_chart_data(data, months, item_groups)
	report_summary = get_report_summary(data, months, item_groups)
	return columns, data, None, chart, report_summary


def validate_filters(filters):
	from_year = cint(filters.get("from_year"))
	to_year = cint(filters.get("to_year"))
	if from_year and to_year and from_year > to_year:
		frappe.throw(_("From Year cannot be greater than To Year"))


def get_columns():
	return [
		{
			"label": _("Month"),
			"fieldname": "month_label",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Item Group"),
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 200,
		},
		{
			"label": _("Inward Qty"),
			"fieldname": "inward_qty",
			"fieldtype": "Float",
			"width": 140,
		},
		{
			"label": _("Outward Qty"),
			"fieldname": "outward_qty",
			"fieldtype": "Float",
			"width": 140,
		},
		{
			"label": _("Net Movement"),
			"fieldname": "net_movement_qty",
			"fieldtype": "Float",
			"width": 150,
		},
	]


def get_data(filters):
	raw_rows = frappe.db.sql(
		"""
		select
			monthly.year_num as year_num,
			monthly.month_num as month_num,
			monthly.item_group as item_group,
			sum(monthly.inward_qty) as inward_qty,
			sum(monthly.outward_qty) as outward_qty
		from (
			select
				year(ci.posting_date) as year_num,
				month(ci.posting_date) as month_num,
				cii.item_group as item_group,
				sum(cii.qty) as inward_qty,
				0 as outward_qty
			from `tabCold Storage Inward` ci
			inner join `tabCold Storage Inward Item` cii
				on cii.parent = ci.name
				and cii.parenttype = 'Cold Storage Inward'
			where ci.docstatus = 1
				and ci.posting_date is not null
				and ifnull(cii.item_group, '') != ''
				and (%(company)s = '' or ci.company = %(company)s)
				and (%(from_year)s = 0 or year(ci.posting_date) >= %(from_year)s)
				and (%(to_year)s = 0 or year(ci.posting_date) <= %(to_year)s)
				and (%(item_group)s = '' or cii.item_group = %(item_group)s)
			group by year(ci.posting_date), month(ci.posting_date), cii.item_group

			union all

			select
				year(co.posting_date) as year_num,
				month(co.posting_date) as month_num,
				coi.item_group as item_group,
				0 as inward_qty,
				sum(coi.qty) as outward_qty
			from `tabCold Storage Outward` co
			inner join `tabCold Storage Outward Item` coi
				on coi.parent = co.name
				and coi.parenttype = 'Cold Storage Outward'
			where co.docstatus = 1
				and co.posting_date is not null
				and ifnull(coi.item_group, '') != ''
				and (%(company)s = '' or co.company = %(company)s)
				and (%(from_year)s = 0 or year(co.posting_date) >= %(from_year)s)
				and (%(to_year)s = 0 or year(co.posting_date) <= %(to_year)s)
				and (%(item_group)s = '' or coi.item_group = %(item_group)s)
			group by year(co.posting_date), month(co.posting_date), coi.item_group
		) monthly
		group by monthly.year_num, monthly.month_num, monthly.item_group
		order by monthly.year_num, monthly.month_num, monthly.item_group
		""",
		{
			"company": filters.get("company") or "",
			"from_year": cint(filters.get("from_year")),
			"to_year": cint(filters.get("to_year")),
			"item_group": filters.get("item_group") or "",
		},
		as_dict=True,
	)

	monthly_totals = {}
	for row in raw_rows:
		year = cint(row.year_num)
		month = cint(row.month_num)
		item_group = (row.item_group or "").strip()
		if not year or not month or not item_group:
			continue
		monthly_totals[(year, month, item_group)] = {
			"inward_qty": flt(row.inward_qty),
			"outward_qty": flt(row.outward_qty),
		}

	months = get_months(filters, monthly_totals)
	item_group_filter = (filters.get("item_group") or "").strip()
	if item_group_filter:
		item_groups = [item_group_filter]
	else:
		item_groups = sorted({item_group for (_year, _month, item_group) in monthly_totals.keys()})

	if not item_groups:
		return [], [], []

	rows = []
	for year, month, month_label in months:
		for item_group in item_groups:
			values = monthly_totals.get((year, month, item_group), {})
			inward_qty = flt(values.get("inward_qty", 0))
			outward_qty = flt(values.get("outward_qty", 0))
			rows.append(
				frappe._dict(
					{
						"month_label": month_label,
						"item_group": item_group,
						"inward_qty": inward_qty,
						"outward_qty": outward_qty,
						"net_movement_qty": inward_qty - outward_qty,
					}
				)
			)

	return rows, months, item_groups


def get_months(filters, monthly_totals):
	from_year = cint(filters.get("from_year"))
	to_year = cint(filters.get("to_year"))
	if from_year and not to_year:
		to_year = from_year
	elif to_year and not from_year:
		from_year = to_year

	if not from_year and not to_year:
		years_in_data = sorted({year for (year, _month, _item_group) in monthly_totals.keys()})
		if years_in_data:
			from_year = min(years_in_data)
			to_year = max(years_in_data)
		else:
			current_year = getdate().year
			from_year = current_year - 5
			to_year = current_year

	months = []
	current = date(from_year, 1, 1)
	end = date(to_year, 12, 1)
	while current <= end:
		months.append((current.year, current.month, current.strftime("%b %Y")))
		if current.month == 12:
			current = date(current.year + 1, 1, 1)
		else:
			current = date(current.year, current.month + 1, 1)

	return months


def get_chart_data(data, months, item_groups):
	if not data or not months or not item_groups:
		return None

	by_month_group = {}
	for row in data:
		by_month_group[(row.month_label, row.item_group)] = {
			"inward_qty": flt(row.inward_qty),
			"outward_qty": flt(row.outward_qty),
		}

	single_group = len(item_groups) == 1
	datasets = []
	for item_group in item_groups:
		inward_values = [
			flt(by_month_group.get((label, item_group), {}).get("inward_qty", 0))
			for (_year, _month, label) in months
		]
		outward_values = [
			flt(by_month_group.get((label, item_group), {}).get("outward_qty", 0))
			for (_year, _month, label) in months
		]
		if single_group:
			inward_name = _("Inward Qty")
			outward_name = _("Outward Qty")
		else:
			inward_name = _("{0} - Inward").format(item_group)
			outward_name = _("{0} - Outward").format(item_group)

		datasets.append({"name": inward_name, "values": inward_values})
		datasets.append({"name": outward_name, "values": outward_values})

	return {
		"data": {
			"labels": [label for (_year, _month, label) in months],
			"datasets": datasets,
		},
		"type": "line",
	}


def get_report_summary(data, months, item_groups):
	total_inward = sum(flt(row.inward_qty) for row in data)
	total_outward = sum(flt(row.outward_qty) for row in data)
	total_net = total_inward - total_outward

	return [
		{
			"value": len(months),
			"label": _("Months Covered"),
			"datatype": "Int",
			"indicator": "Blue",
		},
		{
			"value": len(item_groups),
			"label": _("Item Groups Covered"),
			"datatype": "Int",
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
			"value": total_net,
			"label": _("Net Movement"),
			"datatype": "Float",
			"indicator": "Orange" if total_net < 0 else "Green",
		},
	]
