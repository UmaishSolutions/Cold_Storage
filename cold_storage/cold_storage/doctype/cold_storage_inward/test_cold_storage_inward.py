# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from cold_storage.cold_storage.doctype.cold_storage_inward.cold_storage_inward import (
	ColdStorageInward,
)


class DummyDoc(SimpleNamespace):
	def get(self, key: str):
		return getattr(self, key, None)


class TestColdStorageInward(TestCase):
	def test_create_stock_entry_creates_material_receipt(self):
		doc = SimpleNamespace(
			stock_entry=None,
			company="Default Co",
			posting_date="2026-02-13",
			doctype="Cold Storage Inward",
			name="CSI-0001",
			items=[
				SimpleNamespace(
					item="ITEM-001",
					qty=10,
					uom="Nos",
					batch_no="BATCH-0001",
					warehouse="Stores - CO",
				)
			],
			db_set=Mock(),
		)
		stock_utils = Mock()
		stock_utils.create_stock_entry_for_cold_storage.return_value = "MAT-STE-0001"

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_inward.cold_storage_inward.ColdStorageInward._get_stock_utils",
				return_value=stock_utils,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_inward.cold_storage_inward.frappe.msgprint"
			),
		):
			ColdStorageInward._create_stock_entry(doc)

		stock_utils.create_stock_entry_for_cold_storage.assert_called_once_with(
			company="Default Co",
			posting_date="2026-02-13",
			purpose="Material Receipt",
			items=[
				{
					"item_code": "ITEM-001",
					"qty": 10,
					"uom": "Nos",
					"batch_no": "BATCH-0001",
					"t_warehouse": "Stores - CO",
				}
			],
			reference_doctype="Cold Storage Inward",
			reference_name="CSI-0001",
		)
		doc.db_set.assert_called_once_with("stock_entry", "MAT-STE-0001")

	def test_set_company_rejects_non_default_company(self):
		doc = SimpleNamespace(company="Wrong Co")

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.get_default_company",
				return_value="Default Co",
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_inward.cold_storage_inward.frappe.throw",
				side_effect=frappe.ValidationError("validation failed"),
			),
		):
			with self.assertRaises(frappe.ValidationError):
				ColdStorageInward._set_company(doc)

	def test_validate_items_rejects_batch_item_mismatch(self):
		doc = SimpleNamespace(
			company="Default Co",
			customer="CUST-0001",
			items=[SimpleNamespace(idx=1, batch_no="BATCH-0001", item="ITEM-WRONG")],
		)

		def get_value(_doctype, _name, fieldname):
			if fieldname == "item":
				return "ITEM-ACTUAL"
			if fieldname == "custom_customer":
				return "CUST-0001"
			return None

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_inward.cold_storage_inward.frappe.db.get_value",
				side_effect=get_value,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_inward.cold_storage_inward.frappe.throw",
				side_effect=frappe.ValidationError("validation failed"),
			),
		):
			with self.assertRaises(frappe.ValidationError):
				ColdStorageInward._validate_items(doc)

	def test_cancel_linked_docs_ignores_permissions(self):
		doc = DummyDoc(
			stock_entry="MAT-STE-0001",
			sales_invoice="SINV-0001",
			journal_entry="ACC-JV-0001",
		)
		si = Mock(docstatus=1)
		si.flags = SimpleNamespace(ignore_permissions=False)
		je = Mock(docstatus=1)
		je.flags = SimpleNamespace(ignore_permissions=False)
		stock_utils = Mock()
		stock_utils.cancel_stock_entry_if_submitted.return_value = True

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_inward.cold_storage_inward.ColdStorageInward._get_stock_utils",
				return_value=stock_utils,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_inward.cold_storage_inward.frappe.get_doc",
				side_effect=[si, je],
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_inward.cold_storage_inward.frappe.msgprint"
			),
		):
			ColdStorageInward._cancel_linked_docs(doc)

		stock_utils.cancel_stock_entry_if_submitted.assert_called_once_with("MAT-STE-0001")
		self.assertTrue(si.flags.ignore_permissions)
		self.assertTrue(je.flags.ignore_permissions)
		si.cancel.assert_called_once()
		je.cancel.assert_called_once()

	def test_get_party_details_for_account_returns_customer_for_receivable(self):
		doc = SimpleNamespace(customer="CUST-0001")

		with patch(
			"cold_storage.cold_storage.doctype.cold_storage_inward.cold_storage_inward.frappe.db.get_value",
			return_value="Receivable",
		):
			result = ColdStorageInward._get_party_details_for_account(doc, "ACC-REC", "Default Co")

		self.assertEqual(result, {"party_type": "Customer", "party": "CUST-0001"})

	def test_get_party_details_for_account_returns_supplier_for_payable(self):
		doc = SimpleNamespace(
			_resolve_supplier_for_payable_account=Mock(return_value="SUP-0001"),
		)

		with patch(
			"cold_storage.cold_storage.doctype.cold_storage_inward.cold_storage_inward.frappe.db.get_value",
			return_value="Payable",
		):
			result = ColdStorageInward._get_party_details_for_account(doc, "ACC-PAY", "Default Co")

		doc._resolve_supplier_for_payable_account.assert_called_once_with("ACC-PAY", "Default Co")
		self.assertEqual(result, {"party_type": "Supplier", "party": "SUP-0001"})

	def test_get_party_details_for_account_throws_when_payable_supplier_missing(self):
		doc = SimpleNamespace(
			_resolve_supplier_for_payable_account=Mock(return_value=None),
		)

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_inward.cold_storage_inward.frappe.db.get_value",
				return_value="Payable",
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_inward.cold_storage_inward.frappe.throw",
				side_effect=frappe.ValidationError("validation failed"),
			),
		):
			with self.assertRaises(frappe.ValidationError):
				ColdStorageInward._get_party_details_for_account(doc, "ACC-PAY", "Default Co")
