# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer import (
	ColdStorageTransfer,
)


class TestColdStorageTransfer(TestCase):
	def test_create_stock_entry_for_ownership_uses_source_as_target(self):
		doc = SimpleNamespace(
			stock_entry=None,
			transfer_type="Ownership Transfer",
			company="Default Co",
			posting_date="2026-02-13",
			doctype="Cold Storage Transfer",
			name="CST-OWN-0001",
			items=[
				SimpleNamespace(
					item="ITEM-001",
					qty=6,
					uom="Nos",
					batch_no="BATCH-0001",
					source_warehouse="WH-A",
					target_warehouse=None,
				)
			],
			db_set=Mock(),
		)
		stock_utils = Mock()
		stock_utils.create_stock_entry_for_cold_storage.return_value = "MAT-STE-0001"

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.ColdStorageTransfer._get_or_create_target_batch_for_ownership",
				return_value="BATCH-NEW-0001",
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.ColdStorageTransfer._get_stock_utils",
				return_value=stock_utils,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.msgprint"
			),
		):
			ColdStorageTransfer._create_stock_entry(doc)

		stock_utils.create_stock_entry_for_cold_storage.assert_called_once_with(
			company="Default Co",
			posting_date="2026-02-13",
			purpose="Repack",
			items=[
				{
					"item_code": "ITEM-001",
					"qty": 6,
					"uom": "Nos",
					"batch_no": "BATCH-0001",
					"s_warehouse": "WH-A",
				},
				{
					"item_code": "ITEM-001",
					"qty": 6,
					"uom": "Nos",
					"batch_no": "BATCH-NEW-0001",
					"t_warehouse": "WH-A",
				},
			],
			reference_doctype="Cold Storage Transfer",
			reference_name="CST-OWN-0001",
		)
		doc.db_set.assert_called_once_with("stock_entry", "MAT-STE-0001")

	def test_create_stock_entry_creates_material_transfer(self):
		doc = SimpleNamespace(
			stock_entry=None,
			transfer_type="Inter-Warehouse Transfer",
			company="Default Co",
			posting_date="2026-02-13",
			doctype="Cold Storage Transfer",
			name="CST-0001",
			items=[
				SimpleNamespace(
					item="ITEM-001",
					qty=6,
					uom="Nos",
					batch_no="BATCH-0001",
					source_warehouse="WH-A",
					target_warehouse="WH-B",
				)
			],
			db_set=Mock(),
		)
		stock_utils = Mock()
		stock_utils.create_stock_entry_for_cold_storage.return_value = "MAT-STE-0001"

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.ColdStorageTransfer._get_stock_utils",
				return_value=stock_utils,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.msgprint"
			),
		):
			ColdStorageTransfer._create_stock_entry(doc)

		stock_utils.create_stock_entry_for_cold_storage.assert_called_once_with(
			company="Default Co",
			posting_date="2026-02-13",
			purpose="Material Transfer",
			items=[
				{
					"item_code": "ITEM-001",
					"qty": 6,
					"uom": "Nos",
					"batch_no": "BATCH-0001",
					"s_warehouse": "WH-A",
					"t_warehouse": "WH-B",
				}
			],
			reference_doctype="Cold Storage Transfer",
			reference_name="CST-0001",
		)
		doc.db_set.assert_called_once_with("stock_entry", "MAT-STE-0001")

	def test_create_stock_entry_for_intra_uses_source_when_target_empty(self):
		doc = SimpleNamespace(
			stock_entry=None,
			transfer_type="Intra-Warehouse Transfer",
			company="Default Co",
			posting_date="2026-02-13",
			doctype="Cold Storage Transfer",
			name="CST-INTRA-0001",
			items=[
				SimpleNamespace(
					item="ITEM-001",
					qty=6,
					uom="Nos",
					batch_no="BATCH-0001",
					source_warehouse="WH-A",
					target_warehouse=None,
				)
			],
			db_set=Mock(),
		)
		stock_utils = Mock()
		stock_utils.create_stock_entry_for_cold_storage.return_value = "MAT-STE-0010"

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.ColdStorageTransfer._get_stock_utils",
				return_value=stock_utils,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.msgprint"
			),
		):
			ColdStorageTransfer._create_stock_entry(doc)

		stock_utils.create_stock_entry_for_cold_storage.assert_called_once_with(
			company="Default Co",
			posting_date="2026-02-13",
			purpose="Material Transfer",
			items=[
				{
					"item_code": "ITEM-001",
					"qty": 6,
					"uom": "Nos",
					"batch_no": "BATCH-0001",
					"s_warehouse": "WH-A",
					"t_warehouse": "WH-A",
				}
			],
			reference_doctype="Cold Storage Transfer",
			reference_name="CST-INTRA-0001",
		)
		doc.db_set.assert_called_once_with("stock_entry", "MAT-STE-0010")

	def test_cancel_ownership_transfer_deletes_generated_batches_and_cancels_journal_entry(self):
		doc = SimpleNamespace(
			transfer_type="Ownership Transfer",
			items=[],
			stock_entry=None,
			journal_entry="ACC-JV-0001",
			_delete_generated_target_batches_for_ownership=Mock(),
		)
		je = Mock(docstatus=1)
		je.flags = SimpleNamespace(ignore_permissions=False)
		stock_utils = Mock()
		stock_utils.cancel_stock_entry_if_submitted.return_value = False

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.ColdStorageTransfer._get_stock_utils",
				return_value=stock_utils,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.get_doc",
				return_value=je,
			) as get_doc,
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.msgprint"
			),
		):
			ColdStorageTransfer._cancel_linked_docs(doc)

		stock_utils.cancel_stock_entry_if_submitted.assert_called_once_with(None)
		doc._delete_generated_target_batches_for_ownership.assert_called_once_with()
		get_doc.assert_called_once_with("Journal Entry", "ACC-JV-0001")
		self.assertTrue(je.flags.ignore_permissions)
		je.cancel.assert_called_once()

	def test_cancel_location_transfer_cancels_journal_entry(self):
		doc = SimpleNamespace(
			transfer_type="Inter-Warehouse Transfer",
			items=[],
			stock_entry="MAT-STE-0002",
			journal_entry="ACC-JV-0002",
		)
		je = Mock(docstatus=1)
		je.flags = SimpleNamespace(ignore_permissions=False)
		stock_utils = Mock()
		stock_utils.cancel_stock_entry_if_submitted.return_value = True

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.ColdStorageTransfer._get_stock_utils",
				return_value=stock_utils,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.get_doc",
				return_value=je,
			) as get_doc,
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.msgprint"
			),
		):
			ColdStorageTransfer._cancel_linked_docs(doc)

		stock_utils.cancel_stock_entry_if_submitted.assert_called_once_with("MAT-STE-0002")
		get_doc.assert_called_once_with("Journal Entry", "ACC-JV-0002")
		self.assertTrue(je.flags.ignore_permissions)
		je.cancel.assert_called_once()

	def test_validate_items_requires_source_warehouse_for_ownership(self):
		doc = SimpleNamespace(
			transfer_type="Ownership Transfer",
			company="Default Co",
			from_customer="CUST-OLD",
			items=[SimpleNamespace(idx=1, batch_no="BATCH-0001", item="ITEM-001", source_warehouse=None)],
		)

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.throw",
				side_effect=frappe.ValidationError("validation failed"),
			),
		):
			with self.assertRaises(frappe.ValidationError):
				ColdStorageTransfer._validate_items(doc)

	def test_validate_items_rejects_batch_item_mismatch(self):
		doc = SimpleNamespace(
			transfer_type="Inter-Warehouse Transfer",
			company="Default Co",
			customer="CUST-0001",
			items=[
				SimpleNamespace(
					idx=1,
					batch_no="BATCH-0001",
					item="ITEM-WRONG",
					source_warehouse="WH-A",
					target_warehouse="WH-B",
				)
			],
		)

		def get_value(_doctype, _name, fieldname):
			if fieldname == "item":
				return "ITEM-ACTUAL"
			if fieldname == "custom_customer":
				return "CUST-0001"
			return None

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.db.get_value",
				side_effect=get_value,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.throw",
				side_effect=frappe.ValidationError("validation failed"),
			),
		):
			with self.assertRaises(frappe.ValidationError):
				ColdStorageTransfer._validate_items(doc)

	def test_validate_items_for_intra_sets_target_to_source(self):
		doc = SimpleNamespace(
			transfer_type="Intra-Warehouse Transfer",
			company="Default Co",
			customer="CUST-0001",
			items=[
				SimpleNamespace(
					idx=1,
					batch_no="BATCH-0001",
					item="ITEM-001",
					source_warehouse="WH-A",
					target_warehouse=None,
				)
			],
		)

		def get_value(_doctype, _name, fieldname):
			if fieldname == "item":
				return "ITEM-001"
			if fieldname == "custom_customer":
				return "CUST-0001"
			return None

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.db.get_value",
				side_effect=get_value,
			),
			patch(
				"cold_storage.cold_storage.utils.get_batch_balance",
				return_value=10,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.validate_warehouse_company"
			),
		):
			ColdStorageTransfer._validate_items(doc)

		self.assertEqual(doc.items[0].target_warehouse, "WH-A")

	def test_process_location_transfer_sets_party_for_receivable_account(self):
		doc = SimpleNamespace(
			total_transfer_charges=100,
			posting_date="2026-02-13",
			transfer_type="Inter-Warehouse Transfer",
			name="CST-0002",
			customer="CUST-0001",
			db_set=Mock(),
		)
		settings = SimpleNamespace(
			company="Default Co",
			transfer_expense_account="EXP-ACC",
			default_income_account="REC-ACC",
			cost_center="Main - DC",
		)
		je = Mock()
		je.flags = SimpleNamespace(ignore_permissions=False)
		je.name = "ACC-JV-0003"

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.get_settings",
				return_value=settings,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.db.get_value",
				side_effect=lambda doctype, name, field: (
					"Receivable" if doctype == "Account" and name == "REC-ACC" else None
				),
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.new_doc",
				return_value=je,
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.msgprint"
			),
		):
			ColdStorageTransfer._process_location_transfer(doc)

		self.assertTrue(je.flags.ignore_permissions)
		je.append.assert_any_call(
			"accounts",
			{
				"account": "REC-ACC",
				"credit_in_account_currency": 100,
				"cost_center": "Main - DC",
				"party_type": "Customer",
				"party": "CUST-0001",
			},
		)
		doc.db_set.assert_called_once_with("journal_entry", "ACC-JV-0003")
		je.submit.assert_called_once()

	def test_get_party_details_for_account_throws_for_payable(self):
		doc = SimpleNamespace(customer="CUST-0001")

		with (
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.db.get_value",
				return_value="Payable",
			),
			patch(
				"cold_storage.cold_storage.doctype.cold_storage_transfer.cold_storage_transfer.frappe.throw",
				side_effect=frappe.ValidationError("validation failed"),
			),
		):
			with self.assertRaises(frappe.ValidationError):
				ColdStorageTransfer._get_party_details_for_account(doc, "PAY-ACC")
