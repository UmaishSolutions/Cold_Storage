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
ACTIVE_BATCHES_NUMBER_CARD = "Active Batches"
ACTIVE_BATCHES_NUMBER_CARD_BLOCK_ID = "number-card-active-batches"
LIVE_BATCH_STOCK_REPORT = "Cold Storage Live Batch Stock"
LIVE_BATCH_STOCK_SHORTCUT_LABEL = "Live Batch Stock"
LIVE_BATCH_STOCK_SHORTCUT_BLOCK_ID = "shortcut-cold-storage-live-batch-stock"
REPORTS_SECTION_LABEL = "Reports"
SETUP_SECTION_LABEL = "Setup"
MASTERS_SECTION_LABEL = "Masters"
LIVE_BATCH_STOCK_REPORT_ROLES = (
	"System Manager",
	"Cold Storage Admin",
	"Cold Storage Warehouse Manager",
	"Cold Storage Inbound Operator",
	"Cold Storage Inventory Controller",
	"Cold Storage Billing Executive",
	"Cold Storage Client Portal User",
	"Stock Manager",
	"Stock User",
)


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


def _ensure_top_customers_chart_source() -> None:
	"""Ensure Top Customers chart is based on available stock (Customer Register)."""
	if not frappe.db.exists("Dashboard Chart", "Top Customers"):
		return

	frappe.db.set_value(
		"Dashboard Chart",
		"Top Customers",
		{
			"report_name": "Cold Storage Customer Register",
			"type": "Bar",
			"use_report_chart": 1,
		},
		update_modified=False,
	)
	frappe.cache.delete_key("chart-data:Top Customers")


