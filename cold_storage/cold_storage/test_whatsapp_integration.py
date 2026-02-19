# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from cold_storage.cold_storage.integrations import whatsapp


class _FakeDoc(SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)


class TestWhatsAppIntegration(TestCase):
	def test_normalize_phone_number_strips_symbols(self):
		number = whatsapp._normalize_phone_number("+1 (415) 555-2671")
		self.assertEqual(number, "14155552671")

	def test_normalize_phone_number_applies_default_country_code(self):
		number = whatsapp._normalize_phone_number("0300-1234567", "92")
		self.assertEqual(number, "923001234567")

	def test_send_text_message_uses_meta_messages_endpoint(self):
		settings = {
			"enabled": 1,
			"company": "Default Co",
			"api_version": "v22.0",
			"phone_number_id": "1234567890",
			"access_token": "token-123",
			"default_country_code": "",
			"template_language": "en",
			"inward_template_name": "",
			"outward_template_name": "",
			"send_inward_on_submit": 1,
			"send_outward_on_submit": 1,
		}

		with patch(
			"cold_storage.cold_storage.integrations.whatsapp.make_post_request",
			return_value={"messages": [{"id": "wamid.test.1"}]},
		) as make_post_request:
			response = whatsapp._send_text_message(
				settings=settings,
				to_number="15551234567",
				message="Hello from Cold Storage",
			)

		kwargs = make_post_request.call_args.kwargs
		self.assertEqual(kwargs["url"], "https://graph.facebook.com/v22.0/1234567890/messages")
		self.assertEqual(kwargs["headers"]["Authorization"], "Bearer token-123")
		self.assertEqual(kwargs["json"]["type"], "text")
		self.assertEqual(response["messages"][0]["id"], "wamid.test.1")

	def test_send_document_notification_enforces_company_scope(self):
		settings = {
			"enabled": 1,
			"company": "Company A",
			"api_version": "v22.0",
			"phone_number_id": "1234567890",
			"access_token": "token-123",
			"default_country_code": "",
			"template_language": "en",
			"inward_template_name": "",
			"outward_template_name": "",
			"send_inward_on_submit": 1,
			"send_outward_on_submit": 1,
		}
		doc = _FakeDoc(
			doctype="Cold Storage Inward",
			name="CS-IN-0001",
			company="Company B",
			customer="CUST-0001",
			posting_date="2026-02-19",
			total_qty=10,
		)

		with (
			patch(
				"cold_storage.cold_storage.integrations.whatsapp._get_enabled_settings",
				return_value=settings,
			),
			patch("cold_storage.cold_storage.integrations.whatsapp.frappe.get_doc", return_value=doc),
			patch(
				"cold_storage.cold_storage.integrations.whatsapp.frappe.throw",
				side_effect=frappe.ValidationError("validation failed"),
			),
		):
			with self.assertRaises(frappe.ValidationError):
				whatsapp.send_document_whatsapp_notification(
					doctype="Cold Storage Inward",
					docname="CS-IN-0001",
					raise_exceptions=True,
				)

	def test_build_document_message_uses_custom_inward_template(self):
		doc = _FakeDoc(
			doctype="Cold Storage Inward",
			name="CS-IN-0002",
			company="Default Co",
			customer="CUST-0001",
			posting_date="2026-02-19",
			total_qty=25,
		)
		settings = {"inward_text_template": "Inward {{ voucher_no }} for {{ customer }} qty {{ total_qty }}"}

		message = whatsapp._build_document_message(doc, "Cold Storage Inward", settings)

		self.assertIn("CS-IN-0002", message)
		self.assertIn("CUST-0001", message)
		self.assertIn("25", message)

	def test_build_template_parameters_uses_custom_json_entries(self):
		doc = _FakeDoc(
			doctype="Cold Storage Outward",
			name="CS-OUT-0003",
			company="Default Co",
			customer="CUST-0002",
			posting_date="2026-02-19",
			total_qty=8,
		)
		settings = {
			"outward_template_body_params": (
				'["{{ doc.name }}", "{{ customer }}", "{{ posting_date }}", "Qty {{ total_qty }}"]'
			)
		}

		params = whatsapp._build_template_parameters(doc, "Cold Storage Outward", settings)

		self.assertEqual(params[0], "CS-OUT-0003")
		self.assertEqual(params[1], "CUST-0002")
		self.assertTrue(params[2])
		self.assertIn("Qty", params[3])

	def test_get_whatsapp_setup_status_reports_missing_required_fields(self):
		settings = {
			"enabled": 1,
			"company": "Default Co",
			"api_version": "",
			"phone_number_id": "",
			"access_token": "",
			"default_country_code": "",
			"template_language": "en",
			"inward_template_name": "",
			"inward_template_body_params": '["{{ voucher_no }}"]',
			"inward_text_template": "",
			"outward_template_name": "",
			"outward_template_body_params": '["{{ voucher_no }}"]',
			"outward_text_template": "",
			"send_inward_on_submit": 1,
			"send_outward_on_submit": 1,
		}

		with (
			patch("cold_storage.cold_storage.integrations.whatsapp.frappe.only_for"),
			patch("cold_storage.cold_storage.integrations.whatsapp.get_whatsapp_settings", return_value=settings),
		):
			status = whatsapp.get_whatsapp_setup_status()

		self.assertFalse(status["ready"])
		self.assertIn("Phone Number ID", status["missing_fields"])
		self.assertIn("Permanent Access Token", status["missing_fields"])
		self.assertIn("Meta Graph API Version", status["missing_fields"])

	def test_get_whatsapp_setup_status_returns_ready_for_complete_config(self):
		settings = {
			"enabled": 1,
			"company": "Default Co",
			"api_version": "v22.0",
			"phone_number_id": "123456789",
			"access_token": "token-123",
			"default_country_code": "92",
			"template_language": "en",
			"inward_template_name": "cs_inward_notice",
			"inward_template_body_params": '["{{ voucher_no }}", "{{ customer }}"]',
			"inward_text_template": "",
			"outward_template_name": "cs_outward_notice",
			"outward_template_body_params": '["{{ voucher_no }}", "{{ customer }}"]',
			"outward_text_template": "",
			"send_inward_on_submit": 1,
			"send_outward_on_submit": 1,
		}

		with (
			patch("cold_storage.cold_storage.integrations.whatsapp.frappe.only_for"),
			patch("cold_storage.cold_storage.integrations.whatsapp.get_whatsapp_settings", return_value=settings),
		):
			status = whatsapp.get_whatsapp_setup_status()

		self.assertTrue(status["ready"])
		self.assertEqual(
			status["endpoint"],
			"https://graph.facebook.com/v22.0/123456789/messages",
		)
