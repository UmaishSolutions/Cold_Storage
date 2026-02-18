# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.naming import make_autoname
from frappe.utils import cstr

from cold_storage.cold_storage.naming import (
	get_series_for_company,
	is_cold_storage_prefixed_voucher,
)


def autoname_cold_storage_gl_entry(doc, method: str | None = None) -> None:
	"""Apply company-prefixed GL Entry names only for cold-storage generated vouchers."""
	del method

	if doc.get("name"):
		return

	voucher_type = cstr(doc.get("voucher_type")).strip()
	if voucher_type not in {"Stock Entry", "Sales Invoice", "Journal Entry"}:
		return

	company = cstr(doc.get("company")).strip()
	voucher_no = cstr(doc.get("voucher_no")).strip()
	if not company or not voucher_no:
		return

	if not is_cold_storage_prefixed_voucher(voucher_no, company):
		return

	doc.name = make_autoname(f"{get_series_for_company('gl_entry', company)}.#####", doc=doc)
