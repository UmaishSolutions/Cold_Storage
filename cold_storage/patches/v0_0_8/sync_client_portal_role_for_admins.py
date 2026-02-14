# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.utils import cint

from cold_storage.setup.client_portal_user_permissions import CLIENT_PORTAL_ROLE
from cold_storage.setup.role_based_access import sync_role_based_access

ADMIN_ROLE = "Cold Storage Admin"


def execute() -> None:
	"""Ensure Cold Storage admins also have the client portal role."""
	sync_role_based_access()

	admin_users = frappe.get_all(
		"Has Role",
		filters={"role": ADMIN_ROLE, "parenttype": "User"},
		pluck="parent",
	)
	if not admin_users:
		return

	for user_id in sorted(set(admin_users)):
		if not frappe.db.exists("User", user_id):
			continue

		enabled = cint(frappe.db.get_value("User", user_id, "enabled") or 0)
		if not enabled:
			continue

		if CLIENT_PORTAL_ROLE in set(frappe.get_roles(user_id)):
			continue

		user = frappe.get_doc("User", user_id)
		user.append("roles", {"role": CLIENT_PORTAL_ROLE})
		user.save(ignore_permissions=True)

	frappe.clear_cache()
