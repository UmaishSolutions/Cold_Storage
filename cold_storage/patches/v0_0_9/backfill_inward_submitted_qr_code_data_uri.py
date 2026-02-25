# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _


def execute() -> None:
	"""Backfill submit-time QR data URI for already-submitted inward documents."""
	from cold_storage.cold_storage.utils import get_document_sidebar_qr_code_data_uri

	if not frappe.db.has_column("Cold Storage Inward", "submitted_qr_code_data_uri"):
		return

	inward_names = frappe.get_all(
		"Cold Storage Inward",
		filters={"docstatus": 1, "submitted_qr_code_data_uri": ["in", ["", None]]},
		pluck="name",
	)

	for inward_name in inward_names:
		try:
			data_uri = get_document_sidebar_qr_code_data_uri("Cold Storage Inward", inward_name, scale=3)
			if not data_uri:
				continue
			frappe.db.set_value(
				"Cold Storage Inward",
				inward_name,
				"submitted_qr_code_data_uri",
				data_uri,
				update_modified=False,
			)
		except Exception:
			frappe.log_error(
				title=_("Cold Storage Inward QR Backfill Failed"),
				message=frappe.get_traceback(),
			)

