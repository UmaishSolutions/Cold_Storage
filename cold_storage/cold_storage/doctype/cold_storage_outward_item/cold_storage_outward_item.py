# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ColdStorageOutwardItem(Document):
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		available_qty: DF.Float
		amount: DF.Currency
		batch_no: DF.Link | None
		handling_rate: DF.Currency
		item: DF.Link | None
		item_group: DF.Link | None
		item_name: DF.Data | None
		loading_rate: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		qty: DF.Float
		rack: DF.Data | None
		uom: DF.Link | None
		warehouse: DF.Link | None

	pass
