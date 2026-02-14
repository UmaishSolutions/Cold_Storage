# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


def execute() -> None:
	"""Fix cold storage sidebar dashboard links to route to the workspace."""
	sidebar_names = frappe.get_all(
		"Workspace Sidebar",
		filters={"app": "cold_storage"},
		pluck="name",
	)
	if not sidebar_names:
		return

	updated_any = False
	for sidebar_name in sidebar_names:
		sidebar = frappe.get_doc("Workspace Sidebar", sidebar_name)
		updated = False
		for item in sidebar.get("items", []):
			if (item.get("label") or "").strip() != "Dashboard":
				continue
			if (item.get("link_type") or "").strip() != "Dashboard":
				continue
			if (item.get("link_to") or "").strip() not in {
				"Cold Storage",
				"Dashboard Cold Storage",
			}:
				continue

			item.link_type = "Workspace"
			item.link_to = "Cold Storage"
			updated = True

		if not updated:
			continue

		sidebar.save(ignore_permissions=True)
		updated_any = True

	if updated_any:
		frappe.clear_cache(doctype="Workspace Sidebar")
