# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def validate_batch_customer(doc: "frappe.types.Document", method: str | None = None) -> None:
	"""Validate that the (Batch ID, Customer) combination is logically unique.

	Different customers can share the same batch_id string, but within
	the Frappe Batch DocType (which is unique by name), we track ownership
	via the custom_customer field.
	"""
	customer = doc.get("custom_customer")
	if not customer:
		return

	# Nothing to validate if customer hasn't changed
	if not doc.is_new() and not doc.has_value_changed("custom_customer"):
		return

	# Warn if changing ownership outside of a Cold Storage Transfer
	if not doc.is_new() and doc.has_value_changed("custom_customer"):
		old_customer = doc.get_doc_before_save().get("custom_customer") if doc.get_doc_before_save() else None
		if old_customer and old_customer != customer:
			frappe.msgprint(
				_("Batch {0} ownership changed from {1} to {2}").format(
					doc.batch_id, old_customer, customer
				),
				alert=True,
			)
