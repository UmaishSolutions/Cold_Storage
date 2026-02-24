# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

CLIENT_PORTAL_VIEW_SOURCE_SERVER = "cs-portal-server"
CLIENT_PORTAL_VIEW_SOURCE_API = "cs-portal-api"
CLIENT_PORTAL_VIEW_PATH_DEFAULT = "cs-portal"
CLIENT_PORTAL_VIEW_PATH_FILTER = "%cs-portal%"
CLIENT_PORTAL_VIEWS_CHART = "Client Portal Views"


def log_client_portal_view(source: str, path: str | None = None) -> None:
	"""Insert a cs-portal access row in Web Page View when available."""
	if not _can_track_views():
		return

	view_path = _normalize_path(path)
	referrer = _get_request_header("Referer")
	if referrer:
		referrer = referrer.split("?", 1)[0]

	view = frappe.get_doc(
		{
			"doctype": "Web Page View",
			"path": view_path,
			"referrer": referrer,
			"user_agent": _get_request_header("User-Agent"),
			"source": source,
		}
	)
	view.insert(ignore_permissions=True)
	frappe.cache.delete_key(f"chart-data:{CLIENT_PORTAL_VIEWS_CHART}")


def _can_track_views() -> bool:
	return bool(frappe.db.exists("DocType", "Web Page View"))


def _normalize_path(path: str | None = None) -> str:
	raw_path = path or _get_request_path() or f"/{CLIENT_PORTAL_VIEW_PATH_DEFAULT}"
	view_path = raw_path.split("?", 1)[0]
	if view_path != "/" and view_path.startswith("/"):
		view_path = view_path[1:]
	return view_path or CLIENT_PORTAL_VIEW_PATH_DEFAULT


def _get_request_path() -> str | None:
	try:
		request = getattr(frappe.local, "request", None)
	except Exception:
		return None
	return getattr(request, "path", None) if request else None


def _get_request_header(header_name: str) -> str | None:
	if not _get_request_path():
		return None
	return frappe.get_request_header(header_name)
