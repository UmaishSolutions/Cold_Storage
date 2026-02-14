import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate
from datetime import date

STATUS_CAPACITY_NOT_SET = "Capacity Not Set"
STATUS_EMPTY = "Empty"
STATUS_AVAILABLE = "Available"
STATUS_NEAR_FULL = "Near Full"
STATUS_OVER_CAPACITY = "Over Capacity"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	set_default_filters(filters)
	validate_filters(filters)

	columns = get_columns()
	warehouses = get_warehouses(filters)
	if not warehouses:
		return columns, [], _("No warehouses found for selected filters."), None, []

	months = get_months(filters.from_date, filters.to_date)
	opening_qty_map = get_opening_qty_map(warehouses, months[0])
	monthly_change_map = get_monthly_change_map(warehouses, months[0], filters.to_date)

	data = build_rows(warehouses, months, opening_qty_map, monthly_change_map)
	message = get_report_message(warehouses)
	chart = get_chart_data(data, months, warehouses, filters)
	report_summary = get_report_summary(data, months, warehouses)
	return columns, data, message, chart, report_summary


def set_default_filters(filters):
	if not filters.get("to_date"):
		filters.to_date = nowdate()
	if not filters.get("from_date"):
		to_date = getdate(filters.to_date)
		start_year = to_date.year
		start_month = to_date.month - 5
		while start_month <= 0:
			start_month += 12
			start_year -= 1
		filters.from_date = date(start_year, start_month, 1)


def validate_filters(filters):
	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be greater than To Date"))


def get_columns():
	return [
		{
			"label": _("Month"),
			"fieldname": "month_label",
			"fieldtype": "Data",
			"width": 110,
		},
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
			"label": _("Occupied Stock (Jute Eq.)"),
			"fieldname": "occupied_stock_qty",
			"fieldtype": "Float",
			"width": 170,
		},
		{
			"label": _("Remaining Capacity (Jute)"),
			"fieldname": "remaining_capacity_qty",
			"fieldtype": "Float",
			"width": 170,
		},
		{
			"label": _("Occupancy (%)"),
			"fieldname": "occupancy_pct",
			"fieldtype": "Percent",
			"width": 130,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 140,
		},
	]


def get_warehouses(filters):
	capacity_expr = get_capacity_expression()

	return frappe.db.sql(
		f"""
		select
			w.name as warehouse,
			w.company,
			{capacity_expr} as warehouse_capacity
		from `tabWarehouse` w
		where ifnull(w.is_group, 0) = 0
			and ifnull(w.disabled, 0) = 0
			and (%(company)s = '' or w.company = %(company)s)
			and (%(warehouse)s = '' or w.name = %(warehouse)s)
		order by w.name
		""",
		{
			"company": filters.get("company") or "",
			"warehouse": filters.get("warehouse") or "",
		},
		as_dict=True,
	)


def get_capacity_expression() -> str:
	if frappe.db.has_column("Warehouse", "custom_storage_capacity"):
		return "ifnull(w.custom_storage_capacity, 0)"
	return "0"


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


def get_opening_qty_map(warehouses, from_month_start):
	warehouse_names = tuple(w.warehouse for w in warehouses)
	if not warehouse_names:
		return {}

	rows = frappe.db.sql(
		"""
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
			) as opening_qty
		from `tabStock Ledger Entry` sle
		left join `tabItem` i on i.name = sle.item_code
		where ifnull(sle.is_cancelled, 0) = 0
			and sle.posting_date < %(from_month_start)s
			and sle.warehouse in %(warehouses)s
		group by sle.warehouse
		""",
		{
			"from_month_start": from_month_start,
			"warehouses": warehouse_names,
		},
		as_dict=True,
	)

	return {row.warehouse: flt(row.opening_qty) for row in rows}


def get_monthly_change_map(warehouses, from_month_start, to_date):
	warehouse_names = tuple(w.warehouse for w in warehouses)
	if not warehouse_names:
		return {}

	rows = frappe.db.sql(
		"""
		select
			sle.warehouse,
			year(sle.posting_date) as year_num,
			month(sle.posting_date) as month_num,
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
			) as qty_change
		from `tabStock Ledger Entry` sle
		left join `tabItem` i on i.name = sle.item_code
		where ifnull(sle.is_cancelled, 0) = 0
			and sle.posting_date >= %(from_month_start)s
			and sle.posting_date <= %(to_date)s
			and sle.warehouse in %(warehouses)s
		group by sle.warehouse, year(sle.posting_date), month(sle.posting_date)
		""",
		{
			"from_month_start": from_month_start,
			"to_date": to_date,
			"warehouses": warehouse_names,
		},
		as_dict=True,
	)

	return {(row.warehouse, cint(row.year_num), cint(row.month_num)): flt(row.qty_change) for row in rows}


