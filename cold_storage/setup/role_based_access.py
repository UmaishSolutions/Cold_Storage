# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Final

import frappe
from frappe.permissions import reset_perms
from frappe.utils import cint

PERMISSION_FIELDS: Final[tuple[str, ...]] = (
	"select",
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
	"if_owner",
)

ROLE_DEFINITIONS: Final[dict[str, dict[str, int]]] = {
	"Cold Storage Admin": {"desk_access": 1},
	"Cold Storage Warehouse Manager": {"desk_access": 1},
	"Cold Storage Inbound Operator": {"desk_access": 1},
	"Cold Storage Dispatch Operator": {"desk_access": 1},
	"Cold Storage Inventory Controller": {"desk_access": 1},
	"Cold Storage Billing Executive": {"desk_access": 1},
	"Cold Storage Client Portal User": {"desk_access": 0},
	"Cold Storage Quality Inspector": {"desk_access": 1},
	"Cold Storage Maintenance Technician": {"desk_access": 1},
}

ACTIVITY_LOG_ACCESS_ROLES: Final[tuple[str, ...]] = (
	"Cold Storage Admin",
	"Cold Storage Warehouse Manager",
	"Cold Storage Inbound Operator",
	"Cold Storage Dispatch Operator",
	"Cold Storage Inventory Controller",
	"Cold Storage Billing Executive",
	"Stock Manager",
	"Stock User",
)

WEB_PAGE_VIEW_ACCESS_ROLES: Final[tuple[str, ...]] = (
	"Cold Storage Admin",
	"Cold Storage Warehouse Manager",
	"Cold Storage Inbound Operator",
	"Cold Storage Dispatch Operator",
	"Cold Storage Inventory Controller",
	"Cold Storage Billing Executive",
	"Stock Manager",
	"Stock User",
)

ROLE_PROFILES: Final[dict[str, list[str]]] = {
	"Cold Storage Admin Profile": [
		"System Manager",
		"Stock Manager",
		"Accounts Manager",
		"Cold Storage Admin",
		"Cold Storage Warehouse Manager",
		"Cold Storage Billing Executive",
		"Cold Storage Inventory Controller",
		"Cold Storage Client Portal User",
	],
	"Cold Storage Warehouse Manager Profile": [
		"Stock Manager",
		"Accounts User",
		"Cold Storage Warehouse Manager",
	],
	"Cold Storage Inbound Desk Profile": [
		"Stock User",
		"Cold Storage Inbound Operator",
	],
	"Cold Storage Dispatch Desk Profile": [
		"Stock User",
		"Cold Storage Dispatch Operator",
	],
	"Cold Storage Inventory Control Profile": [
		"Stock User",
		"Cold Storage Inventory Controller",
	],
	"Cold Storage Billing Desk Profile": [
		"Accounts User",
		"Cold Storage Billing Executive",
	],
	"Cold Storage Client Portal Profile": [
		"Customer",
		"Cold Storage Client Portal User",
	],
}

