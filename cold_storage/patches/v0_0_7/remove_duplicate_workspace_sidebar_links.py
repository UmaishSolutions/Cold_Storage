# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


def execute() -> None:
	"""Remove duplicate navigation links from Cold Storage workspace sidebars."""
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
		seen_link_targets: set[tuple[str, str, str]] = set()
		filtered_items = []
		updated = False

		for item in sidebar.get("items", []):
			item_type = (item.get("type") or "").strip()
			link_type = (item.get("link_type") or "").strip()
			link_to = (item.get("link_to") or "").strip()

			# Only dedupe actionable links; keep section headings as-is.
			if item_type != "Link" or not link_type or not link_to:
				filtered_items.append(item)
				continue

			key = (item_type, link_type, link_to)
			if key in seen_link_targets:
				updated = True
				continue

			seen_link_targets.add(key)
			filtered_items.append(item)

		if not updated:
			continue

		sidebar.set("items", filtered_items)
		sidebar.save(ignore_permissions=True)
		updated_any = True

	if updated_any:
		frappe.clear_cache(doctype="Workspace Sidebar")