def build_rows(warehouses, months, opening_qty_map, monthly_change_map):
	rows = []
	current_qty_map = {w.warehouse: flt(opening_qty_map.get(w.warehouse)) for w in warehouses}

	for month_start in months:
		month_key = month_start.strftime("%Y-%m-01")
		month_label = month_start.strftime("%b %Y")

		for warehouse in warehouses:
			warehouse_name = warehouse.warehouse
			current_qty_map[warehouse_name] = flt(current_qty_map.get(warehouse_name)) + flt(
				monthly_change_map.get((warehouse_name, month_start.year, month_start.month))
			)

			occupied_qty = flt(current_qty_map.get(warehouse_name))
			if abs(occupied_qty) < 1e-9:
				occupied_qty = 0.0

			capacity = flt(warehouse.warehouse_capacity)
			remaining_capacity = capacity - occupied_qty if capacity else 0.0
			occupancy_pct = (occupied_qty / capacity * 100.0) if capacity else 0.0

			rows.append(
				frappe._dict(
					{
						"month_start": month_key,
						"month_label": month_label,
						"warehouse": warehouse_name,
						"company": warehouse.company,
						"warehouse_capacity": capacity,
						"occupied_stock_qty": occupied_qty,
						"remaining_capacity_qty": remaining_capacity,
						"occupancy_pct": occupancy_pct,
						"status": get_occupancy_status(occupied_qty, capacity),
					}
				)
			)

	return rows


def get_occupancy_status(occupied_qty: float, warehouse_capacity: float):
	if warehouse_capacity <= 0:
		return STATUS_CAPACITY_NOT_SET
	if occupied_qty <= 0:
		return STATUS_EMPTY
	occupancy_pct = occupied_qty / warehouse_capacity * 100.0
	if occupancy_pct > 100:
		return STATUS_OVER_CAPACITY
	if occupancy_pct >= 90:
		return STATUS_NEAR_FULL
	return STATUS_AVAILABLE


def get_chart_data(data, months, warehouses, filters):
	if not data:
		return None

	selected_warehouses = []
	if filters.get("warehouse"):
		selected_warehouses = [filters.warehouse]
	else:
		latest_month = months[-1].strftime("%Y-%m-01")
		latest_rows = {
			row.warehouse: row for row in data if row.month_start == latest_month and row.warehouse
		}
		warehouse_names = [w.warehouse for w in warehouses]
		selected_warehouses = sorted(
			warehouse_names,
			key=lambda w: flt(latest_rows.get(w, {}).get("occupancy_pct", 0)),
			reverse=True,
		)[:6]

	if not selected_warehouses:
		return None

	occupancy_map = {
		(row.warehouse, row.month_start): flt(row.occupancy_pct)
		for row in data
		if row.warehouse in selected_warehouses
	}

	labels = [month.strftime("%b %Y") for month in months]
	datasets = []
	for warehouse in selected_warehouses:
		values = [
			flt(occupancy_map.get((warehouse, month.strftime("%Y-%m-01")), 0)) for month in months
		]
		datasets.append({"name": warehouse, "values": values})

	return {
		"data": {
			"labels": labels,
			"datasets": datasets,
		},
		"type": "line",
	}


def get_report_summary(data, months, warehouses):
	if not data:
		return []

	latest_month = months[-1].strftime("%Y-%m-01")
	latest_rows = [row for row in data if row.month_start == latest_month]

	total_capacity = sum(flt(row.warehouse_capacity) for row in latest_rows if flt(row.warehouse_capacity) > 0)
	total_occupied = sum(flt(row.occupied_stock_qty) for row in latest_rows)
	overall_occupancy_pct = (total_occupied / total_capacity * 100.0) if total_capacity else 0.0
	over_capacity_count = sum(1 for row in latest_rows if row.status == STATUS_OVER_CAPACITY)
	without_capacity_count = sum(1 for row in warehouses if flt(row.warehouse_capacity) <= 0)

	return [
		{
			"value": len(warehouses),
			"label": _("Warehouses Tracked"),
			"datatype": "Int",
			"indicator": "Blue",
		},
		{
			"value": len(months),
			"label": _("Months Covered"),
			"datatype": "Int",
			"indicator": "Blue",
		},
		{
			"value": total_occupied,
			"label": _("Latest Occupied Stock (Jute Eq.)"),
			"datatype": "Float",
			"indicator": "Green",
		},
		{
			"value": overall_occupancy_pct,
			"label": _("Latest Overall Occupancy (%)"),
			"datatype": "Percent",
			"indicator": "Orange",
		},
		{
			"value": over_capacity_count,
			"label": _("Over Capacity (Latest Month)"),
			"datatype": "Int",
			"indicator": "Red",
		},
		{
			"value": without_capacity_count,
			"label": _("Warehouses Without Capacity"),
			"datatype": "Int",
			"indicator": "Orange",
		},
	]


def get_report_message(warehouses):
	without_capacity_count = sum(1 for row in warehouses if flt(row.warehouse_capacity) <= 0)
	if without_capacity_count == 0:
		return None

	return _(
		"Storage Capacity is not set for {0} warehouse(s). Set Warehouse > Storage Capacity to calculate occupancy timeline. Net Bag stock is auto-converted using 1 Jute Bag = 2 Net Bag."
	).format(without_capacity_count)
