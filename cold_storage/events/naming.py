# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.naming import make_autoname
from frappe.utils import cstr

from cold_storage.cold_storage.naming import (
	get_company_abbreviation,
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


CHILD_DOCTYPE_TOKEN = {
	"Cold Storage Inward Item": "CS-INI",
	"Cold Storage Outward Item": "CS-OUTI",
	"Cold Storage Transfer Item": "CS-TRI",
	"Charge Configuration": "CS-CHG",
}


def autoname_cold_storage_child_doctype(doc, method: str | None = None) -> None:
	"""Apply company-abbreviation prefix for cold storage child doctypes."""
	del method

	if doc.get("name"):
		return

	token = CHILD_DOCTYPE_TOKEN.get(cstr(doc.doctype).strip())
	if not token:
		return

	company = _resolve_company_for_child_doc(doc)
	if not company:
		return

	abbr = get_company_abbreviation(company)
	doc.name = f"{abbr}-{token}-{frappe.generate_hash(length=8).upper()}"


def _resolve_company_for_child_doc(doc) -> str:
	"""Resolve company from parent document context for child rows."""
	parenttype = cstr(doc.get("parenttype")).strip()
	parent = cstr(doc.get("parent")).strip()

	if parenttype in {"Cold Storage Inward", "Cold Storage Outward", "Cold Storage Transfer"} and parent:
		return cstr(frappe.db.get_value(parenttype, parent, "company") or "").strip()

	if parenttype == "Cold Storage Settings":
		return cstr(frappe.db.get_single_value("Cold Storage Settings", "company") or "").strip()

	return ""
