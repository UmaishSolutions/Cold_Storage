# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

import json
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
	ColdStorageSettings,
	get_default_company,
	get_default_whatsapp_template_body_params_json,
	get_item_group_rates,
	get_transfer_rate,
	get_whatsapp_settings,
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

	def test_get_item_group_rates_returns_all_rate_fields(self):
		with patch(
			"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.get_charge_rate",
			side_effect=[5.0, 6.0, 7.0, 8.0, 9.0],
		):
			rates = get_item_group_rates("Frozen Foods")

		self.assertEqual(
			rates,
			{
				"unloading_rate": 5.0,
				"handling_rate": 6.0,
				"loading_rate": 7.0,
				"inter_warehouse_transfer_rate": 8.0,
				"intra_warehouse_transfer_rate": 9.0,
			},
		)

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

	def test_get_whatsapp_settings_returns_company_scoped_config(self):
		settings = SimpleNamespace(
			whatsapp_enabled=1,
			company="Default Co",
			whatsapp_api_version="v22.0",
			whatsapp_phone_number_id="123456",
			whatsapp_default_country_code="92",
			whatsapp_template_language="en",
			whatsapp_inward_template_name="cs_inward_notice",
			whatsapp_inward_template_body_params='["{{ doc.name }}"]',
			whatsapp_inward_text_template="Inward {{ doc.name }}",
			whatsapp_outward_template_name="cs_outward_notice",
			whatsapp_outward_template_body_params='["{{ doc.customer }}"]',
			whatsapp_outward_text_template="Outward {{ doc.name }}",
			whatsapp_send_inward_on_submit=1,
			whatsapp_send_outward_on_submit=0,
			get_password=lambda _fieldname, **_kwargs: "token-xyz",
		)

		with patch(
			"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.get_settings",
			return_value=settings,
		):
			data = get_whatsapp_settings()

		self.assertEqual(data["enabled"], 1)
		self.assertEqual(data["company"], "Default Co")
		self.assertEqual(data["phone_number_id"], "123456")
		self.assertEqual(data["access_token"], "token-xyz")
		self.assertIn("{{ doc.name }}", data["inward_template_body_params"])
		self.assertIn("Outward", data["outward_text_template"])
		self.assertEqual(data["send_outward_on_submit"], 0)

	def test_get_default_whatsapp_template_body_params_json_returns_meta_default(self):
		inward = json.loads(get_default_whatsapp_template_body_params_json("Cold Storage Inward"))
		outward = json.loads(get_default_whatsapp_template_body_params_json("Cold Storage Outward"))

		self.assertEqual(inward, ["{{ voucher_no }}", "{{ customer }}", "{{ posting_date }}", "{{ total_qty }}"])
		self.assertEqual(outward, ["{{ voucher_no }}", "{{ customer }}", "{{ posting_date }}", "{{ total_qty }}"])

	def test_get_whatsapp_settings_falls_back_to_default_body_params_when_blank(self):
		settings = SimpleNamespace(
			whatsapp_enabled=1,
			company="Default Co",
			whatsapp_api_version="v22.0",
			whatsapp_phone_number_id="123456",
			whatsapp_default_country_code="92",
			whatsapp_template_language="en",
			whatsapp_inward_template_name="cs_inward_notice",
			whatsapp_inward_template_body_params="",
			whatsapp_inward_text_template="",
			whatsapp_outward_template_name="cs_outward_notice",
			whatsapp_outward_template_body_params="",
			whatsapp_outward_text_template="",
			whatsapp_send_inward_on_submit=1,
			whatsapp_send_outward_on_submit=1,
			get_password=lambda _fieldname, **_kwargs: "token-xyz",
		)

		with patch(
			"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.get_settings",
			return_value=settings,
		):
			data = get_whatsapp_settings()

		self.assertEqual(
			json.loads(data["inward_template_body_params"]),
			["{{ voucher_no }}", "{{ customer }}", "{{ posting_date }}", "{{ total_qty }}"],
		)
		self.assertEqual(
			json.loads(data["outward_template_body_params"]),
			["{{ voucher_no }}", "{{ customer }}", "{{ posting_date }}", "{{ total_qty }}"],
		)

	def test_validate_dispatch_gst_configuration_requires_account(self):
		doc = SimpleNamespace(
			enable_dispatch_gst_on_handling=1,
			dispatch_gst_account=None,
			dispatch_gst_rate=18,
			company="Default Co",
		)
		with patch(
			"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.throw",
			side_effect=frappe.ValidationError("validation failed"),
		):
			with self.assertRaises(frappe.ValidationError):
				ColdStorageSettings._validate_dispatch_gst_configuration(doc)

	def test_validate_dispatch_gst_configuration_requires_positive_rate(self):
		doc = SimpleNamespace(
			enable_dispatch_gst_on_handling=1,
			dispatch_gst_account="GST Output - CO",
			dispatch_gst_rate=0,
			company="Default Co",
		)
		with patch(
			"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.throw",
			side_effect=frappe.ValidationError("validation failed"),
		):
			with self.assertRaises(frappe.ValidationError):
				ColdStorageSettings._validate_dispatch_gst_configuration(doc)

	def test_validate_dispatch_gst_configuration_checks_company(self):
		doc = SimpleNamespace(
			enable_dispatch_gst_on_handling=1,
			dispatch_gst_account="GST Output - OTH",
			dispatch_gst_rate=18,
			company="Default Co",
		)
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
				ColdStorageSettings._validate_dispatch_gst_configuration(doc)

	def test_validate_dispatch_extra_charges_configuration_requires_positive_rate(self):
		doc = SimpleNamespace(
			dispatch_extra_charges=[
				SimpleNamespace(
					idx=1,
					is_active=1,
					charge_name="Handling Surcharge",
					charge_description="Cold handling surcharge",
					charge_rate=0,
					credit_account="Income - CO",
				)
			]
		)
		with patch(
			"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.throw",
			side_effect=frappe.ValidationError("validation failed"),
		):
			with self.assertRaises(frappe.ValidationError):
				ColdStorageSettings._validate_dispatch_extra_charges_configuration(doc)

	def test_validate_dispatch_extra_charges_configuration_requires_description(self):
		doc = SimpleNamespace(
			dispatch_extra_charges=[
				SimpleNamespace(
					idx=1,
					is_active=1,
					charge_name="Handling Surcharge",
					charge_description="",
					charge_rate=10,
					credit_account="Income - CO",
				)
			]
		)
		with patch(
			"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.throw",
			side_effect=frappe.ValidationError("validation failed"),
		):
			with self.assertRaises(frappe.ValidationError):
				ColdStorageSettings._validate_dispatch_extra_charges_configuration(doc)

	def test_validate_dispatch_extra_charges_configuration_requires_credit_account(self):
		doc = SimpleNamespace(
			dispatch_extra_charges=[
				SimpleNamespace(
					idx=1,
					is_active=1,
					charge_name="Handling Surcharge",
					charge_description="Cold handling",
					charge_rate=10,
					credit_account=None,
				)
			],
			company="Default Co",
		)
		with patch(
			"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.frappe.throw",
			side_effect=frappe.ValidationError("validation failed"),
		):
			with self.assertRaises(frappe.ValidationError):
				ColdStorageSettings._validate_dispatch_extra_charges_configuration(doc)
