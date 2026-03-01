# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from cold_storage.cold_storage.doctype.cold_storage_outward.cold_storage_outward import (
	ColdStorageOutward,
)


class TestColdStorageOutward(TestCase):
	def test_create_stock_entry_creates_material_issue(self):
		doc = SimpleNamespace(
			stock_entry=None,
			company="Default Co",
			posting_date="2026-02-13",
			doctype="Cold Storage Outward",
			name="CSO-0001",
			items=[
				SimpleNamespace(
					item="ITEM-001",
					qty=4,
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
				"cold_storage.cold_storage.doctype.cold_storage_outward.cold_storage_outward.ColdStorageOutward._get_stock_utils",
				return_value=stock_utils,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_outward.cold_storage_outward.frappe.msgprint"
			),
		):
			ColdStorageOutward._create_stock_entry(doc)

		stock_utils.create_stock_entry_for_cold_storage.assert_called_once_with(
			company="Default Co",
			posting_date="2026-02-13",
			purpose="Material Issue",
			items=[
				{
					"item_code": "ITEM-001",
					"qty": 4,
					"uom": "Nos",
					"batch_no": "BATCH-0001",
					"s_warehouse": "Stores - CO",
				}
			],
			reference_doctype="Cold Storage Outward",
			reference_name="CSO-0001",
		)
		doc.db_set.assert_called_once_with("stock_entry", "MAT-STE-0001")

	def test_cancel_linked_docs_cancels_stock_and_sales_invoice(self):
		doc = SimpleNamespace(stock_entry="MAT-STE-0001", sales_invoice="SINV-0001")
		si = Mock(docstatus=1)
		si.flags = SimpleNamespace(ignore_permissions=False)
		stock_utils = Mock()
		stock_utils.cancel_stock_entry_if_submitted.return_value = True

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_outward.cold_storage_outward.ColdStorageOutward._get_stock_utils",
				return_value=stock_utils,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_outward.cold_storage_outward.frappe.get_doc",
				return_value=si,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_outward.cold_storage_outward.frappe.msgprint"
			),
		):
			ColdStorageOutward._cancel_linked_docs(doc)

		stock_utils.cancel_stock_entry_if_submitted.assert_called_once_with("MAT-STE-0001")
		self.assertTrue(si.flags.ignore_permissions)
		si.cancel.assert_called_once()

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
				"cold_storage.cold_storage.doctype.cold_storage_outward.cold_storage_outward.frappe.db.get_value",
				side_effect=get_value,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_outward.cold_storage_outward.frappe.throw",
				side_effect=frappe.ValidationError("validation failed"),
			),
		):
			with self.assertRaises(frappe.ValidationError):
				ColdStorageOutward._validate_items(doc)

	def test_append_dispatch_gst_tax_applies_only_on_handling(self):
		si = Mock()
		doc = SimpleNamespace(
			items=[
				SimpleNamespace(qty=2, handling_rate=100, loading_rate=50),
				SimpleNamespace(qty=1, handling_rate=40, loading_rate=20),
			]
		)
		settings = SimpleNamespace(dispatch_gst_account="GST Output - CO", dispatch_gst_rate=18, cost_center=None)

		ColdStorageOutward._append_dispatch_gst_tax(doc, si, settings)

		si.append.assert_called_once()
		_append_field, tax_row = si.append.call_args.args
		self.assertEqual(_append_field, "taxes")
		self.assertEqual(tax_row["account_head"], "GST Output - CO")
		self.assertEqual(tax_row["tax_amount"], 43.2)

	def test_append_dispatch_gst_tax_skips_when_no_handling_charges(self):
		si = Mock()
		doc = SimpleNamespace(items=[SimpleNamespace(qty=2, handling_rate=0, loading_rate=60)])
		settings = SimpleNamespace(dispatch_gst_account="GST Output - CO", dispatch_gst_rate=18, cost_center=None)

		ColdStorageOutward._append_dispatch_gst_tax(doc, si, settings)

		si.append.assert_not_called()
