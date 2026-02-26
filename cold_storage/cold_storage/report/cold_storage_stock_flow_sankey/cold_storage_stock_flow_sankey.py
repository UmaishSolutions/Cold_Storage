import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.from_date = filters.get("from_date") or nowdate()
	filters.to_date = filters.get("to_date") or nowdate()
	filters.top_n_groups = max(cint(filters.get("top_n_groups") or 8), 1)

	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data, filters)
	message = _("Includes Sankey payload in chart metadata for flow-path analysis by item group.")
	summary = get_summary(data)
	return columns, data, message, chart, summary


def get_columns():
	return [
		{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 220},
		{"label": _("Inward Qty"), "fieldname": "inward_qty", "fieldtype": "Float", "width": 130},
		{"label": _("Transfer Qty"), "fieldname": "transfer_qty", "fieldtype": "Float", "width": 130},
		{"label": _("Outward Qty"), "fieldname": "outward_qty", "fieldtype": "Float", "width": 130},
		{"label": _("Flow Imbalance"), "fieldname": "flow_imbalance", "fieldtype": "Float", "width": 130},
		{"label": _("Transfer Load %"), "fieldname": "transfer_load_pct", "fieldtype": "Percent", "width": 130},
		{"label": _("Dispatch Ratio %"), "fieldname": "dispatch_ratio_pct", "fieldtype": "Percent", "width": 130},
		{"label": _("Bottleneck Score"), "fieldname": "bottleneck_score", "fieldtype": "Float", "precision": 2, "width": 140},
	]


def get_data(filters):
	params = {
		"from_date": filters.from_date,
		"to_date": filters.to_date,
		"company": filters.get("company") or "",
		"item_group": filters.get("item_group") or "",
	}

	rows = frappe.db.sql(
		"""
		select
			t.item_group,
			sum(t.inward_qty) as inward_qty,
			sum(t.transfer_qty) as transfer_qty,
			sum(t.outward_qty) as outward_qty
		from (
			select
				ifnull(i.item_group, 'Uncategorized') as item_group,
				sum(ci.qty) as inward_qty,
				0 as transfer_qty,
				0 as outward_qty
			from `tabCold Storage Inward` p
			inner join `tabCold Storage Inward Item` ci on ci.parent = p.name
			left join `tabItem` i on i.name = ci.item
			where p.docstatus = 1
				and p.posting_date between %(from_date)s and %(to_date)s
				and (%(company)s = '' or p.company = %(company)s)
				and (%(item_group)s = '' or ifnull(i.item_group, 'Uncategorized') = %(item_group)s)
			group by ifnull(i.item_group, 'Uncategorized')

			union all

			select
				ifnull(i.item_group, 'Uncategorized') as item_group,
				0 as inward_qty,
				sum(ct.qty) as transfer_qty,
				0 as outward_qty
			from `tabCold Storage Transfer` p
			inner join `tabCold Storage Transfer Item` ct on ct.parent = p.name
			left join `tabItem` i on i.name = ct.item
			where p.docstatus = 1
				and p.posting_date between %(from_date)s and %(to_date)s
				and (%(company)s = '' or p.company = %(company)s)
				and (%(item_group)s = '' or ifnull(i.item_group, 'Uncategorized') = %(item_group)s)
			group by ifnull(i.item_group, 'Uncategorized')

			union all

			select
				ifnull(i.item_group, 'Uncategorized') as item_group,
				0 as inward_qty,
				0 as transfer_qty,
				sum(co.qty) as outward_qty
			from `tabCold Storage Outward` p
			inner join `tabCold Storage Outward Item` co on co.parent = p.name
			left join `tabItem` i on i.name = co.item
			where p.docstatus = 1
				and p.posting_date between %(from_date)s and %(to_date)s
				and (%(company)s = '' or p.company = %(company)s)
				and (%(item_group)s = '' or ifnull(i.item_group, 'Uncategorized') = %(item_group)s)
			group by ifnull(i.item_group, 'Uncategorized')
		) t
		group by t.item_group
		order by sum(t.inward_qty) desc, t.item_group asc
		""",
		params,
		as_dict=True,
	)

	for row in rows:
		inward_qty = flt(row.get("inward_qty"))
		transfer_qty = flt(row.get("transfer_qty"))
		outward_qty = flt(row.get("outward_qty"))
		row["inward_qty"] = inward_qty
		row["transfer_qty"] = transfer_qty
		row["outward_qty"] = outward_qty
		row["flow_imbalance"] = inward_qty - outward_qty
		row["transfer_load_pct"] = (transfer_qty / inward_qty * 100.0) if inward_qty else 0.0
		row["dispatch_ratio_pct"] = (outward_qty / inward_qty * 100.0) if inward_qty else 0.0
		row["bottleneck_score"] = max(0.0, (inward_qty - outward_qty)) + max(0.0, (transfer_qty - outward_qty))

	rows.sort(key=lambda d: (flt(d.get("bottleneck_score")), flt(d.get("inward_qty"))), reverse=True)
	return rows


def get_chart(data, filters):
	if not data:
		return None

	top_rows = sorted(data, key=lambda d: flt(d.get("inward_qty")), reverse=True)[: filters.top_n_groups]

	chart = {
		"data": {
			"labels": [r.get("item_group") for r in top_rows],
			"datasets": [
				{"name": _("Inward"), "chartType": "bar", "values": [flt(r.get("inward_qty")) for r in top_rows]},
				{"name": _("Transfer"), "chartType": "bar", "values": [flt(r.get("transfer_qty")) for r in top_rows]},
				{"name": _("Outward"), "chartType": "bar", "values": [flt(r.get("outward_qty")) for r in top_rows]},
			],
		},
		"type": "axis-mixed",
		"barOptions": {"stacked": 0, "spaceRatio": 0.25},
		"colors": ["#22c55e", "#f59e0b", "#ef4444"],
	}

	# Sankey-style payload for downstream UI/custom chart rendering.
	chart["custom_sankey"] = get_sankey_payload(top_rows)
	return chart


def get_sankey_payload(rows):
	nodes = [{"name": _("Inward")}, {"name": _("Transfer")}, {"name": _("Outward")}]
	links = []

	for row in rows:
		group = row.get("item_group")
		nodes.append({"name": group})
		inward_qty = flt(row.get("inward_qty"))
		transfer_qty = flt(row.get("transfer_qty"))
		outward_qty = flt(row.get("outward_qty"))
		if inward_qty > 0:
			links.append({"source": _("Inward"), "target": group, "value": inward_qty})
		if transfer_qty > 0:
			links.append({"source": group, "target": _("Transfer"), "value": transfer_qty})
		if outward_qty > 0:
			links.append({"source": group, "target": _("Outward"), "value": outward_qty})

	return {"nodes": nodes, "links": links}


def get_summary(data):
	total_inward = sum(flt(r.get("inward_qty")) for r in data)
	total_transfer = sum(flt(r.get("transfer_qty")) for r in data)
	total_outward = sum(flt(r.get("outward_qty")) for r in data)
	total_bottleneck = sum(flt(r.get("bottleneck_score")) for r in data)

	return [
		{"label": _("Item Groups"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Inward Qty"), "value": total_inward, "datatype": "Float", "indicator": "Green"},
		{"label": _("Transfer Qty"), "value": total_transfer, "datatype": "Float", "indicator": "Orange"},
		{"label": _("Outward Qty"), "value": total_outward, "datatype": "Float", "indicator": "Red"},
		{"label": _("Bottleneck Score"), "value": total_bottleneck, "datatype": "Float", "indicator": "Orange"},
	]
