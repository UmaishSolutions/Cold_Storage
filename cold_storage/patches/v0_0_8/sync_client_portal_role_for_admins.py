# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.utils import cint


def execute() -> None:
	"""Ensure Cold Storage admins also carry the portal role."""
	from cold_storage.setup.role_based_access import sync_role_based_access

	sync_role_based_access()

	admin_users = frappe.get_all(
		"Has Role",
		filters={"role": "Cold Storage Admin", "parenttype": "User"},
		pluck="parent",
	)

	for user in sorted(set(admin_users)):
		if not user or user == "Guest":
			continue
		if not frappe.db.exists("User", user):
			continue
		if not cint(frappe.db.get_value("User", user, "enabled")):
			continue
		if frappe.db.exists(
			"Has Role",
			{
				"parenttype": "User",
				"parent": user,
				"role": "Cold Storage Client Portal User",
			},
		):
			continue

		user_doc = frappe.get_doc("User", user)
		user_doc.append("roles", {"role": "Cold Storage Client Portal User"})
		user_doc.save(ignore_permissions=True)

	frappe.clear_cache()
