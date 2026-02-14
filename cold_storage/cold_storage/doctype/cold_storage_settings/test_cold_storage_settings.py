# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
	get_default_company,
	get_transfer_rate,
	resolve_default_uom,
	validate_warehouse_company,
)


class TestColdStorageSettingsHelpers(TestCase):
	def test_get_default_company_returns_value(self):
		with patch(
			"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.get_settings",
			return_value=SimpleNamespace(company="Default Co"),
		):
			self.assertEqual(get_default_company(), "Default Co")

	def test_get_default_company_throws_when_not_set(self):
		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.get_settings",
				return_value=SimpleNamespace(company=None),
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.throw",
				side_effect=frappe.ValidationError("validation failed"),
			),
		):
			with self.assertRaises(frappe.ValidationError):
				get_default_company()

	def test_validate_warehouse_company_throws_on_mismatch(self):
		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.db.get_value",
				return_value="Other Co",
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.throw",
				side_effect=frappe.ValidationError("validation failed"),
			),
		):
			with self.assertRaises(frappe.ValidationError):
				validate_warehouse_company("WH-A", "Default Co", row_idx=1)

	def test_get_transfer_rate_uses_inter_rate_field(self):
		with patch(
			"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.get_charge_rate",
			return_value=15.5,
		) as get_charge_rate:
			rate = get_transfer_rate("Jute Bag", "Inter-Warehouse Transfer")

		self.assertEqual(rate, 15.5)
		get_charge_rate.assert_called_once_with("Jute Bag", "inter_warehouse_transfer_rate")

	def test_get_transfer_rate_uses_intra_rate_field(self):
		with patch(
			"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.get_charge_rate",
			return_value=9.75,
		) as get_charge_rate:
			rate = get_transfer_rate("Jute Bag", "Intra-Warehouse Transfer")

		self.assertEqual(rate, 9.75)
		get_charge_rate.assert_called_once_with("Jute Bag", "intra_warehouse_transfer_rate")

	def test_get_transfer_rate_returns_zero_for_invalid_transfer_type(self):
		with patch(
			"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.get_charge_rate"
		) as get_charge_rate:
			rate = get_transfer_rate("Jute Bag", "Ownership Transfer")

		self.assertEqual(rate, 0.0)
		get_charge_rate.assert_not_called()

	def test_resolve_default_uom_prefers_nos(self):
		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.db.exists",
				side_effect=[True],
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.db.get_value"
			) as get_value,
		):
			self.assertEqual(resolve_default_uom(), "Nos")
			get_value.assert_not_called()

	def test_resolve_default_uom_falls_back_to_enabled_uom(self):
		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.db.exists",
				side_effect=[False],
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.db.get_value",
				side_effect=["Kg"],
			),
		):
			self.assertEqual(resolve_default_uom(), "Kg")

	def test_resolve_default_uom_can_create_nos_if_missing(self):
		uom_doc = SimpleNamespace(name="Nos", insert=lambda **kwargs: None)
		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.db.exists",
				side_effect=[False],
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.db.get_value",
				side_effect=[None, None],
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.get_doc",
				return_value=uom_doc,
			) as get_doc,
			patch.object(uom_doc, "insert") as insert,
		):
			self.assertEqual(resolve_default_uom(create_if_missing=True), "Nos")
			get_doc.assert_called_once()
			insert.assert_called_once_with(ignore_permissions=True)
