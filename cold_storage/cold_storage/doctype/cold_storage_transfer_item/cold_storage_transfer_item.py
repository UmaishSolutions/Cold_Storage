# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ColdStorageTransferItem(Document):
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
		source_rack: DF.Data | None
		source_warehouse: DF.Link | None
		target_rack: DF.Data | None
		target_warehouse: DF.Link | None
		transfer_rate: DF.Currency
		uom: DF.Link | None

	pass
