# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from cold_storage.cold_storage.naming import (
	get_company_abbreviation,
	get_series_for_company,
	is_cold_storage_prefixed_voucher,
)
from cold_storage.events.naming import autoname_cold_storage_gl_entry


class DummyDoc(SimpleNamespace):
	def get(self, key: str, default=None):
		return getattr(self, key, default)


class TestColdStorageNaming(TestCase):
	def test_get_company_abbreviation_prefers_company_abbr(self):
		with patch(
			"cold_storage.cold_storage.naming.frappe.get_cached_value",
			return_value="SCS",
		):
			self.assertEqual(get_company_abbreviation("Siddique Cold Storage"), "SCS")

	def test_get_company_abbreviation_sanitizes_value(self):
		with patch(
			"cold_storage.cold_storage.naming.frappe.get_cached_value",
			return_value="Scs # 01",
		):
			self.assertEqual(get_company_abbreviation("Siddique Cold Storage"), "SCS01")

	def test_get_series_for_company_builds_prefix(self):
		with patch(
			"cold_storage.cold_storage.naming.frappe.get_cached_value",
			return_value="SCS",
		):
			self.assertEqual(get_series_for_company("inward", "Siddique Cold Storage"), "SCS-CS-IN-.YYYY.-")

	def test_is_cold_storage_prefixed_voucher(self):
		with patch(
			"cold_storage.cold_storage.naming.frappe.get_cached_value",
			return_value="SCS",
		):
			self.assertTrue(
				is_cold_storage_prefixed_voucher("SCS-CS-SINV-2026-00001", "Siddique Cold Storage")
			)
			self.assertFalse(
				is_cold_storage_prefixed_voucher("SCS-SINV-2026-00001", "Siddique Cold Storage")
			)

	def test_autoname_cold_storage_gl_entry_assigns_prefixed_name(self):
		doc = DummyDoc(
			name=None,
			voucher_type="Sales Invoice",
			voucher_no="SCS-CS-SINV-2026-00001",
			company="Siddique Cold Storage",
		)
		with (
			patch(
				"cold_storage.events.naming.is_cold_storage_prefixed_voucher",
				return_value=True,
			),
			patch(
				"cold_storage.events.naming.get_series_for_company",
				return_value="SCS-CS-GLE-.YYYY.-",
			),
			patch(
				"cold_storage.events.naming.make_autoname",
				return_value="SCS-CS-GLE-2026-00001",
			) as make_name,
		):
			autoname_cold_storage_gl_entry(doc)

		self.assertEqual(doc.name, "SCS-CS-GLE-2026-00001")
		make_name.assert_called_once_with("SCS-CS-GLE-.YYYY.-.#####", doc=doc)

	def test_autoname_cold_storage_gl_entry_skips_non_cold_storage_voucher(self):
		doc = DummyDoc(
			name=None,
			voucher_type="Sales Invoice",
			voucher_no="ACC-SINV-2026-00001",
			company="Siddique Cold Storage",
		)
		with (
			patch(
				"cold_storage.events.naming.is_cold_storage_prefixed_voucher",
				return_value=False,
			),
			patch("cold_storage.events.naming.make_autoname") as make_name,
		):
			autoname_cold_storage_gl_entry(doc)

		self.assertIsNone(doc.name)
		make_name.assert_not_called()

