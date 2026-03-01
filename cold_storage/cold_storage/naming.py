# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from typing import Final

import frappe
from frappe import _
from frappe.utils import cstr

SERIES_KEY_TO_TOKEN: Final[dict[str, str]] = {
	"inward": "CS-IN",
	"outward": "CS-OUT",
	"transfer": "CS-TR",
	"stock_entry": "CS-STE",
	"sales_invoice": "CS-SINV",
	"journal_entry": "CS-JV",
	"gl_entry": "CS-GLE",
}


def get_company_abbreviation(company: str) -> str:
	"""Return a safe uppercase company abbreviation used in naming series."""
	abbr = cstr(frappe.get_cached_value("Company", company, "abbr") or "").strip()
	if not abbr:
		abbr = cstr(company).strip()

	safe_abbr = re.sub(r"[^A-Za-z0-9]", "", abbr).upper()
	return safe_abbr or "CO"


def get_series_for_company(series_key: str, company: str) -> str:
	"""Build company-prefixed naming series template for cold storage docs."""
	series_token = SERIES_KEY_TO_TOKEN.get(series_key)
	if not series_token:
		frappe.throw(_("Unsupported naming series key: {0}").format(series_key))

	return f"{get_company_abbreviation(company)}-{series_token}-.YYYY.-.####"


def is_cold_storage_prefixed_voucher(voucher_no: str, company: str) -> bool:
	"""Return True when voucher belongs to the cold-storage naming namespace."""
	abbr = get_company_abbreviation(company)
	return cstr(voucher_no).strip().startswith(f"{abbr}-CS-")
