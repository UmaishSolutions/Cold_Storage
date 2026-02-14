# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from json import JSONDecodeError, loads

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


APP_CUSTOM_FIELDS = {
	"Batch": [
		{
			"fieldname": "custom_customer",
			"fieldtype": "Link",
			"label": "Customer",
			"options": "Customer",
			"insert_after": "item_name",
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
	],
	"Warehouse": [
		{
			"fieldname": "custom_storage_capacity",
			"fieldtype": "Float",
			"label": "Storage Capacity",
			"insert_after": "warehouse_type",
			"in_standard_filter": 1,
			"non_negative": 1,
			"default": "0",
			"description": "Maximum storable quantity in this warehouse.",
		}
	],
}

WORKSPACE_NAME = "Cold Storage"
WAREHOUSE_OCCUPANCY_REPORT = "Cold Storage Warehouse Occupancy Timeline"
WAREHOUSE_OCCUPANCY_CHART = "Warehouse Occupancy Timeline"
WAREHOUSE_OCCUPANCY_CHART_BLOCK_ID = "chart-warehouse-occupancy-timeline"


def _ensure_batch_customizations() -> None:
	"""Apply custom fields and properties required by the cold storage model."""
	create_custom_fields(APP_CUSTOM_FIELDS, update=True)
	make_property_setter("Batch", "batch_id", "unique", "0", "Check")
	frappe.db.updatedb("Batch")
	frappe.db.updatedb("Warehouse")
	frappe.clear_cache(doctype="Batch")
	frappe.clear_cache(doctype="Warehouse")


def _ensure_dashboard_chart_types() -> None:
	"""Keep cold storage chart presentation types aligned with dashboard intent."""
	frappe.db.sql(
		"""
		update `tabDashboard Chart`
		set `type` = case
			when name = 'Yearly Inward Outward Trend' then 'Line'
			when name in ('Inward Quantity Trend', 'Outward Quantity Trend') then 'Bar'
			else `type`
		end
		where name in ('Inward Quantity Trend', 'Outward Quantity Trend', 'Yearly Inward Outward Trend')
		"""
	)
	for chart_name in (
		"Inward Quantity Trend",
		"Outward Quantity Trend",
		"Yearly Inward Outward Trend",
	):
		frappe.cache.delete_key(f"chart-data:{chart_name}")


def _ensure_workspace_assets() -> None:
	"""Ensure cold storage analytics are visible on the workspace dashboard."""
	if not frappe.db.exists("Workspace", WORKSPACE_NAME):
		return

	workspace = frappe.get_doc("Workspace", WORKSPACE_NAME)
	updated = False

	if frappe.db.exists("Report", WAREHOUSE_OCCUPANCY_REPORT):
		has_report_link = any(
			link.type == "Link"
			and link.link_type == "Report"
			and link.link_to == WAREHOUSE_OCCUPANCY_REPORT
			for link in workspace.get("links", [])
		)
		if not has_report_link:
			workspace.append(
				"links",
				{
					"type": "Link",
					"label": "Warehouse Occupancy Timeline",
					"link_type": "Report",
					"link_to": WAREHOUSE_OCCUPANCY_REPORT,
				},
			)
			updated = True

	if frappe.db.exists("Dashboard Chart", WAREHOUSE_OCCUPANCY_CHART):
		has_chart = any(
			chart.chart_name == WAREHOUSE_OCCUPANCY_CHART for chart in workspace.get("charts", [])
		)
		if not has_chart:
			workspace.append(
				"charts",
				{
					"label": WAREHOUSE_OCCUPANCY_CHART,
					"chart_name": WAREHOUSE_OCCUPANCY_CHART,
				},
			)
			updated = True

		content_blocks = _get_workspace_content_blocks(workspace.content)
		has_chart_block = any(
			block.get("type") == "chart"
			and (block.get("data") or {}).get("chart_name") == WAREHOUSE_OCCUPANCY_CHART
			for block in content_blocks
		)
		if not has_chart_block:
			content_blocks.append(
				{
					"id": WAREHOUSE_OCCUPANCY_CHART_BLOCK_ID,
					"type": "chart",
					"data": {"chart_name": WAREHOUSE_OCCUPANCY_CHART, "col": 12},
				}
			)
			workspace.content = frappe.as_json(content_blocks)
			updated = True

	if updated:
		workspace.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Workspace")


def _get_workspace_content_blocks(content: str | None) -> list[dict]:
	if not content:
		return []

	try:
		blocks = loads(content)
	except (JSONDecodeError, TypeError):
		return []

	if not isinstance(blocks, list):
		return []

	return [block for block in blocks if isinstance(block, dict)]


def after_install() -> None:
	_ensure_batch_customizations()
	_ensure_dashboard_chart_types()
	_ensure_workspace_assets()
	_sync_role_based_access()


def after_migrate() -> None:
	_ensure_batch_customizations()
	_ensure_dashboard_chart_types()
	_ensure_workspace_assets()


def _sync_role_based_access() -> None:
	from cold_storage.setup.role_based_access import sync_role_based_access

	sync_role_based_access()
