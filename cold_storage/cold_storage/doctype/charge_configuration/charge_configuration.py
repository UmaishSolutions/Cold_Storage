# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ChargeConfiguration(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		handling_rate: DF.Currency
		inter_warehouse_transfer_rate: DF.Currency
		intra_warehouse_transfer_rate: DF.Currency
		item_group: DF.Link | None
		loading_rate: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		unloading_rate: DF.Currency
	# end: auto-generated types

	pass
