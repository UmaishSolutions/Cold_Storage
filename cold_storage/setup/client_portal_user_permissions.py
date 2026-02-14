# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe.utils import cint


CLIENT_PORTAL_ROLE = "Cold Storage Client Portal User"


def sync_customer_user_permissions_for_client_portal_users() -> None:
	"""Backfill missing customer permissions for all cold-storage client portal users."""
	user_customer_map = _get_user_customer_map()
	for user, customers in user_customer_map.items():
		_create_missing_customer_permissions(user, customers)


def get_customers_for_portal_user(user: str | None = None) -> list[str]:
	"""Return sorted customer list mapped to a portal user."""
	user_id = user or frappe.session.user
	if not user_id:
		return []
	return sorted(_get_customers_for_user(user_id))


def sync_customer_user_permissions_for_customer(doc, method: str | None = None) -> None:
	"""Create missing customer permissions for portal users linked to this customer."""
	customer = getattr(doc, "name", None)
	if not customer:
		return

	portal_users = {
		row.user for row in (doc.get("portal_users") or []) if getattr(row, "user", None)
	}
	for user in sorted(portal_users):
		if not _is_active_user(user):
			continue
		if CLIENT_PORTAL_ROLE not in frappe.get_roles(user):
			continue
		_create_missing_customer_permissions(user, {customer})


def _get_user_customer_map() -> dict[str, set[str]]:
	user_customer_map: dict[str, set[str]] = defaultdict(set)
	for user in _get_client_portal_users():
		if not _is_active_user(user):
			continue

		customers = _get_customers_for_user(user)
		if not customers:
			continue

		user_customer_map[user].update(customers)

	return user_customer_map


def _get_client_portal_users() -> list[str]:
	users = frappe.get_all(
		"Has Role",
		filters={"role": CLIENT_PORTAL_ROLE, "parenttype": "User"},
		pluck="parent",
	)
	return [user for user in users if user]


def _is_active_user(user: str) -> bool:
	if not frappe.db.exists("User", user):
		return False
	return bool(cint(frappe.db.get_value("User", user, "enabled")))


def _get_customers_for_user(user: str) -> set[str]:
	customers: set[str] = set()

	# Primary mapping: Customer > portal_users child table.
	customers.update(
		frappe.get_all(
			"Portal User",
			filters={"parenttype": "Customer", "user": user},
			pluck="parent",
		)
	)

	# Fallback: Customer.email_id.
	customers.update(frappe.get_all("Customer", filters={"email_id": user}, pluck="name"))

	# Fallback: Contact email linked to Customer through Dynamic Link.
	contact_names = frappe.get_all(
		"Contact Email",
		filters={"parenttype": "Contact", "email_id": user},
		pluck="parent",
	)
	if contact_names:
		customers.update(
			frappe.get_all(
				"Dynamic Link",
				filters={
					"parenttype": "Contact",
					"parent": ["in", contact_names],
					"link_doctype": "Customer",
				},
				pluck="link_name",
			)
		)

	return {customer for customer in customers if customer}


def _create_missing_customer_permissions(user: str, customers: set[str]) -> None:
	existing_perms = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "Customer"},
		fields=["for_value", "is_default"],
	)
	existing_customer_values = {row.for_value for row in existing_perms if row.for_value}
	has_default_customer_perm = any(cint(row.is_default) for row in existing_perms)
	should_mark_default = len(customers) == 1 and not has_default_customer_perm

	for customer in sorted(customers):
		if customer in existing_customer_values:
			continue

		user_perm = frappe.new_doc("User Permission")
		user_perm.user = user
		user_perm.allow = "Customer"
		user_perm.for_value = customer
		user_perm.apply_to_all_doctypes = 1
		if should_mark_default:
			user_perm.is_default = 1
			should_mark_default = False
		user_perm.insert(ignore_permissions=True)