def _ensure_workspace_assets() -> None:
	"""Ensure cold storage analytics are visible on the workspace dashboard."""
	if not frappe.db.exists("Workspace", WORKSPACE_NAME):
		return

	workspace = frappe.get_doc("Workspace", WORKSPACE_NAME)
	updated = False

	if frappe.db.exists("Report", WAREHOUSE_OCCUPANCY_REPORT):
		has_report_link = any(
			link.type == "Link" and link.link_type == "Report" and link.link_to == WAREHOUSE_OCCUPANCY_REPORT
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

	if frappe.db.exists("Report", LIVE_BATCH_STOCK_REPORT):
		has_live_batch_stock_link = any(
			link.type == "Link" and link.link_type == "Report" and link.link_to == LIVE_BATCH_STOCK_REPORT
			for link in workspace.get("links", [])
		)
		if not has_live_batch_stock_link:
			workspace.append(
				"links",
				{
					"type": "Link",
					"label": LIVE_BATCH_STOCK_SHORTCUT_LABEL,
					"link_type": "Report",
					"link_to": LIVE_BATCH_STOCK_REPORT,
				},
			)
			updated = True

		has_live_batch_stock_shortcut = any(
			shortcut.type == "Report" and shortcut.link_to == LIVE_BATCH_STOCK_REPORT
			for shortcut in workspace.get("shortcuts", [])
		)
		if not has_live_batch_stock_shortcut:
			workspace.append(
				"shortcuts",
				{
					"type": "Report",
					"label": LIVE_BATCH_STOCK_SHORTCUT_LABEL,
					"link_to": LIVE_BATCH_STOCK_REPORT,
					"color": "Orange",
				},
			)
			updated = True

		content_blocks = _get_workspace_content_blocks(workspace.content)
		has_live_batch_stock_shortcut_block = any(
			block.get("type") == "shortcut"
			and (block.get("data") or {}).get("shortcut_name") == LIVE_BATCH_STOCK_SHORTCUT_LABEL
			for block in content_blocks
		)
		if not has_live_batch_stock_shortcut_block:
			content_blocks.append(
				{
					"id": LIVE_BATCH_STOCK_SHORTCUT_BLOCK_ID,
					"type": "shortcut",
					"data": {"shortcut_name": LIVE_BATCH_STOCK_SHORTCUT_LABEL, "col": 3},
				}
			)
			workspace.content = frappe.as_json(content_blocks)
			updated = True

	if frappe.db.exists("Number Card", ACTIVE_BATCHES_NUMBER_CARD):
		has_number_card = any(
			card.number_card_name == ACTIVE_BATCHES_NUMBER_CARD for card in workspace.get("number_cards", [])
		)
		if not has_number_card:
			workspace.append(
				"number_cards",
				{
					"label": ACTIVE_BATCHES_NUMBER_CARD,
					"number_card_name": ACTIVE_BATCHES_NUMBER_CARD,
				},
			)
			updated = True

		content_blocks = _get_workspace_content_blocks(workspace.content)
		has_number_card_block = any(
			block.get("type") == "number_card"
			and (block.get("data") or {}).get("number_card_name") == ACTIVE_BATCHES_NUMBER_CARD
			for block in content_blocks
		)
		if not has_number_card_block:
			# Prefer replacing legacy duplicate "Total Active Items" slot to keep top-row density unchanged.
			replaced_existing_slot = False
			for block in content_blocks:
				if block.get("type") != "number_card":
					continue
				data = block.get("data") or {}
				if (
					block.get("id") == "jXtpNEtdDN"
					and data.get("number_card_name") == "Total Active Items"
				):
					data["number_card_name"] = ACTIVE_BATCHES_NUMBER_CARD
					block["data"] = data
					replaced_existing_slot = True
					break

			if not replaced_existing_slot:
				content_blocks.append(
					{
						"id": ACTIVE_BATCHES_NUMBER_CARD_BLOCK_ID,
						"type": "number_card",
						"data": {"number_card_name": ACTIVE_BATCHES_NUMBER_CARD, "col": 3},
					}
				)

			workspace.content = frappe.as_json(content_blocks)
			updated = True

	if updated:
		workspace.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Workspace")


def _ensure_workspace_sidebar_assets() -> None:
	"""Ensure live batch stock report appears inside Reports section in sidebar."""
	if not frappe.db.exists("Workspace Sidebar", WORKSPACE_NAME):
		return

	sidebar = frappe.get_doc("Workspace Sidebar", WORKSPACE_NAME)
	items = list(sidebar.get("items", []))
	existing_live_items = [
		item
		for item in items
		if item.type == "Link" and item.link_type == "Report" and item.link_to == LIVE_BATCH_STOCK_REPORT
	]
	items_without_live = [item for item in items if item not in existing_live_items]

	live_item = {
		"type": "Link",
		"label": LIVE_BATCH_STOCK_SHORTCUT_LABEL,
		"link_type": "Report",
		"link_to": LIVE_BATCH_STOCK_REPORT,
		"child": 1,
		"collapsible": 1,
		"keep_closed": 0,
		"indent": 0,
		"show_arrow": 0,
		"icon": "",
	}
	if existing_live_items:
		source = existing_live_items[0]
		live_item.update(
			{
				"label": source.get("label") or LIVE_BATCH_STOCK_SHORTCUT_LABEL,
				"child": source.get("child", 1),
				"collapsible": source.get("collapsible", 1),
				"keep_closed": source.get("keep_closed", 0),
				"indent": source.get("indent", 0),
				"show_arrow": source.get("show_arrow", 0),
				"icon": source.get("icon") or "",
			}
		)

	reports_section_index = next(
		(
			idx
			for idx, item in enumerate(items_without_live)
			if item.get("type") == "Section Break"
			and (item.get("label") or "").strip() == REPORTS_SECTION_LABEL
		),
		None,
	)
	setup_section_index = next(
		(
			idx
			for idx, item in enumerate(items_without_live)
			if item.get("type") == "Section Break"
			and (item.get("label") or "").strip() == SETUP_SECTION_LABEL
		),
		None,
	)
	insert_at = len(items_without_live)
	if reports_section_index is not None:
		next_section_after_reports = next(
			(
				idx
				for idx in range(reports_section_index + 1, len(items_without_live))
				if items_without_live[idx].get("type") == "Section Break"
			),
			None,
		)
		insert_at = next_section_after_reports if next_section_after_reports is not None else len(items_without_live)
	elif setup_section_index is not None:
		insert_at = setup_section_index

	items_without_live.insert(insert_at, live_item)
	items_with_required_masters = _ensure_sidebar_link_under_section(
		items_without_live,
		section_label=MASTERS_SECTION_LABEL,
		link_type="DocType",
		link_to="Item",
		label="Item",
	)
	items_with_required_masters = _ensure_sidebar_link_under_section(
		items_with_required_masters,
		section_label=MASTERS_SECTION_LABEL,
		link_type="DocType",
		link_to="Customer",
		label="Customer",
	)

	sidebar.set("items", items_with_required_masters)
	for idx, item in enumerate(sidebar.get("items", []), start=1):
		item.idx = idx
	sidebar.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Workspace Sidebar")


def _ensure_sidebar_link_under_section(
	items: list, *, section_label: str, link_type: str, link_to: str, label: str
) -> list:
	"""Place a sidebar link under a specific section, deduplicating existing entries."""
	captured_item = None
	clean_items = []
	for item in items:
		if (
			item.get("type") == "Link"
			and (item.get("link_type") or "").strip() == link_type
			and (item.get("link_to") or "").strip() == link_to
		):
			if captured_item is None:
				captured_item = item
			continue
		clean_items.append(item)

	link_item = {
		"type": "Link",
		"label": label,
		"link_type": link_type,
		"link_to": link_to,
		"child": 1,
		"collapsible": 1,
		"keep_closed": 0,
		"indent": 0,
		"show_arrow": 0,
		"icon": "",
	}
	if captured_item:
		link_item.update(
			{
				"label": captured_item.get("label") or label,
				"child": captured_item.get("child", 1),
				"collapsible": captured_item.get("collapsible", 1),
				"keep_closed": captured_item.get("keep_closed", 0),
				"indent": captured_item.get("indent", 0),
				"show_arrow": captured_item.get("show_arrow", 0),
				"icon": captured_item.get("icon") or "",
			}
		)

	section_index = next(
		(
			idx
			for idx, item in enumerate(clean_items)
			if item.get("type") == "Section Break"
			and (item.get("label") or "").strip() == section_label
		),
		None,
	)
	if section_index is None:
		clean_items.append(link_item)
		return clean_items

	next_section_index = next(
		(
			idx
			for idx in range(section_index + 1, len(clean_items))
			if clean_items[idx].get("type") == "Section Break"
		),
		None,
	)
	insert_at = next_section_index if next_section_index is not None else len(clean_items)
	clean_items.insert(insert_at, link_item)
	return clean_items


def _ensure_live_batch_stock_report_roles() -> None:
	"""Ensure all expected roles can see and run the live batch stock report."""
	if not frappe.db.exists("Report", LIVE_BATCH_STOCK_REPORT):
		return

	report = frappe.get_doc("Report", LIVE_BATCH_STOCK_REPORT)
	existing_roles = {row.role for row in report.get("roles", []) if row.role}
	missing_roles = [
		role
		for role in LIVE_BATCH_STOCK_REPORT_ROLES
		if role not in existing_roles and frappe.db.exists("Role", role)
	]
	if not missing_roles:
		return

	for role in missing_roles:
		report.append("roles", {"role": role})

	report.save(ignore_permissions=True)


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


def _ensure_default_uom_setting(*, create_uom_if_missing: bool) -> None:
	"""Keep Cold Storage Settings.default_uom linked to a valid UOM."""
	if not frappe.db.exists("DocType", "Cold Storage Settings"):
		return

	from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
		resolve_default_uom,
	)

	resolved_uom = resolve_default_uom(create_if_missing=create_uom_if_missing)
	if not resolved_uom:
		return

	current_uom = frappe.db.get_single_value("Cold Storage Settings", "default_uom")
	if current_uom and frappe.db.exists("UOM", current_uom):
		return

	frappe.db.set_single_value("Cold Storage Settings", "default_uom", resolved_uom)


def after_install() -> None:
	_ensure_default_uom_setting(create_uom_if_missing=True)
	_ensure_batch_customizations()
	_ensure_dashboard_chart_types()
	_ensure_top_customers_chart_source()
	_ensure_live_batch_stock_report_roles()
	_ensure_workspace_assets()
	_ensure_workspace_sidebar_assets()
	_sync_role_based_access()


def after_migrate() -> None:
	_ensure_default_uom_setting(create_uom_if_missing=True)
	_ensure_batch_customizations()
	_ensure_dashboard_chart_types()
	_ensure_top_customers_chart_source()
	_ensure_live_batch_stock_report_roles()
	_ensure_workspace_assets()
	_ensure_workspace_sidebar_assets()
	_sync_role_based_access()


def _sync_role_based_access() -> None:
	from cold_storage.setup.role_based_access import sync_role_based_access

	sync_role_based_access()
