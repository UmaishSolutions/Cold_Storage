# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from json import JSONDecodeError, loads

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from cold_storage.client_portal_views import CLIENT_PORTAL_VIEW_PATH_FILTER

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
DEFAULT_WEBPAGE_VIEWS_CHART = "Webpage Views"
LEGACY_CUSTOMER_PORTAL_VIEWS_CHART = "Customer Portal Views"
CLIENT_PORTAL_VIEWS_CHART = "Client Portal Views"
LOGIN_ACTIVITY_CHART = "Login Activity"
LOGIN_ACTIVITY_FILTERS_JSON = (
	'[["Activity Log","status","=","Success",false],["Activity Log","operation","=","Login",false]]'
)
CLIENT_PORTAL_VIEWS_CHART_BLOCK_ID = "chart-cs-portal-views"
CLIENT_PORTAL_VIEWS_FILTERS_JSON = (
	f'[["Web Page View","path","like","{CLIENT_PORTAL_VIEW_PATH_FILTER}",false]]'
)
WAREHOUSE_OCCUPANCY_REPORT = "Cold Storage Warehouse Occupancy Timeline"
WAREHOUSE_OCCUPANCY_CHART = "Warehouse Occupancy Timeline"
WAREHOUSE_OCCUPANCY_CHART_BLOCK_ID = "chart-warehouse-occupancy-timeline"
NET_MOVEMENT_WATERFALL_REPORT = "Cold Storage Net Movement Waterfall Monthly"
NET_MOVEMENT_WATERFALL_CHART = "Net Movement Waterfall (Monthly)"
NET_MOVEMENT_WATERFALL_CHART_BLOCK_ID = "chart-net-movement-waterfall-monthly"
ACTIVE_BATCHES_NUMBER_CARD = "Active Batches"
ACTIVE_BATCHES_NUMBER_CARD_BLOCK_ID = "number-card-active-batches"
LIVE_BATCH_STOCK_REPORT = "Cold Storage Live Batch Stock"
LIVE_BATCH_STOCK_SHORTCUT_LABEL = "Live Batch Stock"
LIVE_BATCH_STOCK_SHORTCUT_BLOCK_ID = "shortcut-cold-storage-live-batch-stock"
LOGIN_ACTIVITY_LOG_REPORT = "Cold Storage Login Activity Log"
LOGIN_ACTIVITY_LOG_SHORTCUT_LABEL = "Login Activity Log"
LOGIN_ACTIVITY_LOG_SHORTCUT_BLOCK_ID = "shortcut-cold-storage-login-activity-log"
CLIENT_PORTAL_ACCESS_LOG_REPORT = "Cold Storage Client Portal Access Log"
CLIENT_PORTAL_ACCESS_LOG_SHORTCUT_LABEL = "Client Portal Access Log"
CLIENT_PORTAL_ACCESS_LOG_SHORTCUT_BLOCK_ID = "shortcut-cold-storage-cs-portal-access-log"
LOT_TRACEABILITY_GRAPH_REPORT = "Cold Storage Lot Traceability Graph"
LOT_TRACEABILITY_GRAPH_SHORTCUT_LABEL = "Lot Traceability Graph"
LOT_TRACEABILITY_GRAPH_SHORTCUT_BLOCK_ID = "shortcut-cold-storage-lot-traceability-graph"
LEGACY_AUDIT_TRAIL_REPORT = "Cold Storage Audit Trail & Compliance Pack"
AUDIT_TRAIL_REPORT = "Cold Storage Audit Trail Compliance Pack"
AUDIT_TRAIL_SHORTCUT_LABEL = "Audit Trail & Compliance Pack"
REPORTS_SECTION_LABEL = "Reports"
INVENTORY_MOVEMENT_SECTION_LABEL = "Inventory & Movement"
COMPLIANCE_ACTIVITY_SECTION_LABEL = "Compliance & Activity"
SETUP_SECTION_LABEL = "Setup"
MASTERS_SECTION_LABEL = "Masters"
PEOPLE_OPS_SECTION_LABEL = "People Ops"
REMOVED_PEOPLE_OPS_DOCTYPES = (
	"Employee",
	"Attendance",
	"Employee Checkin",
	"Payroll Entry",
	"Salary Slip",
	"Additional Salary",
	"Employee Advance",
	"Loan Application",
	"Loan",
	"Loan Disbursement",
	"Loan Repayment",
)
LETTER_HEAD_NAME = "Cold Storage Branded Letter Head"
LETTER_HEAD_HEADER_TEMPLATE = "templates/letter_head/cold_storage_branded_header.html"
LETTER_HEAD_FOOTER_TEMPLATE = "templates/letter_head/cold_storage_branded_footer.html"
SIDEBAR_ICON_BY_LABEL = {
	"Home": "🏠",
	"Inward Receipt": "📥",
	"Outward Dispatch": "📤",
	"Transfer": "🔄",
	REPORTS_SECTION_LABEL: "📊",
	"Inward Register": "🧾",
	"Outward Register": "🚚",
	"Transfer Register": "🔁",
	"Customer Register": "👥",
	"Warehouse Utilization": "📈",
	"Warehouse Occupancy Timeline": "🗓️",
	"Yearly Inward Outward Trend": "📉",
	NET_MOVEMENT_WATERFALL_CHART: "🌊",
	LIVE_BATCH_STOCK_SHORTCUT_LABEL: "❄️",
	LOGIN_ACTIVITY_LOG_SHORTCUT_LABEL: "🔐",
	CLIENT_PORTAL_ACCESS_LOG_SHORTCUT_LABEL: "🌐",
	AUDIT_TRAIL_SHORTCUT_LABEL: "🛡️",
	SETUP_SECTION_LABEL: "⚙️",
	"Cold Storage Settings": "🛠️",
	MASTERS_SECTION_LABEL: "🗂️",
	"Warehouse": "🏬",
	"Batch": "📦",
	"Item": "🏷️",
	"Customer": "🤝",
}
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
AUDIT_TRAIL_REPORT_ROLES = (
	"System Manager",
	"Cold Storage Admin",
	"Cold Storage Warehouse Manager",
	"Cold Storage Inbound Operator",
	"Cold Storage Inventory Controller",
	"Cold Storage Billing Executive",
	"Cold Storage Dispatch Operator",
	"Cold Storage Client Portal User",
	"Stock Manager",
	"Stock User",
)
CLIENT_PORTAL_VIEWS_CHART_ROLES = (
	"System Manager",
	"Cold Storage Admin",
	"Cold Storage Warehouse Manager",
	"Cold Storage Inbound Operator",
	"Cold Storage Inventory Controller",
	"Cold Storage Billing Executive",
	"Cold Storage Dispatch Operator",
	"Stock Manager",
	"Stock User",
)
LOGIN_ACTIVITY_CHART_ROLES = (
	"System Manager",
	"Cold Storage Admin",
	"Cold Storage Warehouse Manager",
	"Cold Storage Inbound Operator",
	"Cold Storage Inventory Controller",
	"Cold Storage Billing Executive",
	"Cold Storage Dispatch Operator",
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
			when name = 'Net Movement Waterfall (Monthly)' then 'Line'
			when name in ('Inward Quantity Trend', 'Outward Quantity Trend') then 'Bar'
			else `type`
		end
		where name in (
			'Inward Quantity Trend',
			'Outward Quantity Trend',
			'Yearly Inward Outward Trend',
			'Net Movement Waterfall (Monthly)'
		)
		"""
	)
	for chart_name in (
		"Inward Quantity Trend",
		"Outward Quantity Trend",
		"Yearly Inward Outward Trend",
		"Net Movement Waterfall (Monthly)",
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


def _ensure_website_view_tracking_enabled() -> None:
	"""Enable website view tracking so Web Page View-based charts can populate."""
	if not frappe.db.exists("DocType", "Website Settings"):
		return

	if frappe.db.get_single_value("Website Settings", "enable_view_tracking"):
		return

	frappe.db.set_single_value("Website Settings", "enable_view_tracking", 1)
	frappe.clear_cache()


def _ensure_client_portal_views_chart() -> None:
	"""Ensure client portal views chart only tracks /cs-portal traffic."""
	chart_values = {
		"based_on": "modified",
		"chart_type": "Count",
		"currency": "",
		"document_type": "Web Page View",
		"dynamic_filters_json": "[]",
		"filters_json": CLIENT_PORTAL_VIEWS_FILTERS_JSON,
		"group_by_type": "Count",
		"is_public": 0,
		"is_standard": 1,
		"module": "Cold Storage",
		"time_interval": "Weekly",
		"timeseries": 1,
		"timespan": "Last Year",
		"type": "Line",
		"use_report_chart": 0,
		"value_based_on": "",
	}

	if frappe.db.exists("Dashboard Chart", LEGACY_CUSTOMER_PORTAL_VIEWS_CHART) and not frappe.db.exists(
		"Dashboard Chart", CLIENT_PORTAL_VIEWS_CHART
	):
		frappe.rename_doc(
			"Dashboard Chart",
			LEGACY_CUSTOMER_PORTAL_VIEWS_CHART,
			CLIENT_PORTAL_VIEWS_CHART,
			force=True,
		)

	if frappe.db.exists("Dashboard Chart", CLIENT_PORTAL_VIEWS_CHART):
		frappe.db.set_value(
			"Dashboard Chart",
			CLIENT_PORTAL_VIEWS_CHART,
			chart_values,
			update_modified=False,
		)
	else:
		chart_doc = frappe.get_doc(
			{
				"doctype": "Dashboard Chart",
				"name": CLIENT_PORTAL_VIEWS_CHART,
				"chart_name": CLIENT_PORTAL_VIEWS_CHART,
				**chart_values,
			}
		)
		chart_doc.insert(ignore_permissions=True)

	chart_doc = frappe.get_doc("Dashboard Chart", CLIENT_PORTAL_VIEWS_CHART)
	desired_roles = [role for role in CLIENT_PORTAL_VIEWS_CHART_ROLES if frappe.db.exists("Role", role)]
	existing_roles = [row.role for row in chart_doc.get("roles", []) if row.role]
	if existing_roles != desired_roles:
		chart_doc.set("roles", [{"role": role} for role in desired_roles])
		chart_doc.save(ignore_permissions=True)

	frappe.cache.delete_key(f"chart-data:{LEGACY_CUSTOMER_PORTAL_VIEWS_CHART}")
	frappe.cache.delete_key(f"chart-data:{CLIENT_PORTAL_VIEWS_CHART}")


def _ensure_non_currency_dashboard_charts() -> None:
	"""Keep count charts numeric without currency formatting."""
	for chart_name in (CLIENT_PORTAL_VIEWS_CHART, LOGIN_ACTIVITY_CHART):
		if not frappe.db.exists("Dashboard Chart", chart_name):
			continue
		values = {"currency": ""}
		if chart_name == LOGIN_ACTIVITY_CHART:
			values["filters_json"] = LOGIN_ACTIVITY_FILTERS_JSON
		frappe.db.set_value(
			"Dashboard Chart",
			chart_name,
			values,
			update_modified=False,
		)
		frappe.cache.delete_key(f"chart-data:{chart_name}")


def _ensure_login_activity_chart_roles() -> None:
	"""Ensure Login Activity chart is visible to internal cold-storage desk roles."""
	if not frappe.db.exists("Dashboard Chart", LOGIN_ACTIVITY_CHART):
		return

	desired_roles = [role for role in LOGIN_ACTIVITY_CHART_ROLES if frappe.db.exists("Role", role)]
	existing_roles = frappe.get_all(
		"Has Role",
		filters={
			"parent": LOGIN_ACTIVITY_CHART,
			"parenttype": "Dashboard Chart",
			"parentfield": "roles",
		},
		pluck="role",
		order_by="idx asc",
	)
	if existing_roles == desired_roles:
		return

	frappe.db.delete(
		"Has Role",
		{
			"parent": LOGIN_ACTIVITY_CHART,
			"parenttype": "Dashboard Chart",
			"parentfield": "roles",
		},
	)
	for idx, role in enumerate(desired_roles, start=1):
		frappe.get_doc(
			{
				"doctype": "Has Role",
				"parent": LOGIN_ACTIVITY_CHART,
				"parenttype": "Dashboard Chart",
				"parentfield": "roles",
				"idx": idx,
				"role": role,
			}
		).insert(ignore_permissions=True)
	frappe.clear_cache(doctype="Dashboard Chart")
	frappe.cache.delete_key(f"chart-data:{LOGIN_ACTIVITY_CHART}")


def _ensure_workspace_report_link_and_shortcut(
	workspace,
	*,
	report_name: str,
	label: str,
	shortcut_block_id: str,
	shortcut_color: str = "Blue",
	insert_after_block_id: str | None = None,
) -> bool:
	"""Ensure a report link + shortcut exists and shortcut is rendered in workspace content."""
	if not frappe.db.exists("Report", report_name):
		return False

	updated = False

	has_report_link = any(
		link.type == "Link" and link.link_type == "Report" and link.link_to == report_name
		for link in workspace.get("links", [])
	)
	if not has_report_link:
		workspace.append(
			"links",
			{
				"type": "Link",
				"label": label,
				"link_type": "Report",
				"link_to": report_name,
			},
		)
		updated = True

	has_report_shortcut = any(
		shortcut.type == "Report" and shortcut.link_to == report_name
		for shortcut in workspace.get("shortcuts", [])
	)
	if not has_report_shortcut:
		workspace.append(
			"shortcuts",
			{
				"type": "Report",
				"label": label,
				"link_to": report_name,
				"color": shortcut_color,
			},
		)
		updated = True

	content_blocks = _get_workspace_content_blocks(workspace.content)
	has_shortcut_block = any(
		block.get("type") == "shortcut" and (block.get("data") or {}).get("shortcut_name") == label
		for block in content_blocks
	)
	if not has_shortcut_block:
		insert_at = len(content_blocks)
		if insert_after_block_id:
			anchor_index = next(
				(idx for idx, block in enumerate(content_blocks) if block.get("id") == insert_after_block_id),
				None,
			)
			if anchor_index is not None:
				insert_at = anchor_index + 1
		content_blocks.insert(
			insert_at,
			{
				"id": shortcut_block_id,
				"type": "shortcut",
				"data": {"shortcut_name": label, "col": 3},
			},
		)
		workspace.content = frappe.as_json(content_blocks)
		updated = True

	return updated


def _ensure_workspace_assets() -> None:
	"""Ensure cold storage analytics are visible on the workspace dashboard."""
	if not frappe.db.exists("Workspace", WORKSPACE_NAME):
		return

	workspace = frappe.get_doc("Workspace", WORKSPACE_NAME)
	updated = False

	removed_shortcut_report_names = {
		LIVE_BATCH_STOCK_REPORT,
		LOGIN_ACTIVITY_LOG_REPORT,
		CLIENT_PORTAL_ACCESS_LOG_REPORT,
		LOT_TRACEABILITY_GRAPH_REPORT,
	}
	removed_shortcut_labels = {
		LIVE_BATCH_STOCK_SHORTCUT_LABEL,
		LOGIN_ACTIVITY_LOG_SHORTCUT_LABEL,
		CLIENT_PORTAL_ACCESS_LOG_SHORTCUT_LABEL,
		LOT_TRACEABILITY_GRAPH_SHORTCUT_LABEL,
	}
	removed_shortcut_block_ids = {
		LIVE_BATCH_STOCK_SHORTCUT_BLOCK_ID,
		LOGIN_ACTIVITY_LOG_SHORTCUT_BLOCK_ID,
		CLIENT_PORTAL_ACCESS_LOG_SHORTCUT_BLOCK_ID,
		LOT_TRACEABILITY_GRAPH_SHORTCUT_BLOCK_ID,
	}

	# Remove deprecated dashboard shortcuts from Workspace Shortcut child table.
	for shortcut in list(workspace.get("shortcuts", [])):
		if shortcut.type == "Report" and shortcut.link_to in removed_shortcut_report_names:
			workspace.remove(shortcut)
			updated = True

	# Remove deprecated shortcut blocks from workspace layout content.
	content_blocks = _get_workspace_content_blocks(workspace.content)
	filtered_content_blocks = []
	content_blocks_changed = False
	for block in content_blocks:
		if block.get("type") != "shortcut":
			filtered_content_blocks.append(block)
			continue

		block_id = block.get("id")
		shortcut_name = (block.get("data") or {}).get("shortcut_name")
		if block_id in removed_shortcut_block_ids or shortcut_name in removed_shortcut_labels:
			content_blocks_changed = True
			continue

		filtered_content_blocks.append(block)

	if content_blocks_changed:
		workspace.content = frappe.as_json(filtered_content_blocks)
		updated = True

	# Remove previously-added People Ops links from existing sites.
	people_ops_links = [
		link
		for link in workspace.get("links", [])
		if link.type == "Link"
		and link.link_type == "DocType"
		and (link.link_to in REMOVED_PEOPLE_OPS_DOCTYPES)
	]
	for link in people_ops_links:
		workspace.remove(link)
		updated = True

	legacy_audit_links = [
		link
		for link in workspace.get("links", [])
		if link.type == "Link" and link.link_type == "Report" and link.link_to == LEGACY_AUDIT_TRAIL_REPORT
	]
	for link in legacy_audit_links:
		workspace.remove(link)
		updated = True

	if frappe.db.exists("Dashboard Chart", CLIENT_PORTAL_VIEWS_CHART):
		has_client_portal_chart = False
		for chart in list(workspace.get("charts", [])):
			if chart.chart_name in (
				DEFAULT_WEBPAGE_VIEWS_CHART,
				LEGACY_CUSTOMER_PORTAL_VIEWS_CHART,
			):
				workspace.remove(chart)
				updated = True
				continue

			if chart.chart_name != CLIENT_PORTAL_VIEWS_CHART:
				continue

			if has_client_portal_chart:
				workspace.remove(chart)
				updated = True
				continue

			has_client_portal_chart = True
			if chart.label != CLIENT_PORTAL_VIEWS_CHART:
				chart.label = CLIENT_PORTAL_VIEWS_CHART
				updated = True

		if not has_client_portal_chart:
			workspace.append(
				"charts",
				{
					"label": CLIENT_PORTAL_VIEWS_CHART,
					"chart_name": CLIENT_PORTAL_VIEWS_CHART,
				},
			)
			updated = True

		content_blocks = _get_workspace_content_blocks(workspace.content)
		normalized_blocks = []
		has_client_portal_block = False
		blocks_changed = False

		for block in content_blocks:
			if block.get("type") != "chart":
				normalized_blocks.append(block)
				continue

			data = dict(block.get("data") or {})
			chart_name = data.get("chart_name")
			if chart_name in (
				DEFAULT_WEBPAGE_VIEWS_CHART,
				LEGACY_CUSTOMER_PORTAL_VIEWS_CHART,
			):
				data["chart_name"] = CLIENT_PORTAL_VIEWS_CHART
				chart_name = CLIENT_PORTAL_VIEWS_CHART
				block["data"] = data
				blocks_changed = True

			if chart_name != CLIENT_PORTAL_VIEWS_CHART:
				normalized_blocks.append(block)
				continue

			if has_client_portal_block:
				blocks_changed = True
				continue

			has_client_portal_block = True
			if block.get("id") != CLIENT_PORTAL_VIEWS_CHART_BLOCK_ID:
				block["id"] = CLIENT_PORTAL_VIEWS_CHART_BLOCK_ID
				blocks_changed = True

			if not data.get("col"):
				data["col"] = 6
				block["data"] = data
				blocks_changed = True

			normalized_blocks.append(block)

		if not has_client_portal_block:
			client_portal_block = {
				"id": CLIENT_PORTAL_VIEWS_CHART_BLOCK_ID,
				"type": "chart",
				"data": {"chart_name": CLIENT_PORTAL_VIEWS_CHART, "col": 6},
			}
			login_chart_index = next(
				(
					idx
					for idx, block in enumerate(normalized_blocks)
					if block.get("type") == "chart"
					and (block.get("data") or {}).get("chart_name") == "Login Activity"
				),
				None,
			)
			if login_chart_index is None:
				normalized_blocks.append(client_portal_block)
			else:
				normalized_blocks.insert(login_chart_index + 1, client_portal_block)
			blocks_changed = True

		if blocks_changed:
			workspace.content = frappe.as_json(normalized_blocks)
			updated = True

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

	if frappe.db.exists("Dashboard Chart", NET_MOVEMENT_WATERFALL_CHART):
		has_net_chart = any(
			chart.chart_name == NET_MOVEMENT_WATERFALL_CHART for chart in workspace.get("charts", [])
		)
		if not has_net_chart:
			workspace.append(
				"charts",
				{
					"label": NET_MOVEMENT_WATERFALL_CHART,
					"chart_name": NET_MOVEMENT_WATERFALL_CHART,
				},
			)
			updated = True

		content_blocks = _get_workspace_content_blocks(workspace.content)
		has_net_chart_block = any(
			block.get("type") == "chart"
			and (block.get("data") or {}).get("chart_name") == NET_MOVEMENT_WATERFALL_CHART
			for block in content_blocks
		)
		if not has_net_chart_block:
			net_chart_block = {
				"id": NET_MOVEMENT_WATERFALL_CHART_BLOCK_ID,
				"type": "chart",
				"data": {"chart_name": NET_MOVEMENT_WATERFALL_CHART, "col": 12},
			}
			yearly_chart_index = next(
				(
					idx
					for idx, block in enumerate(content_blocks)
					if block.get("type") == "chart"
					and (block.get("data") or {}).get("chart_name") == "Yearly Inward Outward Trend"
				),
				None,
			)
			if yearly_chart_index is None:
				content_blocks.append(net_chart_block)
			else:
				content_blocks.insert(yearly_chart_index + 1, net_chart_block)

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

	if frappe.db.exists("Report", AUDIT_TRAIL_REPORT):
		has_audit_trail_link = any(
			link.type == "Link" and link.link_type == "Report" and link.link_to == AUDIT_TRAIL_REPORT
			for link in workspace.get("links", [])
		)
		if not has_audit_trail_link:
			workspace.append(
				"links",
				{
					"type": "Link",
					"label": AUDIT_TRAIL_SHORTCUT_LABEL,
					"link_type": "Report",
					"link_to": AUDIT_TRAIL_REPORT,
				},
			)
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
				if block.get("id") == "jXtpNEtdDN" and data.get("number_card_name") == "Total Active Items":
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
	# Remove previously-added People Ops section and links from existing sites.
	cleaned_items = []
	for item in items:
		if (
			item.get("type") == "Section Break"
			and (item.get("label") or "").strip() == PEOPLE_OPS_SECTION_LABEL
		):
			continue
		if (
			item.get("type") == "Link"
			and (item.get("link_type") or "").strip() == "DocType"
			and (item.get("link_to") or "").strip() in REMOVED_PEOPLE_OPS_DOCTYPES
		):
			continue
		cleaned_items.append(item)
	items = cleaned_items
	items_without_legacy_audit = [
		item
		for item in items
		if not (
			item.get("type") == "Link"
			and (item.get("link_type") or "").strip() == "Report"
			and (item.get("link_to") or "").strip() == LEGACY_AUDIT_TRAIL_REPORT
		)
	]
	items_with_required_reports = _ensure_sidebar_link_under_section(
		items_without_legacy_audit,
		section_label=INVENTORY_MOVEMENT_SECTION_LABEL,
		link_type="Report",
		link_to=LIVE_BATCH_STOCK_REPORT,
		label=LIVE_BATCH_STOCK_SHORTCUT_LABEL,
	)
	items_with_required_reports = _ensure_sidebar_link_under_section(
		items_with_required_reports,
		section_label=COMPLIANCE_ACTIVITY_SECTION_LABEL,
		link_type="Report",
		link_to=AUDIT_TRAIL_REPORT,
		label=AUDIT_TRAIL_SHORTCUT_LABEL,
	)
	items_with_required_reports = _ensure_sidebar_link_under_section(
		items_with_required_reports,
		section_label=COMPLIANCE_ACTIVITY_SECTION_LABEL,
		link_type="Report",
		link_to=LOGIN_ACTIVITY_LOG_REPORT,
		label=LOGIN_ACTIVITY_LOG_SHORTCUT_LABEL,
	)
	items_with_required_reports = _ensure_sidebar_link_under_section(
		items_with_required_reports,
		section_label=COMPLIANCE_ACTIVITY_SECTION_LABEL,
		link_type="Report",
		link_to=CLIENT_PORTAL_ACCESS_LOG_REPORT,
		label=CLIENT_PORTAL_ACCESS_LOG_SHORTCUT_LABEL,
	)
	items_with_required_masters = _ensure_sidebar_link_under_section(
		items_with_required_reports,
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
	items_with_required_masters = _apply_sidebar_icons(items_with_required_masters)
	items_with_required_masters = _normalize_sidebar_sections(items_with_required_masters)

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
		"icon": SIDEBAR_ICON_BY_LABEL.get(label, ""),
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
			if item.get("type") == "Section Break" and (item.get("label") or "").strip() == section_label
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


def _apply_sidebar_icons(items: list) -> list:
	"""Apply consistent sidebar icons for better visual hierarchy."""
	for item in items:
		label = (item.get("label") or "").strip()
		desired_icon = SIDEBAR_ICON_BY_LABEL.get(label)
		if not desired_icon:
			continue

		if isinstance(item, dict):
			item["icon"] = desired_icon
		else:
			item.icon = desired_icon

	return items


def _normalize_sidebar_sections(items: list) -> list:
	"""Ensure section headers remain top-level for stable sidebar rendering."""
	for item in items:
		if (item.get("type") or "").strip() != "Section Break":
			continue

		if isinstance(item, dict):
			item["child"] = 0
		else:
			item.child = 0

	return items


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


def _ensure_audit_trail_report_roles() -> None:
	"""Ensure all expected roles can see and run the audit trail report."""
	if not frappe.db.exists("Report", AUDIT_TRAIL_REPORT):
		return

	report = frappe.get_doc("Report", AUDIT_TRAIL_REPORT)
	existing_roles = {row.role for row in report.get("roles", []) if row.role}
	missing_roles = [
		role
		for role in AUDIT_TRAIL_REPORT_ROLES
		if role not in existing_roles and frappe.db.exists("Role", role)
	]
	if not missing_roles:
		return

	for role in missing_roles:
		report.append("roles", {"role": role})

	report.save(ignore_permissions=True)


def _rename_legacy_audit_trail_report() -> None:
	"""Keep audit trail report name import-safe by removing '&' from report document name."""
	if not frappe.db.exists("Report", LEGACY_AUDIT_TRAIL_REPORT):
		return

	if not frappe.db.exists("Report", AUDIT_TRAIL_REPORT):
		frappe.rename_doc("Report", LEGACY_AUDIT_TRAIL_REPORT, AUDIT_TRAIL_REPORT, force=True)
	else:
		try:
			frappe.delete_doc("Report", LEGACY_AUDIT_TRAIL_REPORT, force=1, ignore_permissions=True)
		except Exception:
			frappe.db.set_value(
				"Report",
				LEGACY_AUDIT_TRAIL_REPORT,
				{"disabled": 1},
				update_modified=False,
			)

	frappe.db.sql(
		"""
		update `tabWorkspace Link`
		set link_to = %s
		where link_type = 'Report' and link_to = %s
		""",
		(AUDIT_TRAIL_REPORT, LEGACY_AUDIT_TRAIL_REPORT),
	)
	frappe.db.sql(
		"""
		update `tabWorkspace Sidebar Item`
		set link_to = %s
		where link_type = 'Report' and link_to = %s
		""",
		(AUDIT_TRAIL_REPORT, LEGACY_AUDIT_TRAIL_REPORT),
	)


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


def _read_letter_head_template(relative_path: str) -> str:
	"""Read bundled letter head HTML template from the app directory."""
	template_path = frappe.get_app_path("cold_storage", *relative_path.split("/"))
	return frappe.read_file(template_path)


def _ensure_cold_storage_letter_head() -> None:
	"""Create or update a branded Cold Storage letter head used by print formats."""
	content = _read_letter_head_template(LETTER_HEAD_HEADER_TEMPLATE)
	footer = _read_letter_head_template(LETTER_HEAD_FOOTER_TEMPLATE)

	if frappe.db.exists("Letter Head", LETTER_HEAD_NAME):
		letter_head = frappe.get_doc("Letter Head", LETTER_HEAD_NAME)
		changed = False
		for fieldname, value in (
			("source", "HTML"),
			("footer_source", "HTML"),
			("content", content),
			("footer", footer),
			("disabled", 0),
		):
			if letter_head.get(fieldname) != value:
				letter_head.set(fieldname, value)
				changed = True

		if changed:
			letter_head.save(ignore_permissions=True)
		return

	frappe.get_doc(
		{
			"doctype": "Letter Head",
			"letter_head_name": LETTER_HEAD_NAME,
			"source": "HTML",
			"footer_source": "HTML",
			"content": content,
			"footer": footer,
			"is_default": 0,
			"disabled": 0,
		}
	).insert(ignore_permissions=True)


def after_install() -> None:
	_ensure_default_uom_setting(create_uom_if_missing=True)
	_ensure_cold_storage_letter_head()
	_ensure_website_view_tracking_enabled()
	_ensure_batch_customizations()
	_ensure_dashboard_chart_types()
	_ensure_top_customers_chart_source()
	_ensure_client_portal_views_chart()
	_ensure_non_currency_dashboard_charts()
	_ensure_login_activity_chart_roles()
	_rename_legacy_audit_trail_report()
	_ensure_live_batch_stock_report_roles()
	_ensure_audit_trail_report_roles()
	_ensure_workspace_assets()
	_ensure_workspace_sidebar_assets()
	_sync_role_based_access()


def after_migrate() -> None:
	_ensure_default_uom_setting(create_uom_if_missing=True)
	_ensure_cold_storage_letter_head()
	_ensure_website_view_tracking_enabled()
	_ensure_batch_customizations()
	_ensure_dashboard_chart_types()
	_ensure_top_customers_chart_source()
	_ensure_client_portal_views_chart()
	_ensure_non_currency_dashboard_charts()
	_ensure_login_activity_chart_roles()
	_rename_legacy_audit_trail_report()
	_ensure_live_batch_stock_report_roles()
	_ensure_audit_trail_report_roles()
	_ensure_workspace_assets()
	_ensure_workspace_sidebar_assets()
	_sync_role_based_access()


def _sync_role_based_access() -> None:
	from cold_storage.setup.role_based_access import sync_role_based_access

	sync_role_based_access()
