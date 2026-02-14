# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from collections import defaultdict


class ColdStorageOutward(Document):
	# begin: auto-generated types
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from cold_storage.cold_storage.doctype.cold_storage_outward_item.cold_storage_outward_item import (
			ColdStorageOutwardItem,
		)

		amended_from: DF.Link | None
		customer: DF.Link | None
		items: DF.Table[ColdStorageOutwardItem]
		naming_series: DF.Literal["CS-OUT-.YYYY.-"]
		posting_date: DF.Date | None
		sales_invoice: DF.Link | None
		stock_entry: DF.Link | None
		total_charges: DF.Currency
		total_qty: DF.Float
	# end: auto-generated types

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
		self._create_stock_entry()
		self._create_sales_invoice()

	def on_cancel(self) -> None:
		self._cancel_linked_docs()

	# ── Validations ──────────────────────────────────────────────

	def _validate_items(self) -> None:
		from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
			validate_warehouse_company,
		)
		from cold_storage.cold_storage.utils import get_batch_balance

		requested_qty_map: dict[tuple[str, str, str | None], dict[str, object]] = defaultdict(
			lambda: {"qty": 0.0, "rows": []}
		)

		for row in self.items:
			validate_warehouse_company(getattr(row, "warehouse", None), self.company, row_idx=row.idx)

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
			if batch_customer != self.customer:
				frappe.throw(
					_("Row {0}: Batch {1} belongs to Customer {2}, not {3}").format(
						row.idx, row.batch_no, batch_customer, self.customer
					)
				)

			key = (row.batch_no, row.warehouse, row.item)
			requested_qty_map[key]["qty"] = flt(requested_qty_map[key]["qty"]) + flt(getattr(row, "qty", 0))
			requested_qty_map[key]["rows"].append(row.idx)

		for (batch_no, warehouse, item_code), data in requested_qty_map.items():
			available_qty = flt(get_batch_balance(batch_no=batch_no, warehouse=warehouse, item_code=item_code))
			requested_qty = flt(data["qty"])
			if requested_qty > available_qty:
				rows = ", ".join(str(idx) for idx in data["rows"])
				frappe.throw(
					_(
						"Rows {0}: Requested Qty {1} exceeds available Qty {2} for Batch {3} in Warehouse {4}"
					).format(rows, requested_qty, available_qty, batch_no, warehouse)
				)

	# ── Rate Fetching ────────────────────────────────────────────

	def _fetch_rates(self) -> None:
		from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
			get_charge_rate,
		)

		for row in self.items:
			if row.item_group:
				row.handling_rate = get_charge_rate(row.item_group, "handling_rate")
				row.loading_rate = get_charge_rate(row.item_group, "loading_rate")
			row.amount = flt(row.qty) * (flt(row.handling_rate) + flt(row.loading_rate))

	def _compute_totals(self) -> None:
		self.total_qty = sum(flt(row.qty) for row in self.items)
		self.total_charges = sum(flt(row.amount) for row in self.items)

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
				"s_warehouse": row.warehouse,
			}
			for row in self.items
		]

		stock_entry_name = ColdStorageOutward._get_stock_utils().create_stock_entry_for_cold_storage(
			company=self.company,
			posting_date=self.posting_date,
			purpose="Material Issue",
			items=items,
			reference_doctype=self.doctype,
			reference_name=self.name,
		)

		self.db_set("stock_entry", stock_entry_name)
		frappe.msgprint(
			_("Stock Entry {0} created for outward stock movement").format(
				frappe.utils.get_link_to_form("Stock Entry", stock_entry_name)
			),
			alert=True,
		)

	# ── Sales Invoice Creation ───────────────────────────────────

	def _create_sales_invoice(self) -> None:
		from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
			get_settings,
		)

		settings = get_settings()

		si = frappe.new_doc("Sales Invoice")
		si.customer = self.customer
		si.company = settings.company
		si.posting_date = self.posting_date or nowdate()
		si.due_date = si.posting_date
		si.set_posting_time = 1

		for row in self.items:
			if flt(row.handling_rate):
				si.append(
					"items",
					{
						"item_name": _("Handling — {0} ({1})").format(row.item_name or row.item, row.batch_no),
						"description": _("Handling charges for Batch {0}, Qty {1}").format(
							row.batch_no, row.qty
						),
						"qty": row.qty,
						"rate": row.handling_rate,
						"uom": row.uom or settings.default_uom or "Nos",
						"income_account": settings.default_income_account,
						"cost_center": settings.cost_center,
					},
				)
			if flt(row.loading_rate):
				si.append(
					"items",
					{
						"item_name": _("Loading — {0} ({1})").format(row.item_name or row.item, row.batch_no),
						"description": _("Loading charges for Batch {0}, Qty {1}").format(
							row.batch_no, row.qty
						),
						"qty": row.qty,
						"rate": row.loading_rate,
						"uom": row.uom or settings.default_uom or "Nos",
						"income_account": settings.default_income_account,
						"cost_center": settings.cost_center,
					},
				)

		if settings.gst_template:
			si.taxes_and_charges = settings.gst_template
			si.set_taxes()

		si.flags.ignore_permissions = True
		si.insert()
		si.submit()

		self.db_set("sales_invoice", si.name)
		frappe.msgprint(
			_("Sales Invoice {0} created for dispatch charges").format(
				frappe.utils.get_link_to_form("Sales Invoice", si.name)
			),
			alert=True,
		)

	# ── Cancellation ─────────────────────────────────────────────

	def _cancel_linked_docs(self) -> None:
		if ColdStorageOutward._get_stock_utils().cancel_stock_entry_if_submitted(self.stock_entry):
			frappe.msgprint(_("Stock Entry {0} cancelled").format(self.stock_entry), alert=True)

		if not self.sales_invoice:
			return
		si = frappe.get_doc("Sales Invoice", self.sales_invoice)
		if si.docstatus == 1:
			si.flags.ignore_permissions = True
			si.cancel()
			frappe.msgprint(_("Sales Invoice {0} cancelled").format(self.sales_invoice), alert=True)
