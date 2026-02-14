# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ColdStorageInwardItem(Document):
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		available_qty: DF.Float
		amount: DF.Currency
		batch_no: DF.Link | None
		item: DF.Link | None
		item_group: DF.Link | None
		item_name: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		qty: DF.Float
		unloading_rate: DF.Currency
		uom: DF.Link | None
		warehouse: DF.Link | None

	pass
