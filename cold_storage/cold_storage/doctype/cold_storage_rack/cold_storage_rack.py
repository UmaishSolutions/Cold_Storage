# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr


class ColdStorageRack(Document):
	# begin: auto-generated types
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link | None
		is_active: DF.Check
		notes: DF.SmallText | None
		rack_code: DF.Data
		warehouse: DF.Link
	# end: auto-generated types

	def validate(self) -> None:
		self.rack_code = cstr(self.rack_code).strip().upper()
		if not self.rack_code:
			frappe.throw(_("Rack Code is required"))


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def search_active_racks_for_warehouse(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict | None = None,
) -> list[tuple[str]]:
	"""Search active racks by warehouse and rack code."""
	del doctype, searchfield
	filters = filters or {}
	warehouse = cstr(filters.get("warehouse")).strip()
	if not warehouse:
		return []

	return frappe.db.sql(
		"""
		select csr.name
		from `tabCold Storage Rack` csr
		where csr.warehouse = %(warehouse)s
			and ifnull(csr.is_active, 0) = 1
			and (
				csr.name like %(txt)s
				or ifnull(csr.rack_code, '') like %(txt)s
			)
		order by ifnull(csr.rack_code, csr.name), csr.name
		limit %(start)s, %(page_len)s
		""",
		{
			"warehouse": warehouse,
			"txt": f"%{cstr(txt).strip()}%",
			"start": cint(start or 0),
			"page_len": cint(page_len or 20),
		},
	)


@frappe.whitelist()
def create_racks_for_warehouse(
	warehouse: str,
	count: int,
	*,
	prefix: str = "R-",
	start_from: int = 1,
	digits: int = 3,
) -> dict[str, object]:
	"""Bulk-create rack masters for a given warehouse."""
	if not warehouse:
		frappe.throw(_("Warehouse is required"))

	count = cint(count)
	start_from = cint(start_from) or 1
	digits = max(cint(digits), 1)
	prefix = cstr(prefix).strip() or "R-"

	if count <= 0:
		frappe.throw(_("Count must be greater than 0"))

	frappe.only_for(("System Manager", "Stock Manager"))

	created: list[str] = []
	skipped_existing = 0
	for offset in range(count):
		number = start_from + offset
		rack_code = f"{prefix}{number:0{digits}d}"
		if frappe.db.exists("Cold Storage Rack", rack_code):
			skipped_existing += 1
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Cold Storage Rack",
				"warehouse": warehouse,
				"rack_code": rack_code,
				"is_active": 1,
			}
		)
		doc.insert(ignore_permissions=True)
		created.append(doc.name)

	return {
		"warehouse": warehouse,
		"created_count": len(created),
		"skipped_existing_count": skipped_existing,
		"created": created,
	}


def normalize_rack_document_names() -> dict[str, int]:
	"""Rename legacy rack documents so name is exactly rack_code."""
	if not frappe.db.exists("DocType", "Cold Storage Rack"):
		return {"renamed": 0, "skipped": 0}

	rows = frappe.get_all(
		"Cold Storage Rack",
		fields=["name", "rack_code"],
		limit_page_length=0,
	)

	renamed = 0
	skipped = 0
	for row in rows:
		current_name = cstr(row.get("name")).strip()
		rack_code = cstr(row.get("rack_code")).strip().upper()
		if not current_name or not rack_code or current_name == rack_code:
			continue

		if frappe.db.exists("Cold Storage Rack", rack_code):
			skipped += 1
			continue

		frappe.rename_doc("Cold Storage Rack", current_name, rack_code, force=True)
		renamed += 1

	return {"renamed": renamed, "skipped": skipped}