DOCTYPE_PERMISSIONS: Final[dict[str, list[dict[str, int | str]]]] = {
	"Charge Configuration": [
		{
			"role": "System Manager",
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"delete": 1,
			"report": 1,
			"export": 1,
			"share": 1,
			"print": 1,
			"email": 1,
		},
		{
			"role": "Cold Storage Admin",
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"delete": 1,
			"print": 1,
			"email": 1,
		},
		{
			"role": "Cold Storage Warehouse Manager",
			"select": 1,
			"read": 1,
		},
		{
			"role": "Cold Storage Billing Executive",
			"select": 1,
			"read": 1,
		},
	],
	"Cold Storage Settings": [
		{
			"role": "System Manager",
			"create": 1,
			"delete": 1,
			"read": 1,
			"write": 1,
			"print": 1,
			"email": 1,
			"share": 1,
		},
		{
			"role": "Cold Storage Admin",
			"read": 1,
			"write": 1,
		},
		{
			"role": "Cold Storage Warehouse Manager",
			"read": 1,
		},
		{
			"role": "Cold Storage Billing Executive",
			"read": 1,
		},
	],
	"Web Page View": [
		{
			"role": role,
			"select": 1,
			"read": 1,
			"report": 1,
		}
		for role in WEB_PAGE_VIEW_ACCESS_ROLES
	],
	"Cold Storage Inward": [
		{
			"role": "System Manager",
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"delete": 1,
			"submit": 1,
			"cancel": 1,
			"amend": 1,
			"report": 1,
			"export": 1,
			"share": 1,
			"print": 1,
			"email": 1,
		},
		{
			"role": "Cold Storage Admin",
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"submit": 1,
			"cancel": 1,
			"amend": 1,
			"report": 1,
			"export": 1,
			"share": 1,
			"print": 1,
			"email": 1,
		},
		{
			"role": "Cold Storage Inbound Operator",
			"if_owner": 1,
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"print": 1,
			"email": 1,
		},
		{
			"role": "Cold Storage Warehouse Manager",
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"submit": 1,
			"cancel": 1,
			"amend": 1,
			"report": 1,
			"export": 1,
			"share": 1,
			"print": 1,
			"email": 1,
		},
		{
			"role": "Cold Storage Inventory Controller",
			"select": 1,
			"read": 1,
			"report": 1,
			"export": 1,
			"print": 1,
		},
		{
			"role": "Cold Storage Billing Executive",
			"select": 1,
			"read": 1,
			"report": 1,
			"export": 1,
			"print": 1,
		},
		{
			"role": "Cold Storage Client Portal User",
			"select": 1,
			"read": 1,
			"print": 1,
		},
	],
	"Cold Storage Outward": [
		{
			"role": "System Manager",
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"delete": 1,
			"submit": 1,
			"cancel": 1,
			"amend": 1,
			"report": 1,
			"export": 1,
			"share": 1,
			"print": 1,
			"email": 1,
		},
		{
			"role": "Cold Storage Admin",
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"submit": 1,
			"cancel": 1,
			"amend": 1,
			"report": 1,
			"export": 1,
			"share": 1,
			"print": 1,
			"email": 1,
		},
		{
			"role": "Cold Storage Dispatch Operator",
			"if_owner": 1,
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"print": 1,
			"email": 1,
		},
		{
			"role": "Cold Storage Warehouse Manager",
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"submit": 1,
			"cancel": 1,
			"amend": 1,
			"report": 1,
			"export": 1,
			"share": 1,
			"print": 1,
			"email": 1,
		},
		{
			"role": "Cold Storage Inventory Controller",
			"select": 1,
			"read": 1,
			"report": 1,
			"export": 1,
			"print": 1,
		},
		{
			"role": "Cold Storage Billing Executive",
			"select": 1,
			"read": 1,
			"report": 1,
			"export": 1,
			"print": 1,
		},
		{
			"role": "Cold Storage Client Portal User",
			"select": 1,
			"read": 1,
			"print": 1,
		},
	],
	"Cold Storage Transfer": [
		{
			"role": "System Manager",
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"delete": 1,
			"submit": 1,
			"cancel": 1,
			"amend": 1,
			"report": 1,
			"export": 1,
			"share": 1,
			"print": 1,
			"email": 1,
		},
		{
			"role": "Cold Storage Admin",
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"submit": 1,
			"cancel": 1,
			"amend": 1,
			"report": 1,
			"export": 1,
			"share": 1,
			"print": 1,
			"email": 1,
		},
		{
			"role": "Cold Storage Inventory Controller",
			"if_owner": 1,
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"print": 1,
			"email": 1,
		},
		{
			"role": "Cold Storage Warehouse Manager",
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"submit": 1,
			"cancel": 1,
			"amend": 1,
			"report": 1,
			"export": 1,
			"share": 1,
			"print": 1,
			"email": 1,
		},
		{
			"role": "Cold Storage Dispatch Operator",
			"select": 1,
			"read": 1,
			"print": 1,
		},
		{
			"role": "Cold Storage Billing Executive",
			"select": 1,
			"read": 1,
			"report": 1,
			"export": 1,
			"print": 1,
		},
		{
			"role": "Cold Storage Client Portal User",
			"select": 1,
			"read": 1,
			"print": 1,
		},
	],
}

REPORT_ROLES: Final[dict[str, list[str]]] = {
	"Cold Storage Inward Register": [
		"System Manager",
		"Cold Storage Admin",
		"Cold Storage Warehouse Manager",
		"Cold Storage Inbound Operator",
		"Cold Storage Inventory Controller",
		"Cold Storage Billing Executive",
		"Cold Storage Client Portal User",
	],
	"Cold Storage Outward Register": [
		"System Manager",
		"Cold Storage Admin",
		"Cold Storage Warehouse Manager",
		"Cold Storage Dispatch Operator",
		"Cold Storage Inventory Controller",
		"Cold Storage Billing Executive",
		"Cold Storage Client Portal User",
	],
	"Cold Storage Transfer Register": [
		"System Manager",
		"Cold Storage Admin",
		"Cold Storage Warehouse Manager",
		"Cold Storage Inventory Controller",
		"Cold Storage Billing Executive",
		"Cold Storage Dispatch Operator",
		"Cold Storage Client Portal User",
	],
	"Cold Storage Warehouse Utilization": [
		"System Manager",
		"Cold Storage Admin",
		"Cold Storage Warehouse Manager",
		"Cold Storage Inventory Controller",
	],
	"Cold Storage Warehouse Occupancy Timeline": [
		"System Manager",
		"Cold Storage Admin",
		"Cold Storage Warehouse Manager",
		"Cold Storage Inventory Controller",
	],
	"Cold Storage Yearly Inward Outward Trend": [
		"System Manager",
		"Cold Storage Admin",
		"Cold Storage Warehouse Manager",
		"Cold Storage Inventory Controller",
		"Cold Storage Billing Executive",
	],
	"Cold Storage Net Movement Waterfall Monthly": [
		"System Manager",
		"Cold Storage Admin",
		"Cold Storage Warehouse Manager",
		"Cold Storage Inventory Controller",
		"Cold Storage Billing Executive",
	],
	"Cold Storage Login Activity Log": [
		"System Manager",
		"Cold Storage Admin",
		"Cold Storage Warehouse Manager",
		"Cold Storage Inbound Operator",
		"Cold Storage Inventory Controller",
		"Cold Storage Billing Executive",
		"Cold Storage Dispatch Operator",
		"Stock Manager",
		"Stock User",
	],
	"Cold Storage Client Portal Access Log": [
		"System Manager",
		"Cold Storage Admin",
		"Cold Storage Warehouse Manager",
		"Cold Storage Inbound Operator",
		"Cold Storage Inventory Controller",
		"Cold Storage Billing Executive",
		"Cold Storage Dispatch Operator",
		"Stock Manager",
		"Stock User",
	],
}


