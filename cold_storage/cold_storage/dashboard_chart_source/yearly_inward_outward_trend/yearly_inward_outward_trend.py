import frappe
from frappe import _
from frappe.utils import cint, flt, getdate
from frappe.utils.dashboard import cache_source
from datetime import date


def _normalize_filters(filters):
	"""Support both dict filters and legacy list-based filters."""
	if isinstance(filters, dict):
		return filters

	normalized = {}
	if not isinstance(filters, (list, tuple)):
		return normalized

	for entry in filters:
		if isinstance(entry, dict):
			fieldname = entry.get("fieldname")
			value = entry.get("value")
			if fieldname and value is not None:
				normalized[fieldname] = value
			continue

		if not isinstance(entry, (list, tuple)):
			continue

		fieldname = None
		value = None

		# Typical Frappe filter row: [doctype, fieldname, operator, value, ...]
		if len(entry) >= 4:
			fieldname = entry[1]
			value = entry[3]
		# Fallback pair format: [fieldname, value]
		elif len(entry) >= 2:
			fieldname = entry[0]
			value = entry[1]

		if fieldname and value is not None:
			normalized[fieldname] = value

	return normalized


@frappe.whitelist()
@cache_source
def get(
	chart_name=None,
	chart=None,
	no_cache=None,
	filters=None,
	from_date=None,
	to_date=None,
	timespan=None,
	time_interval=None,
	heatmap_year=None,
):
	del chart_name, chart, no_cache, from_date, to_date, timespan, time_interval, heatmap_year

	filters = _normalize_filters(frappe.parse_json(filters) or {})
	from_year = cint(filters.get("from_year"))
	to_year = cint(filters.get("to_year"))
	company = filters.get("company") or ""
	if from_year and to_year and from_year > to_year:
		from_year, to_year = to_year, from_year

	rows = frappe.db.sql(
		"""
		select
			monthly.year_num as year_num,
			monthly.month_num as month_num,
			sum(monthly.inward_qty) as inward_qty,
			sum(monthly.outward_qty) as outward_qty
		from (
			select
				year(ci.posting_date) as year_num,
				month(ci.posting_date) as month_num,
				sum(ci.total_qty) as inward_qty,
				0 as outward_qty
			from `tabCold Storage Inward` ci
			where ci.docstatus = 1
				and ci.posting_date is not null
				and (%(company)s = '' or ci.company = %(company)s)
				and (%(from_year)s = 0 or year(ci.posting_date) >= %(from_year)s)
				and (%(to_year)s = 0 or year(ci.posting_date) <= %(to_year)s)
			group by year(ci.posting_date), month(ci.posting_date)

			union all

			select
				year(co.posting_date) as year_num,
				month(co.posting_date) as month_num,
				0 as inward_qty,
				sum(co.total_qty) as outward_qty
			from `tabCold Storage Outward` co
			where co.docstatus = 1
				and co.posting_date is not null
				and (%(company)s = '' or co.company = %(company)s)
				and (%(from_year)s = 0 or year(co.posting_date) >= %(from_year)s)
				and (%(to_year)s = 0 or year(co.posting_date) <= %(to_year)s)
			group by year(co.posting_date), month(co.posting_date)
		) monthly
		group by monthly.year_num, monthly.month_num
		order by monthly.year_num, monthly.month_num
		""",
		{
			"company": company,
			"from_year": from_year,
			"to_year": to_year,
		},
		as_dict=True,
	)

	if from_year and not to_year:
		to_year = from_year
	elif to_year and not from_year:
		from_year = to_year

	if not from_year and not to_year:
		years_in_data = [cint(row.year_num) for row in rows if row.year_num is not None]
		if years_in_data:
			from_year = min(years_in_data)
			to_year = max(years_in_data)
		else:
			current_year = getdate().year
			from_year = current_year
			to_year = current_year

	monthly_totals = {}
	for row in rows:
		year = cint(row.year_num)
		month = cint(row.month_num)
		if not year or not month:
			continue
		monthly_totals[(year, month)] = {
			"inward_qty": flt(row.inward_qty),
			"outward_qty": flt(row.outward_qty),
		}

	labels = []
	inward_values = []
	outward_values = []
	current = date(from_year, 1, 1)
	end = date(to_year, 12, 1)
	while current <= end:
		key = (current.year, current.month)
		labels.append(current.strftime("%b %Y"))
		inward_values.append(flt(monthly_totals.get(key, {}).get("inward_qty", 0)))
		outward_values.append(flt(monthly_totals.get(key, {}).get("outward_qty", 0)))
		if current.month == 12:
			current = date(current.year + 1, 1, 1)
		else:
			current = date(current.year, current.month + 1, 1)

	return {
		"labels": labels,
		"datasets": [
			{"name": _("Inward Qty"), "values": inward_values},
			{"name": _("Outward Qty"), "values": outward_values},
		],
		"type": "line",
	}
