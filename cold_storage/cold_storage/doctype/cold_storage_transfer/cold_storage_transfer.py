# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate


class ColdStorageTransfer(Document):
	# begin: auto-generated types
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from cold_storage.cold_storage.doctype.cold_storage_transfer_item.cold_storage_transfer_item import (
			ColdStorageTransferItem,
		)

		amended_from: DF.Link | None
		customer: DF.Link | None
		from_customer: DF.Link | None
		items: DF.Table[ColdStorageTransferItem]
		journal_entry: DF.Link | None
		naming_series: DF.Literal["CS-TR-.YYYY.-"]
		posting_date: DF.Date | None
		stock_entry: DF.Link | None
		to_customer: DF.Link | None
		total_qty: DF.Float
		total_transfer_charges: DF.Currency
		transfer_type: DF.Literal[
			"", "Ownership Transfer", "Inter-Warehouse Transfer", "Intra-Warehouse Transfer"
		]
	# end: auto-generated types

	def before_naming(self) -> None:
		from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
			get_default_company,
		)
		from cold_storage.cold_storage.naming import get_series_for_company

		self.company = self.company or get_default_company()
		self.naming_series = get_series_for_company("transfer", self.company)

	def validate(self) -> None:
		self._set_company()
		self._validate_transfer_type_fields()
		self._validate_items()
		self._fetch_rates()
		self._compute_totals()

	def _set_company(self) -> None:
		"""Restrict transaction company to Cold Storage Settings default company."""
		from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
			get_default_company,
		)

		default_company = get_default_company()
		if self.company and self.company != default_company:
			frappe.throw(
				_("Company must be {0} as configured in Cold Storage Settings").format(default_company)
			)
		self.company = default_company

	def on_submit(self) -> None:
		if self.transfer_type == "Ownership Transfer":
			self._create_stock_entry()
			self._process_ownership_transfer()
		else:
			self._create_stock_entry()
			self._process_location_transfer()

	def on_cancel(self) -> None:
		self._cancel_linked_docs()

	# ── Validations ──────────────────────────────────────────────

	def _validate_transfer_type_fields(self) -> None:
		if self.transfer_type == "Ownership Transfer":
			if self.from_customer == self.to_customer:
				frappe.throw(_("From Customer and To Customer cannot be the same"))

	def _validate_items(self) -> None:
		"""Validate batch ownership and warehouse per item row."""
		from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
			validate_warehouse_company,
		)
		from cold_storage.cold_storage.utils import get_batch_balance

		requested_qty_map: dict[tuple[str, str, str | None], dict[str, object]] = defaultdict(
			lambda: {"qty": 0.0, "rows": []}
		)

		for row in self.items:
			if self.transfer_type == "Ownership Transfer":
				if not row.source_warehouse:
					frappe.throw(
						_("Row {0}: Source Warehouse is required for Ownership Transfer").format(row.idx)
					)
				validate_warehouse_company(
					row.source_warehouse, self.company, row_idx=row.idx, label=_("Source Warehouse")
				)

			# Warehouse validation for location transfers
			if self.transfer_type in ["Inter-Warehouse Transfer", "Intra-Warehouse Transfer"]:
				if not row.source_warehouse:
					frappe.throw(
						_("Row {0}: Source Warehouse is required for {1}").format(row.idx, self.transfer_type)
					)
				validate_warehouse_company(
					row.source_warehouse, self.company, row_idx=row.idx, label=_("Source Warehouse")
				)

			if self.transfer_type == "Inter-Warehouse Transfer":
				if not row.target_warehouse:
					frappe.throw(
						_("Row {0}: Target Warehouse is required for Inter-Warehouse Transfer").format(
							row.idx
						)
					)
				validate_warehouse_company(
					row.target_warehouse, self.company, row_idx=row.idx, label=_("Target Warehouse")
				)
				if row.source_warehouse == row.target_warehouse:
					frappe.throw(_("Row {0}: Source and Target Warehouse must be different").format(row.idx))

			if self.transfer_type == "Intra-Warehouse Transfer":
				# In intra-warehouse transfer, target is always the same warehouse.
				row.target_warehouse = row.source_warehouse

			if not row.batch_no:
				continue

			batch_item = frappe.db.get_value("Batch", row.batch_no, "item")
			if batch_item and row.item and batch_item != row.item:
				frappe.throw(
					_("Row {0}: Batch {1} belongs to Item {2}, not {3}").format(
						row.idx, row.batch_no, batch_item, row.item
					)
				)

			batch_customer = frappe.db.get_value("Batch", row.batch_no, "custom_customer")
			if not batch_customer:
				frappe.throw(
					_("Row {0}: Batch {1} must have Customer set in Batch master").format(
						row.idx, row.batch_no
					)
				)
			if self.transfer_type == "Ownership Transfer":
				if batch_customer != self.from_customer:
					frappe.throw(
						_("Row {0}: Batch {1} does not belong to Customer {2}").format(
							row.idx, row.batch_no, self.from_customer
						)
					)
			else:
				customer = self.customer
				if batch_customer != customer:
					frappe.throw(
						_("Row {0}: Batch {1} does not belong to Customer {2}").format(
							row.idx, row.batch_no, customer
						)
					)

			key = (row.batch_no, row.source_warehouse, row.item)
			requested_qty_map[key]["qty"] = flt(requested_qty_map[key]["qty"]) + flt(getattr(row, "qty", 0))
			requested_qty_map[key]["rows"].append(row.idx)

		for (batch_no, source_warehouse, item_code), data in requested_qty_map.items():
			available_qty = flt(
				get_batch_balance(batch_no=batch_no, warehouse=source_warehouse, item_code=item_code)
			)
			requested_qty = flt(data["qty"])
			if requested_qty > available_qty:
				rows = ", ".join(str(idx) for idx in data["rows"])
				frappe.throw(
					_(
						"Rows {0}: Requested Qty {1} exceeds available Qty {2} for Batch {3} in Source Warehouse {4}"
					).format(rows, requested_qty, available_qty, batch_no, source_warehouse)
				)

	# ── Rate Fetching ────────────────────────────────────────────

	def _fetch_rates(self) -> None:
		if self.transfer_type == "Ownership Transfer":
			for row in self.items:
				row.transfer_rate = 0
				row.amount = 0
			return

		from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
			get_charge_rate,
		)

		rate_field = (
			"inter_warehouse_transfer_rate"
			if self.transfer_type == "Inter-Warehouse Transfer"
			else "intra_warehouse_transfer_rate"
		)
		for row in self.items:
			if row.item_group:
				row.transfer_rate = get_charge_rate(row.item_group, rate_field)
			row.amount = flt(row.qty) * flt(row.transfer_rate)

	def _compute_totals(self) -> None:
		self.total_qty = sum(flt(row.qty) for row in self.items)
		self.total_transfer_charges = sum(flt(row.amount) for row in self.items)

	# ── Stock Entry Creation ────────────────────────────────────

	@staticmethod
	def _get_stock_utils():
		from cold_storage.cold_storage import utils as stock_utils

		return stock_utils

	def _create_stock_entry(self) -> None:
		if self.stock_entry:
			return

		is_ownership_transfer = getattr(self, "transfer_type", None) == "Ownership Transfer"
		purpose = "Material Transfer"
		items: list[dict] = []
		if is_ownership_transfer:
			purpose = "Repack"
			for row in self.items:
				target_batch = ColdStorageTransfer._get_or_create_target_batch_for_ownership(self, row)
				items.extend(
					[
						{
							"item_code": row.item,
							"qty": row.qty,
							"uom": row.uom,
							"batch_no": row.batch_no,
							"s_warehouse": row.source_warehouse,
						},
						{
							"item_code": row.item,
							"qty": row.qty,
							"uom": row.uom,
							"batch_no": target_batch,
							"t_warehouse": row.source_warehouse,
						},
					]
				)
		else:
			for row in self.items:
				target_warehouse = row.target_warehouse
				if self.transfer_type == "Intra-Warehouse Transfer":
					target_warehouse = row.source_warehouse

				items.append(
					{
						"item_code": row.item,
						"qty": row.qty,
						"uom": row.uom,
						"batch_no": row.batch_no,
						"s_warehouse": row.source_warehouse,
						"t_warehouse": target_warehouse,
					}
				)

		stock_entry_name = ColdStorageTransfer._get_stock_utils().create_stock_entry_for_cold_storage(
			company=self.company,
			posting_date=self.posting_date,
			purpose=purpose,
			items=items,
			reference_doctype=self.doctype,
			reference_name=self.name,
		)

		self.db_set("stock_entry", stock_entry_name)
		frappe.msgprint(
			_("Stock Entry {0} created for transfer stock movement").format(
				frappe.utils.get_link_to_form("Stock Entry", stock_entry_name)
			),
			alert=True,
		)

		# ── Ownership Transfer ───────────────────────────────────────

	def _process_ownership_transfer(self) -> None:
		frappe.msgprint(
			_("Batch ownership transferred from {0} to {1} with batch transfer").format(
				self.from_customer, self.to_customer
			),
			alert=True,
		)

	def _get_or_create_target_batch_for_ownership(self, row) -> str:
		"""Create a to-customer batch for ownership transfer and return its name."""
		batch = frappe.get_doc("Batch", row.batch_no)
		customer_token = frappe.scrub(self.to_customer or "customer")
		base_batch_id = f"{batch.batch_id}-{customer_token}"[:120]
		batch_id = base_batch_id
		counter = 1
		while frappe.db.exists("Batch", batch_id):
			batch_id = f"{base_batch_id}-{counter}"[:140]
			counter += 1

		new_batch = frappe.new_doc("Batch")
		new_batch.batch_id = batch_id
		new_batch.item = batch.item
		new_batch.manufacturing_date = batch.manufacturing_date
		new_batch.expiry_date = batch.expiry_date
		new_batch.reference_doctype = self.doctype
		new_batch.reference_name = self.name
		new_batch.custom_customer = self.to_customer
		new_batch.flags.ignore_permissions = True
		new_batch.insert()
		return new_batch.name

	# ── Location Transfer ────────────────────────────────────────

	def _process_location_transfer(self) -> None:
		amount = flt(self.total_transfer_charges)
		if not amount:
			return

		from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
			get_settings,
		)

		settings = get_settings()
		debit_party = ColdStorageTransfer._get_party_details_for_account(
			self, settings.transfer_expense_account
		)
		credit_party = ColdStorageTransfer._get_party_details_for_account(
			self, settings.default_income_account
		)

		je = frappe.new_doc("Journal Entry")
		from cold_storage.cold_storage.naming import get_series_for_company

		je.naming_series = get_series_for_company("journal_entry", settings.company)
		je.posting_date = self.posting_date or nowdate()
		je.company = settings.company
		je.user_remark = _("{0} — {1}").format(self.transfer_type, self.name)

		je.append(
			"accounts",
			{
				"account": settings.transfer_expense_account,
				"debit_in_account_currency": amount,
				"cost_center": settings.cost_center,
				**debit_party,
			},
		)
		je.append(
			"accounts",
			{
				"account": settings.default_income_account,
				"credit_in_account_currency": amount,
				"cost_center": settings.cost_center,
				**credit_party,
			},
		)

		je.flags.ignore_permissions = True
		je.insert()
		je.submit()

		self.db_set("journal_entry", je.name)
		frappe.msgprint(
			_("Journal Entry {0} created for transfer charges").format(
				frappe.utils.get_link_to_form("Journal Entry", je.name)
			),
			alert=True,
		)

	def _get_party_details_for_account(self, account: str | None) -> dict:
		"""Return party fields required for receivable/payable accounts."""
		if not account:
			return {}

		account_type = frappe.db.get_value("Account", account, "account_type")
		if account_type == "Receivable":
			customer = self.customer
			if not customer:
				frappe.throw(_("Customer is required for receivable account {0}").format(account))
			return {"party_type": "Customer", "party": customer}

		if account_type == "Payable":
			frappe.throw(
				_(
					"Account {0} is Payable. Please configure a non-Payable account in Cold Storage Settings"
				).format(account)
			)

		return {}

	# ── Cancellation ─────────────────────────────────────────────

	def _cancel_linked_docs(self) -> None:
		stock_entry = getattr(self, "stock_entry", None)
		if ColdStorageTransfer._get_stock_utils().cancel_stock_entry_if_submitted(stock_entry):
			frappe.msgprint(_("Stock Entry {0} cancelled").format(stock_entry), alert=True)

		if self.transfer_type == "Ownership Transfer":
			self._delete_generated_target_batches_for_ownership()

		if not self.journal_entry:
			return

		je = frappe.get_doc("Journal Entry", self.journal_entry)
		if je.docstatus == 1:
			je.flags.ignore_permissions = True
			je.cancel()
			frappe.msgprint(_("Journal Entry {0} cancelled").format(self.journal_entry), alert=True)

	def _delete_generated_target_batches_for_ownership(self) -> None:
		"""Delete ownership-transfer target batches generated by this document."""
		generated_batches = frappe.get_all(
			"Batch",
			filters={
				"reference_doctype": self.doctype,
				"reference_name": self.name,
				"custom_customer": self.to_customer,
			},
			pluck="name",
		)
		if not generated_batches:
			return

		for batch_name in generated_batches:
			active_sle_count = frappe.db.count(
				"Stock Ledger Entry", {"batch_no": batch_name, "is_cancelled": 0}
			)
			if active_sle_count:
				frappe.throw(
					_("Cannot delete generated target Batch {0} because active stock ledger exists").format(
						batch_name
					)
				)
			frappe.delete_doc("Batch", batch_name, force=1, ignore_permissions=True)

		frappe.msgprint(
			_("Generated target Batch records deleted: {0}").format(", ".join(generated_batches)),
			alert=True,
		)
