# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, nowdate


class TestColdStorageIntegration(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self._ensure_batch_custom_customer_field()
		self._setup_test_context()
		self._setup_cold_storage_settings()

	def _ensure_batch_custom_customer_field(self) -> None:
		if frappe.get_meta("Batch").has_field("custom_customer"):
			return

		from cold_storage.install import after_migrate

		after_migrate()

	def _setup_test_context(self) -> None:
		self.company = frappe.db.get_value("Company", {}, "name", order_by="creation asc")
		if not self.company:
			self.skipTest("No Company found. Integration tests require at least one Company.")

		warehouses = frappe.get_all(
			"Warehouse",
			filters={"company": self.company, "is_group": 0},
			pluck="name",
			order_by="creation asc",
			limit=2,
		)
		if len(warehouses) < 2:
			self.skipTest("At least two non-group warehouses are required for transfer integration tests.")
		self.warehouse = warehouses[0]
		self.finished_warehouse = warehouses[1]

		self.cost_center = frappe.get_cached_value(
			"Company", self.company, "cost_center"
		) or frappe.db.get_value("Cost Center", {"company": self.company, "is_group": 0}, "name")
		self.income_account = frappe.db.get_value(
			"Account",
			{"company": self.company, "is_group": 0, "root_type": "Income"},
			"name",
		)
		self.expense_account = frappe.db.get_value(
			"Account",
			{"company": self.company, "is_group": 0, "root_type": "Expense"},
			"name",
		)
		self.uom = frappe.db.exists("UOM", "Nos") or frappe.db.get_value("UOM", {}, "name")

		if not all([self.cost_center, self.income_account, self.expense_account, self.uom]):
			self.skipTest("Missing setup prerequisites (cost center/income account/expense account/UOM).")

		self.customer_a = self._ensure_customer("CS Test Customer A")
		self.customer_b = self._ensure_customer("CS Test Customer B")

	def _ensure_customer(self, customer_name: str) -> str:
		if frappe.db.exists("Customer", customer_name):
			return customer_name

		customer = frappe.new_doc("Customer")
		customer.customer_name = customer_name
		customer.customer_type = "Individual"
		customer.customer_group = frappe.db.get_value("Customer Group", {}, "name")
		customer.territory = frappe.db.get_value("Territory", {}, "name")
		customer.save()
		return customer.name

	def _setup_cold_storage_settings(self) -> None:
		settings = frappe.get_single("Cold Storage Settings")
		settings.company = self.company
		settings.default_uom = self.uom
		settings.cost_center = self.cost_center
		settings.default_income_account = self.income_account
		settings.labour_account = self.expense_account
		settings.labour_manager_account = self.income_account
		settings.transfer_expense_account = self.expense_account
		settings.set("charge_configurations", [])
		settings.append(
			"charge_configurations",
			{
				"item_group": "Products",
				"unloading_rate": 5,
				"handling_rate": 4,
				"loading_rate": 3,
				"inter_warehouse_transfer_rate": 2,
				"intra_warehouse_transfer_rate": 1,
			},
		)
		settings.flags.ignore_permissions = True
		settings.save()

	def _make_batch_with_stock(
		self,
		*,
		customer: str | None,
		qty: float,
		warehouse: str | None = None,
	) -> tuple[str, str, str]:
		warehouse = warehouse or self.warehouse
		item = make_item(
			item_code=f"CS-ITEM-{frappe.generate_hash(length=8)}",
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"stock_uom": self.uom,
				"item_group": "Products",
			},
		)

		batch = frappe.new_doc("Batch")
		batch.batch_id = f"CS-BATCH-{frappe.generate_hash(length=8)}"
		batch.item = item.name
		if customer:
			batch.custom_customer = customer
		batch.insert()

		make_stock_entry(
			item_code=item.name,
			qty=flt(qty),
			company=self.company,
			to_warehouse=warehouse,
			rate=100,
			batch_no=batch.name,
			use_serial_batch_fields=1,
			cost_center=self.cost_center,
			expense_account=self.expense_account,
		)

		return item.name, batch.name, warehouse

	def _make_outward_doc(
		self, *, customer: str, item_code: str, batch_no: str, warehouse: str, row_qtys: list[float]
	):
		item_group = frappe.db.get_value("Item", item_code, "item_group")
		uom = frappe.db.get_value("Item", item_code, "stock_uom") or self.uom

		return frappe.get_doc(
			{
				"doctype": "Cold Storage Outward",
				"naming_series": "CS-OUT-.YYYY.-.####",
				"company": self.company,
				"customer": customer,
				"posting_date": nowdate(),
				"items": [
					{
						"item": item_code,
						"item_group": item_group,
						"batch_no": batch_no,
						"warehouse": warehouse,
						"qty": flt(qty),
						"uom": uom,
					}
					for qty in row_qtys
				],
			}
		)

	def _make_transfer_doc(
		self,
		*,
		transfer_type: str,
		item_code: str,
		batch_no: str,
		source_warehouse: str,
		qty: float,
		target_warehouse: str | None = None,
		customer: str | None = None,
		from_customer: str | None = None,
		to_customer: str | None = None,
	):
		item_group = frappe.db.get_value("Item", item_code, "item_group")
		uom = frappe.db.get_value("Item", item_code, "stock_uom") or self.uom

		return frappe.get_doc(
			{
				"doctype": "Cold Storage Transfer",
				"naming_series": "CS-TR-.YYYY.-.####",
				"company": self.company,
				"transfer_type": transfer_type,
				"posting_date": nowdate(),
				"customer": customer,
				"from_customer": from_customer,
				"to_customer": to_customer,
				"items": [
					{
						"item": item_code,
						"item_group": item_group,
						"batch_no": batch_no,
						"source_warehouse": source_warehouse,
						"target_warehouse": target_warehouse,
						"qty": flt(qty),
						"uom": uom,
					}
				],
			}
		)

	def test_outward_rejects_batch_without_customer(self):
		item_code, batch_no, warehouse = self._make_batch_with_stock(customer=None, qty=10)
		doc = self._make_outward_doc(
			customer=self.customer_a,
			item_code=item_code,
			batch_no=batch_no,
			warehouse=warehouse,
			row_qtys=[1],
		)

		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_outward_rejects_requested_qty_above_available_across_rows(self):
		item_code, batch_no, warehouse = self._make_batch_with_stock(customer=self.customer_a, qty=10)
		doc = self._make_outward_doc(
			customer=self.customer_a,
			item_code=item_code,
			batch_no=batch_no,
			warehouse=warehouse,
			row_qtys=[6, 6],
		)

		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_transfer_rejects_batch_without_customer(self):
		item_code, batch_no, source_warehouse = self._make_batch_with_stock(customer=None, qty=5)
		doc = self._make_transfer_doc(
			transfer_type="Inter-Warehouse Transfer",
			customer=self.customer_a,
			item_code=item_code,
			batch_no=batch_no,
			source_warehouse=source_warehouse,
			target_warehouse=self.finished_warehouse,
			qty=1,
		)

		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_transfer_rejects_requested_qty_above_available(self):
		item_code, batch_no, source_warehouse = self._make_batch_with_stock(customer=self.customer_a, qty=5)
		doc = self._make_transfer_doc(
			transfer_type="Inter-Warehouse Transfer",
			customer=self.customer_a,
			item_code=item_code,
			batch_no=batch_no,
			source_warehouse=source_warehouse,
			target_warehouse=self.finished_warehouse,
			qty=6,
		)

		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_ownership_transfer_cancel_deletes_generated_target_batches(self):
		item_code, batch_no, source_warehouse = self._make_batch_with_stock(customer=self.customer_a, qty=8)
		doc = self._make_transfer_doc(
			transfer_type="Ownership Transfer",
			from_customer=self.customer_a,
			to_customer=self.customer_b,
			item_code=item_code,
			batch_no=batch_no,
			source_warehouse=source_warehouse,
			qty=3,
		)
		doc.insert()
		doc.submit()

		generated_batches = frappe.get_all(
			"Batch",
			filters={
				"reference_doctype": "Cold Storage Transfer",
				"reference_name": doc.name,
				"custom_customer": self.customer_b,
			},
			pluck="name",
		)
		self.assertTrue(generated_batches)

		doc.cancel()

		self.assertEqual(frappe.db.get_value("Stock Entry", doc.stock_entry, "docstatus"), 2)
		for generated_batch in generated_batches:
			self.assertFalse(frappe.db.exists("Batch", generated_batch))
