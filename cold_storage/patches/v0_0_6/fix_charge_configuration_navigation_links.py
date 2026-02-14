# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

LEGACY_DOCTYPE = "Charge Configuration"
TARGET_DOCTYPE = "Cold Storage Settings"


def execute() -> None:
	"""Replace broken child-table navigation links with Cold Storage Settings links."""
	updated_workspace = _fix_workspace_links()
	updated_sidebar = _fix_workspace_sidebar_links()

	if updated_workspace:
		frappe.clear_cache(doctype="Workspace")
	if updated_sidebar:
		frappe.clear_cache(doctype="Workspace Sidebar")


def _fix_workspace_links() -> bool:
	workspace_names = frappe.get_all("Workspace", filters={"module": "Cold Storage"}, pluck="name")
	if not workspace_names:
		return False

	updated_any = False
	for workspace_name in workspace_names:
		workspace = frappe.get_doc("Workspace", workspace_name)
		updated = False
		for link in workspace.get("links", []):
			if (link.get("link_type") or "").strip() != "DocType":
				continue
			if (link.get("link_to") or "").strip() != LEGACY_DOCTYPE:
				continue

			link.link_to = TARGET_DOCTYPE
			if (link.get("label") or "").strip() == LEGACY_DOCTYPE:
				link.label = "Charge Settings"
			updated = True

		if not updated:
			continue

		workspace.save(ignore_permissions=True)
		updated_any = True

	return updated_any


def _fix_workspace_sidebar_links() -> bool:
	sidebar_names = frappe.get_all("Workspace Sidebar", filters={"app": "cold_storage"}, pluck="name")
	if not sidebar_names:
		return False

	updated_any = False
	for sidebar_name in sidebar_names:
		sidebar = frappe.get_doc("Workspace Sidebar", sidebar_name)
		updated = False
		for item in sidebar.get("items", []):
			if (item.get("link_type") or "").strip() != "DocType":
				continue
			if (item.get("link_to") or "").strip() != LEGACY_DOCTYPE:
				continue

			item.link_to = TARGET_DOCTYPE
			if (item.get("label") or "").strip() == LEGACY_DOCTYPE:
				item.label = "Charge Settings"
			updated = True

		if not updated:
			continue

		sidebar.save(ignore_permissions=True)
		updated_any = True

	return updated_any
