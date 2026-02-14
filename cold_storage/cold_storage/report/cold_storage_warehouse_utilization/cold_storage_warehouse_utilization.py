import frappe
from frappe import _
from frappe.utils import flt, nowdate

STATUS_CAPACITY_NOT_SET = "Capacity Not Set"
STATUS_EMPTY = "Empty"
STATUS_AVAILABLE = "Available"
STATUS_NEAR_FULL = "Near Full"
STATUS_OVER_CAPACITY = "Over Capacity"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("as_on_date"):
		filters.as_on_date = nowdate()

	columns = get_columns()
	data = get_data(filters)
	message = get_report_message(data)
	chart = get_chart_data(data)
	report_summary = get_report_summary(data)
	return columns, data, message, chart, report_summary


def get_columns():
	return [
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 220,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 160,
		},
		{
			"label": _("Warehouse Capacity"),
			"fieldname": "warehouse_capacity",
			"fieldtype": "Float",
			"width": 150,
		},
		{
			"label": _("Available Stock (Jute Eq.)"),
			"fieldname": "available_stock_qty",
			"fieldtype": "Float",
			"width": 140,
		},
		{
			"label": _("Remaining Capacity (Jute)"),
			"fieldname": "remaining_capacity_qty",
			"fieldtype": "Float",
			"width": 150,
		},
		{
			"label": _("Utilization (%)"),
			"fieldname": "utilization_pct",
			"fieldtype": "Percent",
			"width": 140,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 140,
		},
	]


def get_data(filters):
	capacity_expr = get_capacity_expression()

	rows = frappe.db.sql(
		f"""
		select
			w.name as warehouse,
			w.company,
			{capacity_expr} as warehouse_capacity,
			ifnull(stock.available_stock_qty, 0) as available_stock_qty
		from `tabWarehouse` w
			left join (
				select
					sle.warehouse,
					sum(
						case
							when (
								lower(ifnull(i.item_group, '')) like '%%net bag%%'
								or lower(ifnull(i.item_name, '')) like '%%net bag%%'
								or lower(ifnull(i.name, '')) like '%%net bag%%'
							)
							then sle.actual_qty / 2
							else sle.actual_qty
						end
					) as available_stock_qty
				from `tabStock Ledger Entry` sle
				left join `tabItem` i on i.name = sle.item_code
				where ifnull(sle.is_cancelled, 0) = 0
					and sle.posting_date <= %(as_on_date)s
				group by sle.warehouse
		) stock on stock.warehouse = w.name
		where ifnull(w.is_group, 0) = 0
			and ifnull(w.disabled, 0) = 0
			and (%(company)s = '' or w.company = %(company)s)
			and (%(warehouse)s = '' or w.name = %(warehouse)s)
			and ({capacity_expr} > 0 or ifnull(stock.available_stock_qty, 0) > 0)
		order by w.name
		""",
		{
			"as_on_date": filters.as_on_date,
			"company": filters.get("company") or "",
			"warehouse": filters.get("warehouse") or "",
		},
		as_dict=True,
	)

	for row in rows:
		row.warehouse_capacity = flt(row.warehouse_capacity)
		row.available_stock_qty = flt(row.available_stock_qty)
		row.remaining_capacity_qty = (
			row.warehouse_capacity - row.available_stock_qty if row.warehouse_capacity else 0.0
		)
		row.utilization_pct = (
			(row.available_stock_qty / row.warehouse_capacity * 100.0) if row.warehouse_capacity else 0.0
		)
		row.status = get_utilization_status(
			available_stock_qty=row.available_stock_qty,
			warehouse_capacity=row.warehouse_capacity,
		)

	rows.sort(
		key=lambda row: (
			1 if row.warehouse_capacity > 0 else 0,
			row.utilization_pct,
			row.available_stock_qty,
		),
		reverse=True,
	)

	return rows


def get_capacity_expression() -> str:
	if frappe.db.has_column("Warehouse", "custom_storage_capacity"):
		return "ifnull(w.custom_storage_capacity, 0)"
	return "0"


def get_utilization_status(*, available_stock_qty: float, warehouse_capacity: float) -> str:
	if warehouse_capacity <= 0:
		return STATUS_CAPACITY_NOT_SET
	if available_stock_qty <= 0:
		return STATUS_EMPTY
	utilization_pct = available_stock_qty / warehouse_capacity * 100.0
	if utilization_pct > 100:
		return STATUS_OVER_CAPACITY
	if utilization_pct >= 90:
		return STATUS_NEAR_FULL
	return STATUS_AVAILABLE


def get_chart_data(data):
	chart_rows = data[:10]
	if not chart_rows:
		return None

	return {
		"data": {
			"labels": [row.warehouse for row in chart_rows],
			"datasets": [{"name": _("Utilization %"), "values": [row.utilization_pct for row in chart_rows]}],
		},
		"type": "bar",
		"colors": ["#0ea5e9"],
	}


def get_report_summary(data):
	total_capacity = sum(flt(row.warehouse_capacity) for row in data if flt(row.warehouse_capacity) > 0)
	total_available_stock = sum(flt(row.available_stock_qty) for row in data)
	overall_utilization = (total_available_stock / total_capacity * 100.0) if total_capacity else 0.0
	over_capacity_count = sum(1 for row in data if row.status == STATUS_OVER_CAPACITY)
	capacity_missing_count = sum(1 for row in data if row.status == STATUS_CAPACITY_NOT_SET)

	return [
		{
			"value": total_capacity,
			"label": _("Total Capacity"),
			"datatype": "Float",
			"indicator": "Blue",
		},
		{
			"value": total_available_stock,
			"label": _("Total Available Stock (Jute Eq.)"),
			"datatype": "Float",
			"indicator": "Green",
		},
		{
			"value": overall_utilization,
			"label": _("Overall Utilization (%)"),
			"datatype": "Percent",
			"indicator": "Orange",
		},
		{
			"value": over_capacity_count,
			"label": _("Warehouses Over Capacity"),
			"datatype": "Int",
			"indicator": "Red",
		},
		{
			"value": capacity_missing_count,
			"label": _("Warehouses Without Capacity"),
			"datatype": "Int",
			"indicator": "Orange",
		},
	]


def get_report_message(data) -> str | None:
	capacity_missing_count = sum(1 for row in data if row.status == STATUS_CAPACITY_NOT_SET)
	if capacity_missing_count == 0:
		return None

	return _(
		"Storage Capacity is not set for {0} warehouse(s). Set Warehouse > Storage Capacity to calculate utilization. Net Bag stock is auto-converted using 1 Jute Bag = 2 Net Bag."
	).format(capacity_missing_count)
