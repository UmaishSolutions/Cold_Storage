# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ColdStorageDispatchExtraCharge(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		charge_name: DF.Data
		charge_description: DF.SmallText
		charge_rate: DF.Currency
		credit_account: DF.Link
		is_active: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types

	pass
