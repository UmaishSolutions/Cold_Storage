# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate


class ColdStorageInward(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from cold_storage.cold_storage.doctype.cold_storage_inward_item.cold_storage_inward_item import ColdStorageInwardItem
		from frappe.types import DF

		amended_from: DF.Link | None
		company: DF.Link
		customer: DF.Link
		items: DF.Table[ColdStorageInwardItem]
		journal_entry: DF.Link | None
		naming_series: DF.Literal["CS-IN-.YYYY.-"]
		posting_date: DF.Date
		receipt_no: DF.Data | None
		remarks: DF.SmallText | None
		sales_invoice: DF.Link | None
		stock_entry: DF.Link | None
		submitted_qr_code_data_uri: DF.SmallText | None
		total_qty: DF.Float
		total_unloading_charges: DF.Currency
	# end: auto-generated types

	def before_naming(self) -> None:
		from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
			get_default_company,
		)
		from cold_storage.cold_storage.naming import get_series_for_company

		self.company = self.company or get_default_company()
		self.naming_series = get_series_for_company("inward", self.company)

	def validate(self) -> None:
		self._set_company()
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
		self._store_submitted_qr_code_data_uri()
		self._create_stock_entry()
		self._create_sales_invoice()
		self._create_labour_journal_entry()
		self._enqueue_whatsapp_notification()

	def on_cancel(self) -> None:
		self._cancel_linked_docs()

	# ── Validations ──────────────────────────────────────────────

	def _validate_items(self) -> None:
		"""Validate each item row: batch belongs to customer."""
		from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
			validate_warehouse_company,
		)

		for row in self.items:
			validate_warehouse_company(getattr(row, "warehouse", None), self.company, row_idx=row.idx)
			if not row.rack:
				frappe.throw(_("Row {0}: Rack is mandatory").format(row.idx))
			rack_warehouse = frappe.db.get_value("Cold Storage Rack", row.rack, "warehouse")
			if not rack_warehouse:
				frappe.throw(_("Row {0}: Rack {1} does not exist").format(row.idx, row.rack))
			if rack_warehouse != row.warehouse:
				frappe.throw(
					_("Row {0}: Rack {1} does not belong to Warehouse {2}").format(
						row.idx, row.rack, row.warehouse
					)
				)
			rack_active = frappe.db.get_value("Cold Storage Rack", row.rack, "is_active")
			if not rack_active:
				frappe.throw(_("Row {0}: Rack {1} is inactive").format(row.idx, row.rack))

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
			if batch_customer and batch_customer != self.customer:
				frappe.throw(
					_("Row {0}: Batch {1} belongs to Customer {2}, not {3}").format(
						row.idx, row.batch_no, batch_customer, self.customer
					)
				)

	# ── Rate Fetching ────────────────────────────────────────────

	def _fetch_rates(self) -> None:
		"""Fetch unloading rate from Settings for rows where rate is not set."""
		from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
			get_charge_rate,
		)

		for row in self.items:
			if row.item_group:
				row.unloading_rate = get_charge_rate(row.item_group, "unloading_rate")
			row.amount = flt(row.qty) * flt(row.unloading_rate)

	def _compute_totals(self) -> None:
		self.total_qty = sum(flt(row.qty) for row in self.items)
		self.total_unloading_charges = sum(flt(row.amount) for row in self.items)

	# ── Stock Entry Creation ────────────────────────────────────

	@staticmethod
	def _get_stock_utils():
		from cold_storage.cold_storage import utils as stock_utils

		return stock_utils

	def _create_stock_entry(self) -> None:
		if self.stock_entry:
			return

		items = [
			{
				"item_code": row.item,
				"qty": row.qty,
				"uom": row.uom,
				"batch_no": row.batch_no,
				"t_warehouse": row.warehouse,
			}
			for row in self.items
		]

		stock_entry_name = ColdStorageInward._get_stock_utils().create_stock_entry_for_cold_storage(
			company=self.company,
			posting_date=self.posting_date,
			purpose="Material Receipt",
			items=items,
			reference_doctype=self.doctype,
			reference_name=self.name,
		)

		self.db_set("stock_entry", stock_entry_name)
		frappe.msgprint(
			_("Stock Entry {0} created for inward stock movement").format(
				frappe.utils.get_link_to_form("Stock Entry", stock_entry_name)
			),
			alert=True,
		)

	# ── Sales Invoice Creation ───────────────────────────────────

	def _create_sales_invoice(self) -> None:
		"""Create a Sales Invoice with one line per item row for unloading charges."""
		from cold_storage.cold_storage.doctype.cold_storage_settings import (
			cold_storage_settings as cs_settings,
		)

		settings = cs_settings.get_settings()
		resolve_default_uom = getattr(cs_settings, "resolve_default_uom", None)
		invoice_uom = (
			resolve_default_uom(create_if_missing=False) if callable(resolve_default_uom) else None
		) or settings.default_uom
		if not invoice_uom:
			frappe.throw(_("Please configure at least one UOM before invoicing inward charges"))

		si = frappe.new_doc("Sales Invoice")
		from cold_storage.cold_storage.naming import get_series_for_company

		si.naming_series = get_series_for_company("sales_invoice", settings.company)
		si.customer = self.customer
		si.company = settings.company
		si.posting_date = self.posting_date or nowdate()
		si.due_date = si.posting_date
		si.set_posting_time = 1
		company_cost_center = frappe.get_cached_value("Company", settings.company, "cost_center")

		for row in self.items:
			si.append(
				"items",
				{
					"item_name": _("Unloading — {0} ({1})").format(row.item_name or row.item, row.batch_no),
					"description": _("Unloading charges for Batch {0}, Qty {1}").format(
						row.batch_no, row.qty
					),
					"qty": row.qty,
					"rate": row.unloading_rate,
					"uom": row.uom or invoice_uom,
					"income_account": settings.default_income_account,
					"cost_center": company_cost_center,
				},
			)

		si.flags.ignore_permissions = True
		si.insert()
		si.submit()

		self.db_set("sales_invoice", si.name)
		frappe.msgprint(
			_("Sales Invoice {0} created for unloading charges").format(
				frappe.utils.get_link_to_form("Sales Invoice", si.name)
			),
			alert=True,
		)

	# ── Labour Journal Entry ─────────────────────────────────────

	def _create_labour_journal_entry(self) -> None:
		"""Create a Journal Entry: Debit Labour Account, Credit Labour Manager Account."""
		from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
			get_settings,
		)

		settings = get_settings()
		amount = flt(self.total_unloading_charges)
		debit_party = ColdStorageInward._get_party_details_for_account(
			self, settings.labour_account, settings.company
		)
		credit_party = ColdStorageInward._get_party_details_for_account(
			self, settings.labour_manager_account, settings.company
		)

		if not amount:
			return

		je = frappe.new_doc("Journal Entry")
		from cold_storage.cold_storage.naming import get_series_for_company

		je.naming_series = get_series_for_company("journal_entry", settings.company)
		je.posting_date = self.posting_date or nowdate()
		je.company = settings.company
		je.user_remark = _("Labour charges for Inward {0}").format(self.name)
		company_cost_center = frappe.get_cached_value("Company", settings.company, "cost_center")

		je.append(
			"accounts",
			{
				"account": settings.labour_account,
				"debit_in_account_currency": amount,
				"cost_center": company_cost_center,
				**debit_party,
			},
		)
		je.append(
			"accounts",
			{
				"account": settings.labour_manager_account,
				"credit_in_account_currency": amount,
				"cost_center": company_cost_center,
				**credit_party,
			},
		)

		je.flags.ignore_permissions = True
		je.insert()
		je.submit()

		self.db_set("journal_entry", je.name)
		frappe.msgprint(
			_("Journal Entry {0} created for labour charges").format(
				frappe.utils.get_link_to_form("Journal Entry", je.name)
			),
			alert=True,
		)

	def _get_party_details_for_account(self, account: str | None, company: str | None = None) -> dict:
		"""Return party fields required for receivable/payable accounts."""
		if not account:
			return {}

		account_type = frappe.db.get_value("Account", account, "account_type")
		if account_type == "Receivable":
			if not self.customer:
				frappe.throw(_("Customer is required for receivable account {0}").format(account))
			return {"party_type": "Customer", "party": self.customer}

		if account_type == "Payable":
			supplier = self._resolve_supplier_for_payable_account(account, company)
			if supplier:
				return {"party_type": "Supplier", "party": supplier}
			frappe.throw(
				_(
					"Account {0} is Payable and needs Supplier party mapping. "
					"Map this account in Supplier > Accounts for company {1}, "
					"or configure a non-Payable account in Cold Storage Settings"
				).format(account, company or _("(Not Set)"))
			)

		return {}

	def _resolve_supplier_for_payable_account(self, account: str, company: str | None = None) -> str | None:
		"""Resolve Supplier for a payable account using Supplier > Accounts mapping."""
		filters: dict[str, str] = {"parenttype": "Supplier", "account": account}
		if company:
			filters["company"] = company

		suppliers = sorted(
			{
				supplier
				for supplier in frappe.get_all("Party Account", filters=filters, pluck="parent")
				if supplier
			}
		)
		if len(suppliers) == 1:
			return suppliers[0]
		if len(suppliers) > 1:
			frappe.throw(
				_(
					"Account {0} is mapped to multiple Suppliers in company {1}: {2}. "
					"Please keep a unique mapping or use a non-Payable account"
				).format(account, company or _("(Not Set)"), ", ".join(suppliers))
			)

		# Fallback: infer supplier from account name pattern "<Supplier> - <Company Abbr>".
		candidate_name = account.rsplit(" - ", 1)[0].strip()
		if candidate_name and frappe.db.exists("Supplier", candidate_name):
			return candidate_name

		if candidate_name:
			candidates = frappe.get_all("Supplier", filters={"supplier_name": candidate_name}, pluck="name")
			if len(candidates) == 1:
				return candidates[0]

		return None

	# ── Cancellation ─────────────────────────────────────────────

	def _cancel_linked_docs(self) -> None:
		if ColdStorageInward._get_stock_utils().cancel_stock_entry_if_submitted(self.get("stock_entry")):
			frappe.msgprint(_("Stock Entry {0} cancelled").format(self.stock_entry), alert=True)

		for field, doctype in [
			("sales_invoice", "Sales Invoice"),
			("journal_entry", "Journal Entry"),
		]:
			linked_name = self.get(field)
			if not linked_name:
				continue
			linked_doc = frappe.get_doc(doctype, linked_name)
			if linked_doc.docstatus == 1:
				linked_doc.flags.ignore_permissions = True
				linked_doc.cancel()
				frappe.msgprint(_("{0} {1} cancelled").format(doctype, linked_name), alert=True)

	def _enqueue_whatsapp_notification(self) -> None:
		"""Queue WhatsApp notification after submit without blocking core transaction."""
		try:
			from cold_storage.cold_storage.integrations.whatsapp import (
				enqueue_document_whatsapp_notification,
			)

			enqueue_document_whatsapp_notification(self.doctype, self.name)
		except Exception:
			frappe.log_error(
				title=_("Cold Storage Inward WhatsApp Enqueue Failed"),
				message=frappe.get_traceback(),
			)

	def _store_submitted_qr_code_data_uri(self) -> None:
		"""Persist a QR image at submit time so print formats never regenerate it."""
		try:
			from cold_storage.cold_storage.utils import get_document_sidebar_qr_code_data_uri

			qr_data_uri = get_document_sidebar_qr_code_data_uri(self.doctype, self.name, scale=3)
			if not qr_data_uri:
				return

			self.submitted_qr_code_data_uri = qr_data_uri
			self.db_set("submitted_qr_code_data_uri", qr_data_uri, update_modified=False)
		except Exception:
			frappe.log_error(
				title=_("Cold Storage Inward QR Cache Failed"),
				message=frappe.get_traceback(),
			)
