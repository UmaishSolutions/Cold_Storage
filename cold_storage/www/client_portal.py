# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _

from cold_storage.client_portal_views import (
	CLIENT_PORTAL_VIEW_SOURCE_SERVER,
	log_client_portal_view,
)
from cold_storage.setup.client_portal_user_permissions import CLIENT_PORTAL_ROLE

ADMIN_ROLE = "Cold Storage Admin"


def get_context(context: dict) -> None:
	context.no_cache = 1
	context.show_sidebar = False
	context.full_width = True
	context.title = _("Cold Storage Client Portal")
	context.no_breadcrumbs = 1

	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to access the client portal"), frappe.PermissionError)

	roles = set(frappe.get_roles())
	if "System Manager" in roles:
		_log_client_portal_access()
		return
	if CLIENT_PORTAL_ROLE not in roles and ADMIN_ROLE not in roles:
		frappe.throw(_("You are not allowed to access the client portal"), frappe.PermissionError)

	_log_client_portal_access()


def _log_client_portal_access() -> None:
	"""Write a deterministic view-log row for client-portal page loads."""
	try:
		log_client_portal_view(source=CLIENT_PORTAL_VIEW_SOURCE_SERVER)
	except Exception:
		# Never block portal rendering due to analytics logging.
		frappe.log_error(frappe.get_traceback(), "Client Portal View Logging Failed")
