# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def get_permissions_matrix() -> dict:
	"""Return the complete role-permission matrix for all Cold Storage doctypes."""

	# All CS-relevant roles
	cs_roles = [
		"System Manager",
		"Stock Manager",
		"Cold Storage Admin",
		"Cold Storage Warehouse Manager",
		"Cold Storage Inbound Operator",
		"Cold Storage Dispatch Operator",
		"Cold Storage Inventory Controller",
		"Cold Storage Billing Executive",
		"Cold Storage Quality Inspector",
		"Cold Storage Maintenance Technician",
		"Cold Storage Client Portal User",
	]

	# All CS doctypes grouped by category
	doctype_groups = {
		"Configuration": [
			"Cold Storage Settings",
			"Charge Configuration",
		],
		"Inward / Storage": [
			"Cold Storage Inward",
		],
		"Outward / Dispatch": [
			"Cold Storage Outward",
		],
		"Transfer": [
			"Cold Storage Transfer",
		],
	}

	perm_types = [
		"read", "write", "create", "delete",
		"submit", "cancel", "amend",
		"report", "export", "print", "share", "email",
	]

	# Fetch permissions from DocType meta
	matrix = {}
	for group, doctypes in doctype_groups.items():
		for dt in doctypes:
			try:
				meta = frappe.get_meta(dt)
			except Exception:
				continue

			dt_perms = {}
			for role in cs_roles:
				role_perm = {"has_access": False}
				for perm in meta.permissions:
					if perm.role == role:
						role_perm["has_access"] = True
						for pt in perm_types:
							if perm.get(pt):
								role_perm[pt] = 1
				dt_perms[role] = role_perm

			matrix[dt] = {
				"group": group,
				"is_submittable": bool(meta.is_submittable),
				"permissions": dt_perms,
			}

	# --- Portal access summary ---
	# The CS Client Portal is an API-driven portal (cs-portal) where
	# Cold Storage Client Portal User gets customer-scoped access.
	portal_access = [
		{
			"feature": "Dashboard",
			"description": "View current stock, recent movements, and outstanding invoices",
			"api": "get_portal_dashboard",
			"access": "Read (customer-scoped)",
		},
		{
			"feature": "Batch Details",
			"description": "View batch-wise stock details with quantities and locations",
			"api": "get_batch_stock_details",
			"access": "Read (customer-scoped)",
		},
		{
			"feature": "Movement History",
			"description": "View inward, outward, and transfer history",
			"api": "get_movement_history",
			"access": "Read (customer-scoped)",
		},
		{
			"feature": "Outstanding Invoices",
			"description": "View unpaid invoices and payment history",
			"api": "get_invoices",
			"access": "Read (customer-scoped)",
		},
		{
			"feature": "Reports (PDF)",
			"description": "Download customer-scoped reports as PDF",
			"api": "download_portal_report_pdf",
			"access": "Read + Export (customer-scoped)",
		},
		{
			"feature": "Product Brochure",
			"description": "Download the Cold Storage brochure PDF",
			"api": "get_brochure_pdf",
			"access": "Read",
		},
		{
			"feature": "Settings (Announcement)",
			"description": "View portal announcements set by admin",
			"api": "get_portal_dashboard",
			"access": "Read (filtered)",
		},
	]

	return {
		"roles": cs_roles,
		"perm_types": perm_types,
		"doctype_groups": doctype_groups,
		"matrix": matrix,
		"portal_access": portal_access,
	}


@frappe.whitelist()
def update_permission(doctype: str, role: str, perm_type: str, value: int) -> None:
	"""Update a single permission for a role on a Cold Storage doctype."""
	frappe.only_for("System Manager")

	meta = frappe.get_meta(doctype)
	perm_row = None
	for perm in meta.permissions:
		if perm.role == role:
			perm_row = perm
			break

	if value and not perm_row:
		doc = frappe.get_doc("DocType", doctype)
		doc.append("permissions", {
			"role": role,
			perm_type: 1,
			"read": 1,
		})
		doc.save()
		frappe.msgprint(_(f"Added {role} to {doctype} with {perm_type} permission"), alert=True)
	elif perm_row:
		frappe.db.set_value("DocPerm", perm_row.name, perm_type, value)
		frappe.clear_cache(doctype=doctype)
		frappe.msgprint(_(f"Updated {perm_type} for {role} on {doctype}"), alert=True)