def sync_role_based_access() -> None:
	"""Synchronize roles, role profiles, doctype permissions and report access."""
	_ensure_roles()
	_ensure_role_profiles()
	_sync_doctype_permissions()
	_ensure_activity_log_permissions()
	_sync_report_roles()
	frappe.clear_cache()


def _ensure_roles() -> None:
	for role_name, config in ROLE_DEFINITIONS.items():
		desk_access = cint(config.get("desk_access", 1))

		if frappe.db.exists("Role", role_name):
			role = frappe.get_doc("Role", role_name)
			updated = False
			if cint(role.desk_access) != desk_access:
				role.desk_access = desk_access
				updated = True
			if cint(role.disabled):
				role.disabled = 0
				updated = True
			if updated:
				role.save(ignore_permissions=True)
			continue

		role = frappe.new_doc("Role")
		role.role_name = role_name
		role.desk_access = desk_access
		role.disabled = 0
		role.insert(ignore_permissions=True)


def _ensure_role_profiles() -> None:
	for profile_name, roles in ROLE_PROFILES.items():
		profile = (
			frappe.get_doc("Role Profile", profile_name)
			if frappe.db.exists("Role Profile", profile_name)
			else frappe.new_doc("Role Profile")
		)

		existing_roles = [row.role for row in profile.get("roles", []) if row.role]
		if profile.role_profile == profile_name and existing_roles == roles:
			continue

		profile.role_profile = profile_name
		profile.set("roles", [])
		for role in roles:
			profile.append("roles", {"role": role})

		if profile.is_new():
			profile.insert(ignore_permissions=True)
		else:
			profile.save(ignore_permissions=True)


def _sync_doctype_permissions() -> None:
	from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype

	for doctype, permission_rows in DOCTYPE_PERMISSIONS.items():
		if not frappe.db.exists("DocType", doctype):
			continue

		reset_perms(doctype)

		for permission in permission_rows:
			custom_perm = frappe.new_doc("Custom DocPerm")
			custom_perm.parent = doctype
			custom_perm.parenttype = "DocType"
			custom_perm.parentfield = "permissions"
			custom_perm.role = permission["role"]
			custom_perm.permlevel = cint(permission.get("permlevel", 0))
			for fieldname in PERMISSION_FIELDS:
				custom_perm.set(fieldname, cint(permission.get(fieldname, 0)))
			custom_perm.insert(ignore_permissions=True)

		validate_permissions_for_doctype(doctype)
		frappe.clear_cache(doctype=doctype)


def _ensure_activity_log_permissions() -> None:
	from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype

	if not frappe.db.exists("DocType", "Activity Log"):
		return

	updated = False
	for role in ACTIVITY_LOG_ACCESS_ROLES:
		existing_name = frappe.db.get_value(
			"Custom DocPerm",
			{
				"parent": "Activity Log",
				"role": role,
				"permlevel": 0,
			},
			"name",
		)
		permission_values = {"select": 1, "read": 1, "report": 1}

		if existing_name:
			current = frappe.db.get_value("Custom DocPerm", existing_name, list(permission_values), as_dict=True) or {}
			if all(cint(current.get(field)) == value for field, value in permission_values.items()):
				continue
			for field, value in permission_values.items():
				frappe.db.set_value("Custom DocPerm", existing_name, field, value, update_modified=False)
			updated = True
			continue

		custom_perm = frappe.new_doc("Custom DocPerm")
		custom_perm.parent = "Activity Log"
		custom_perm.role = role
		custom_perm.permlevel = 0
		for fieldname in PERMISSION_FIELDS:
			custom_perm.set(fieldname, 0)
		for field, value in permission_values.items():
			custom_perm.set(field, value)
		custom_perm.insert(ignore_permissions=True)
		updated = True

	if updated:
		validate_permissions_for_doctype("Activity Log")
		frappe.clear_cache(doctype="Activity Log")


def _sync_report_roles() -> None:
	for report_name, roles in REPORT_ROLES.items():
		if not frappe.db.exists("Report", report_name):
			continue

		report = frappe.get_doc("Report", report_name)
		existing_roles = [row.role for row in report.get("roles", []) if row.role]
		if existing_roles == roles:
			continue

		report.set("roles", [])
		for role in roles:
			report.append("roles", {"role": role})
		report.save(ignore_permissions=True)
