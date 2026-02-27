import frappe
from frappe import _
from frappe.utils import flt, nowdate


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
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 220},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 220},
		{"label": _("Inward Qty"), "fieldname": "inward_qty", "fieldtype": "Float", "width": 130},
		{"label": _("Outward Qty"), "fieldname": "outward_qty", "fieldtype": "Float", "width": 130},
		{"label": _("Transfer Qty"), "fieldname": "transfer_qty", "fieldtype": "Float", "width": 130},
		{"label": _("Net Qty"), "fieldname": "net_qty", "fieldtype": "Float", "width": 120},
	]


def get_data(filters):
	params = {
		"from_date": filters.from_date,
		"to_date": filters.to_date,
		"company": filters.get("company") or "",
		"item": filters.get("item") or "",
	}

	rows = frappe.db.sql(
		"""
		select
			t.item_code,
			ifnull(i.item_name, t.item_code) as item_name,
			sum(t.inward_qty) as inward_qty,
			sum(t.outward_qty) as outward_qty,
			sum(t.transfer_qty) as transfer_qty
		from (
			select ci.item as item_code, sum(ci.qty) as inward_qty, 0 as outward_qty, 0 as transfer_qty
			from `tabCold Storage Inward` p
			inner join `tabCold Storage Inward Item` ci on ci.parent = p.name
			where p.docstatus = 1
				and p.posting_date between %(from_date)s and %(to_date)s
				and (%(company)s = '' or p.company = %(company)s)
				and (%(item)s = '' or ci.item = %(item)s)
			group by ci.item

			union all

			select co.item as item_code, 0 as inward_qty, sum(co.qty) as outward_qty, 0 as transfer_qty
			from `tabCold Storage Outward` p
			inner join `tabCold Storage Outward Item` co on co.parent = p.name
			where p.docstatus = 1
				and p.posting_date between %(from_date)s and %(to_date)s
				and (%(company)s = '' or p.company = %(company)s)
				and (%(item)s = '' or co.item = %(item)s)
			group by co.item

			union all

			select ct.item as item_code, 0 as inward_qty, 0 as outward_qty, sum(ct.qty) as transfer_qty
			from `tabCold Storage Transfer` p
			inner join `tabCold Storage Transfer Item` ct on ct.parent = p.name
			where p.docstatus = 1
				and p.posting_date between %(from_date)s and %(to_date)s
				and (%(company)s = '' or p.company = %(company)s)
				and (%(item)s = '' or ct.item = %(item)s)
			group by ct.item
		) t
		left join `tabItem` i on i.name = t.item_code
		group by t.item_code, i.item_name
		order by sum(t.inward_qty - t.outward_qty) desc, t.item_code asc
		""",
		params,
		as_dict=True,
	)

	for row in rows:
		row["inward_qty"] = flt(row.get("inward_qty"))
		row["outward_qty"] = flt(row.get("outward_qty"))
		row["transfer_qty"] = flt(row.get("transfer_qty"))
		row["net_qty"] = row["inward_qty"] - row["outward_qty"]

	return rows


def get_chart(data):
	if not data:
		return None
	rows = sorted(data, key=lambda d: flt(d.get("inward_qty")), reverse=True)[:8]
	return {
		"data": {
			"labels": [r.get("item_code") for r in rows],
			"datasets": [
				{"name": _("Inward"), "values": [flt(r.get("inward_qty")) for r in rows]},
				{"name": _("Outward"), "values": [flt(r.get("outward_qty")) for r in rows]},
			],
		},
		"type": "bar",
		"colors": ["#16a34a", "#ef4444"],
	}


def get_summary(data):
	total_inward = sum(flt(r.get("inward_qty")) for r in data)
	total_outward = sum(flt(r.get("outward_qty")) for r in data)
	total_transfer = sum(flt(r.get("transfer_qty")) for r in data)
	return [
		{"label": _("Items"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Inward Qty"), "value": total_inward, "datatype": "Float", "indicator": "Green"},
		{"label": _("Outward Qty"), "value": total_outward, "datatype": "Float", "indicator": "Red"},
		{"label": _("Transfer Qty"), "value": total_transfer, "datatype": "Float", "indicator": "Orange"},
	]
