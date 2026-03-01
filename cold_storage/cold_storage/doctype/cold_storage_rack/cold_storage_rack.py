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
		name = f"{warehouse}-{rack_code}"
		if frappe.db.exists("Cold Storage Rack", name):
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
