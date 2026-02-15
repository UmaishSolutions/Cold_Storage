# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from unittest import TestCase
from unittest.mock import patch

from cold_storage.cold_storage.utils import (
	get_batch_balance,
	get_document_qr_code_data_uri,
	get_document_qr_code_payload,
	get_document_sidebar_qr_code_data_uri,
	get_document_sidebar_qr_code_payload,
	search_batches_for_customer_warehouse,
	search_items_for_customer_stock,
	search_warehouses_for_batch,
	search_warehouses_for_customer,
)


class TestUtils(TestCase):
	def test_get_batch_balance_returns_zero_without_batch_or_warehouse(self):
		self.assertEqual(get_batch_balance(""), 0.0)
		self.assertEqual(get_batch_balance("BATCH-0001"), 0.0)

	def test_get_batch_balance_uses_erpnext_batch_qty(self):
		with patch(
			"cold_storage.cold_storage.utils.get_batch_qty",
			return_value=5.5,
		):
			self.assertEqual(
				get_batch_balance("BATCH-0001", warehouse="Main - CO", item_code="ITEM-001"), 5.5
			)

	def test_get_batch_balance_ignores_item_code_and_uses_batch_warehouse(self):
		with patch(
			"cold_storage.cold_storage.utils.get_batch_qty",
			return_value=4,
		):
			self.assertEqual(get_batch_balance("BATCH-0001", warehouse="Main - CO"), 4.0)

	def test_search_batches_returns_empty_without_customer_or_warehouse(self):
		with patch("cold_storage.cold_storage.utils.frappe.db.sql") as db_sql:
			rows = search_batches_for_customer_warehouse(
				doctype="Batch",
				txt="",
				searchfield="name",
				start=0,
				page_len=20,
				filters={"customer": "", "warehouse": "Main - CO", "item": ""},
			)
			self.assertEqual(rows, [])
			stock_ledger_calls = [
				args for args, _kwargs in db_sql.call_args_list if "tabStock Ledger Entry" in args[0]
			]
			self.assertEqual(stock_ledger_calls, [])

			rows = search_batches_for_customer_warehouse(
				doctype="Batch",
				txt="",
				searchfield="name",
				start=0,
				page_len=20,
				filters={"customer": "CUST-0001", "warehouse": "", "item": ""},
			)
			self.assertEqual(rows, [])
			stock_ledger_calls = [
				args for args, _kwargs in db_sql.call_args_list if "tabStock Ledger Entry" in args[0]
			]
			self.assertEqual(stock_ledger_calls, [])

	def test_search_batches_filters_by_customer_warehouse_item(self):
		def sql_side_effect(query, *args, **kwargs):
			if "tabStock Ledger Entry" in query:
				return [("BATCH-0001",)]
			if "tabDocType" in query:
				params = args[0] if args else {}
				doctype_name = params.get("param1") if isinstance(params, dict) else "Batch"
				return [(doctype_name,)]
			return []

		with patch(
			"cold_storage.cold_storage.utils.frappe.db.sql",
			side_effect=sql_side_effect,
		) as db_sql:
			rows = search_batches_for_customer_warehouse(
				doctype="Batch",
				txt="BATCH",
				searchfield="name",
				start=5,
				page_len=10,
				filters={"customer": "CUST-0001", "warehouse": "Main - CO", "item": "ITEM-001"},
			)

		self.assertEqual(rows, [("BATCH-0001",)])
		_, kwargs = db_sql.call_args
		self.assertEqual(kwargs, {})
		query, params = db_sql.call_args.args
		self.assertIn("b.custom_customer = %(customer)s", query)
		self.assertIn("sle.warehouse = %(warehouse)s", query)
		self.assertIn("and b.item = %(item)s", query)
		self.assertEqual(params["customer"], "CUST-0001")
		self.assertEqual(params["warehouse"], "Main - CO")
		self.assertEqual(params["item"], "ITEM-001")
		self.assertEqual(params["start"], 5)
		self.assertEqual(params["page_len"], 10)

	def test_search_warehouses_returns_empty_without_customer(self):
		with patch("cold_storage.cold_storage.utils.frappe.db.sql") as db_sql:
			rows = search_warehouses_for_customer(
				doctype="Warehouse",
				txt="",
				searchfield="name",
				start=0,
				page_len=20,
				filters={"customer": "", "company": "Default Co", "item": ""},
			)
			self.assertEqual(rows, [])
			stock_ledger_calls = [
				args for args, _kwargs in db_sql.call_args_list if "tabStock Ledger Entry" in args[0]
			]
			self.assertEqual(stock_ledger_calls, [])

	def test_search_warehouses_filters_by_customer_company_item(self):
		def sql_side_effect(query, *args, **kwargs):
			if "tabStock Ledger Entry" in query:
				return [("Stores - CO",)]
			if "tabDocType" in query:
				params = args[0] if args else {}
				doctype_name = params.get("param1") if isinstance(params, dict) else "Warehouse"
				return [(doctype_name,)]
			return []

		with patch(
			"cold_storage.cold_storage.utils.frappe.db.sql",
			side_effect=sql_side_effect,
		) as db_sql:
			rows = search_warehouses_for_customer(
				doctype="Warehouse",
				txt="Stores",
				searchfield="name",
				start=2,
				page_len=15,
				filters={"customer": "CUST-0001", "company": "Default Co", "item": "ITEM-001"},
			)

		self.assertEqual(rows, [("Stores - CO",)])
		query, params = db_sql.call_args.args
		self.assertIn("b.custom_customer = %(customer)s", query)
		self.assertIn("w.company = %(company)s", query)
		self.assertIn("and sle.item_code = %(item)s", query)
		self.assertEqual(params["customer"], "CUST-0001")
		self.assertEqual(params["company"], "Default Co")
		self.assertEqual(params["item"], "ITEM-001")
		self.assertEqual(params["start"], 2)
		self.assertEqual(params["page_len"], 15)

	def test_search_items_returns_empty_without_customer(self):
		with patch("cold_storage.cold_storage.utils.frappe.db.sql") as db_sql:
			rows = search_items_for_customer_stock(
				doctype="Item",
				txt="",
				searchfield="name",
				start=0,
				page_len=20,
				filters={"customer": "", "company": "Default Co", "warehouse": "Stores - CO"},
			)
			self.assertEqual(rows, [])
			stock_ledger_calls = [
				args for args, _kwargs in db_sql.call_args_list if "tabStock Ledger Entry" in args[0]
			]
			self.assertEqual(stock_ledger_calls, [])

	def test_search_items_filters_by_customer_company_and_warehouse(self):
		def sql_side_effect(query, *args, **kwargs):
			if "tabStock Ledger Entry" in query:
				return [("ITEM-001", "Sample Item")]
			if "tabDocType" in query:
				params = args[0] if args else {}
				doctype_name = params.get("param1") if isinstance(params, dict) else "Item"
				return [(doctype_name,)]
			return []

		with patch(
			"cold_storage.cold_storage.utils.frappe.db.sql",
			side_effect=sql_side_effect,
		) as db_sql:
			rows = search_items_for_customer_stock(
				doctype="Item",
				txt="ITEM",
				searchfield="name",
				start=3,
				page_len=12,
				filters={"customer": "CUST-0001", "company": "Default Co", "warehouse": "Stores - CO"},
			)

		self.assertEqual(rows, [("ITEM-001", "Sample Item")])
		query, params = db_sql.call_args.args
		self.assertIn("b.custom_customer = %(customer)s", query)
		self.assertIn("w.company = %(company)s", query)
		self.assertIn("sle.warehouse = %(warehouse)s", query)
		self.assertEqual(params["customer"], "CUST-0001")
		self.assertEqual(params["company"], "Default Co")
		self.assertEqual(params["warehouse"], "Stores - CO")
		self.assertEqual(params["start"], 3)
		self.assertEqual(params["page_len"], 12)

	def test_search_warehouses_for_batch_returns_empty_without_batch(self):
		with patch("cold_storage.cold_storage.utils.frappe.db.sql") as db_sql:
			rows = search_warehouses_for_batch(
				doctype="Warehouse",
				txt="",
				searchfield="name",
				start=0,
				page_len=20,
				filters={
					"batch_no": "",
					"company": "Default Co",
					"customer": "CUST-0001",
					"item": "ITEM-001",
				},
			)
			self.assertEqual(rows, [])
			stock_ledger_calls = [
				args for args, _kwargs in db_sql.call_args_list if "tabStock Ledger Entry" in args[0]
			]
			self.assertEqual(stock_ledger_calls, [])

	def test_search_warehouses_for_batch_filters_by_batch_company_customer_item(self):
		with (
			patch(
				"cold_storage.cold_storage.utils.frappe.db.get_value",
				return_value={"custom_customer": "CUST-0001", "item": "ITEM-001"},
			),
			patch(
				"cold_storage.cold_storage.utils.frappe.db.sql",
				return_value=[("Stores - CO",), ("Spare - CO",)],
			) as db_sql,
			patch(
				"cold_storage.cold_storage.utils.get_batch_qty",
				side_effect=[0, 5],
			) as mocked_get_batch_qty,
		):
			rows = search_warehouses_for_batch(
				doctype="Warehouse",
				txt="Stores",
				searchfield="name",
				start=0,
				page_len=10,
				filters={
					"batch_no": "BATCH-0001",
					"company": "Default Co",
					"customer": "CUST-0001",
					"item": "ITEM-001",
				},
			)

		self.assertEqual(rows, [("Spare - CO",)])
		query, params = db_sql.call_args.args
		self.assertIn("from `tabWarehouse` w", query)
		self.assertIn("w.company = %(company)s", query)
		self.assertEqual(params["company"], "Default Co")
		self.assertEqual(params["scan_limit"], 100)
		self.assertEqual(mocked_get_batch_qty.call_count, 2)

	def test_search_warehouses_for_batch_returns_empty_on_customer_or_item_mismatch(self):
		with (
			patch(
				"cold_storage.cold_storage.utils.frappe.db.get_value",
				return_value={"custom_customer": "CUST-OTHER", "item": "ITEM-OTHER"},
			),
			patch("cold_storage.cold_storage.utils.frappe.db.sql") as db_sql,
			patch("cold_storage.cold_storage.utils.get_batch_qty") as mocked_get_batch_qty,
		):
			rows = search_warehouses_for_batch(
				doctype="Warehouse",
				txt="",
				searchfield="name",
				start=0,
				page_len=20,
				filters={
					"batch_no": "BATCH-0001",
					"company": "Default Co",
					"customer": "CUST-0001",
					"item": "ITEM-001",
				},
			)

		self.assertEqual(rows, [])
		db_sql.assert_not_called()
		mocked_get_batch_qty.assert_not_called()

	def test_get_document_qr_code_payload_returns_empty_when_document_is_missing(self):
		self.assertEqual(get_document_qr_code_payload("", "CS-IN-00001"), "")
		self.assertEqual(get_document_qr_code_payload("Cold Storage Inward", ""), "")

	def test_get_document_qr_code_payload_uses_form_url(self):
		with patch(
			"cold_storage.cold_storage.utils.frappe.utils.get_url_to_form",
			return_value="https://erp.example.com/app/cold-storage-inward/CS-IN-00001",
		) as get_url_to_form:
			payload = get_document_qr_code_payload("Cold Storage Inward", "CS-IN-00001")

		self.assertEqual(payload, "https://erp.example.com/app/cold-storage-inward/CS-IN-00001")
		get_url_to_form.assert_called_once_with("Cold Storage Inward", "CS-IN-00001")

	def test_get_document_qr_code_data_uri_returns_empty_without_payload(self):
		with patch(
			"cold_storage.cold_storage.utils.get_document_qr_code_payload",
			return_value="",
		):
			self.assertEqual(get_document_qr_code_data_uri("Cold Storage Inward", "CS-IN-00001"), "")

	def test_get_document_qr_code_data_uri_returns_svg_data_uri(self):
		with patch(
			"cold_storage.cold_storage.utils.get_document_qr_code_payload",
			return_value="https://erp.example.com/app/cold-storage-inward/CS-IN-00001",
		):
			data_uri = get_document_qr_code_data_uri(
				"Cold Storage Inward",
				"CS-IN-00001",
			)

		self.assertTrue(data_uri.startswith("data:image/svg+xml;base64,"))
		self.assertGreater(len(data_uri), len("data:image/svg+xml;base64,"))

	def test_get_document_sidebar_qr_code_payload_contains_required_fields(self):
		with (
			patch("cold_storage.cold_storage.utils.frappe.db.exists", return_value=True),
			patch(
				"cold_storage.cold_storage.utils.frappe.get_doc",
				return_value={
					"owner": "john@example.com",
					"posting_date": "2026-02-15",
					"receipt_no": "RCPT-0001",
					"customer": "CUST-0001",
					"total_qty": 12,
					"remarks": "Keep frozen at -18C",
					"items": [
						{
							"item": "ITEM-001",
							"batch_no": "BATCH-001",
							"warehouse": "Main - CO",
						}
					],
				},
			),
			patch("cold_storage.cold_storage.utils.frappe.db.get_value", return_value="John Doe"),
			patch(
				"cold_storage.cold_storage.utils.frappe.utils.get_url_to_form",
				return_value="https://erp.example.com/app/cold-storage-inward/CS-IN-00001",
			),
		):
			payload = get_document_sidebar_qr_code_payload("Cold Storage Inward", "CS-IN-00001")

		self.assertIn("Receipt #: RCPT-0001", payload)
		self.assertIn("Date: 2026-02-15", payload)
		self.assertIn("Customer: CUST-0001", payload)
		self.assertIn("Item: ITEM-001", payload)
		self.assertIn("Batch No: BATCH-001", payload)
		self.assertIn("Warehouse: Main - CO", payload)
		self.assertIn("Quantity: 12.0", payload)
		self.assertIn("Remarks: Keep frozen at -18C", payload)
		self.assertIn("Posted By: John Doe", payload)

	def test_get_document_sidebar_qr_code_data_uri_returns_svg_data_uri(self):
		with (
			patch("cold_storage.cold_storage.utils.frappe.has_permission", return_value=True),
			patch(
				"cold_storage.cold_storage.utils.get_document_sidebar_qr_code_payload",
				return_value="Document: Cold Storage Inward\nID: CS-IN-00001",
			),
		):
			data_uri = get_document_sidebar_qr_code_data_uri("Cold Storage Inward", "CS-IN-00001")

		self.assertTrue(data_uri.startswith("data:image/svg+xml;base64,"))
		self.assertGreater(len(data_uri), len("data:image/svg+xml;base64,"))
