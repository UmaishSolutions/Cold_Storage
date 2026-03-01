# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, nowdate


class ColdStorageOutward(Document):
	# begin: auto-generated types
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from cold_storage.cold_storage.doctype.cold_storage_dispatch_extra_charge.cold_storage_dispatch_extra_charge import (
			ColdStorageDispatchExtraCharge,
		)
		from cold_storage.cold_storage.doctype.cold_storage_outward_item.cold_storage_outward_item import (
			ColdStorageOutwardItem,
		)

		amended_from: DF.Link | None
		apply_dispatch_extra_charges: DF.Check
		apply_dispatch_gst: DF.Check
		customer: DF.Link | None
		dispatch_selected_extra_charges_json: DF.LongText | None
		items: DF.Table[ColdStorageOutwardItem]
		naming_series: DF.Literal["CS-OUT-.YYYY.-"]
		posting_date: DF.Date | None
		sales_invoice: DF.Link | None
		selected_dispatch_extra_charges: DF.SmallText | None
		select_dispatch_extra_charges: DF.Button | None
		stock_entry: DF.Link | None
		submitted_qr_code_data_uri: DF.SmallText | None
		total_gst_charges: DF.Currency
		total_selected_extra_charges: DF.Currency
		total_charges: DF.Currency
		total_qty: DF.Float
	# end: auto-generated types

	def before_naming(self) -> None:
		from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
			get_default_company,
		)
		from cold_storage.cold_storage.naming import get_series_for_company

		self.company = self.company or get_default_company()
		self.naming_series = get_series_for_company("outward", self.company)

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
		self._enqueue_whatsapp_notification()

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
			available_qty = flt(
				get_batch_balance(batch_no=batch_no, warehouse=warehouse, item_code=item_code)
			)
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
		self.total_gst_charges = self._calculate_total_gst_charges()

	def _calculate_total_gst_charges(self) -> float:
		"""Calculate GST amount on handling charges for display on dispatch."""
		if not cint(getattr(self, "apply_dispatch_gst", 1) or 1):
			return 0.0

		from cold_storage.cold_storage.doctype.cold_storage_settings import (
			cold_storage_settings as cs_settings,
		)

		settings = cs_settings.get_settings()
		if not cint(getattr(settings, "enable_dispatch_gst_on_handling", 0)):
			return 0.0

		dispatch_gst_rate = flt(getattr(settings, "dispatch_gst_rate", 0))
		if dispatch_gst_rate <= 0:
			return 0.0

		handling_charges = sum(
			flt(row.qty) * flt(row.handling_rate) for row in self.items if flt(row.handling_rate)
		)
		if handling_charges <= 0:
			return 0.0

		return flt(handling_charges * dispatch_gst_rate / 100.0)

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
		from cold_storage.cold_storage.doctype.cold_storage_settings import (
			cold_storage_settings as cs_settings,
		)

		settings = cs_settings.get_settings()
		resolve_default_uom = getattr(cs_settings, "resolve_default_uom", None)
		invoice_uom = (
			resolve_default_uom(create_if_missing=False) if callable(resolve_default_uom) else None
		) or settings.default_uom
		if not invoice_uom:
			frappe.throw(_("Please configure at least one UOM before invoicing dispatch charges"))

		si = frappe.new_doc("Sales Invoice")
		from cold_storage.cold_storage.naming import get_series_for_company

		si.naming_series = get_series_for_company("sales_invoice", settings.company)
		si.customer = self.customer
		si.company = settings.company
		si.posting_date = self.posting_date or nowdate()
		si.due_date = si.posting_date
		si.set_posting_time = 1
		company_cost_center = frappe.get_cached_value("Company", settings.company, "cost_center")
		attach_dispatch_gst, attach_dispatch_extra_charges = self._get_dispatch_charge_flags()

		for row in self.items:
			if flt(row.handling_rate):
				si.append(
					"items",
					{
						"item_name": _("Handling — {0} ({1})").format(
							row.item_name or row.item, row.batch_no
						),
						"description": _("Handling charges for Batch {0}, Qty {1}").format(
							row.batch_no, row.qty
						),
						"qty": row.qty,
						"rate": row.handling_rate,
						"uom": row.uom or invoice_uom,
						"income_account": settings.default_income_account,
						"cost_center": company_cost_center,
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
						"uom": row.uom or invoice_uom,
						"income_account": settings.default_income_account,
						"cost_center": company_cost_center,
					},
				)

		if attach_dispatch_extra_charges:
			self._append_dispatch_extra_charges(si, settings, invoice_uom, company_cost_center)

		if attach_dispatch_gst and cint(getattr(settings, "enable_dispatch_gst_on_handling", 0)):
			self._append_dispatch_gst_tax(si, settings)

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

	def _append_dispatch_extra_charges(self, si, settings, invoice_uom: str, company_cost_center: str | None):
		"""Append quantity-based extra dispatch charge lines from settings."""
		total_qty = sum(flt(row.qty) for row in self.items)
		if total_qty <= 0:
			return

		for charge_row in self._get_dispatch_extra_charge_rows(settings):
			if isinstance(charge_row, dict):
				row_get = charge_row.get
			else:
				row_get = lambda fieldname, default=None: getattr(charge_row, fieldname, default)

			if not cint(row_get("is_active", 0)):
				continue

			extra_rate = flt(row_get("charge_rate", 0))
			if extra_rate <= 0:
				continue

			extra_name = (row_get("charge_name", "") or "").strip()
			extra_description = (row_get("charge_description", "") or "").strip()
			if not extra_name and not extra_description:
				continue
			credit_account = row_get("credit_account", None)
			if not credit_account:
				continue

			label = extra_name or _("Extra Dispatch Charges")
			si.append(
				"items",
				{
					"item_name": label,
					"description": _("{0}{1} (Qty {2})").format(
						label,
						f" - {extra_description}" if extra_description else "",
						total_qty,
					),
					"qty": total_qty,
					"rate": extra_rate,
					"uom": invoice_uom,
					"income_account": credit_account,
					"cost_center": company_cost_center,
				},
			)

	def _get_dispatch_extra_charge_rows(self, settings):
		"""Return dispatch-specific selected rows, fallback to settings rows."""
		payload = (getattr(self, "dispatch_selected_extra_charges_json", None) or "").strip()
		if payload:
			try:
				rows = json.loads(payload)
			except json.JSONDecodeError:
				rows = []
			if isinstance(rows, list):
				return rows

		# Backward compatibility for older drafts where table field may exist.
		selected_rows = getattr(self, "dispatch_extra_charge_rows", None) or []
		return selected_rows or (getattr(settings, "dispatch_extra_charges", None) or [])

	def _get_dispatch_charge_flags(self) -> tuple[bool, bool]:
		"""Return (attach_gst, attach_extra_charges) flags for this dispatch."""
		if hasattr(self, "apply_dispatch_gst") and hasattr(self, "apply_dispatch_extra_charges"):
			return (
				cint(getattr(self, "apply_dispatch_gst", 1) or 1) == 1,
				cint(getattr(self, "apply_dispatch_extra_charges", 1) or 1) == 1,
			)

		# Backward compatibility fallback: derive from Customer if dispatch fields are unavailable.
		if not self.customer:
			return True, True

		apply_dispatch_gst, apply_dispatch_extra_charges = frappe.db.get_value(
			"Customer",
			self.customer,
			["custom_apply_dispatch_gst", "custom_apply_dispatch_extra_charges"],
		) or (None, None)

		return cint(apply_dispatch_gst) == 1, cint(apply_dispatch_extra_charges) == 1

	def _append_dispatch_gst_tax(self, si, settings) -> None:
		"""Apply GST only on dispatch handling charges as an explicit tax row."""
		dispatch_gst_account = getattr(settings, "dispatch_gst_account", None)
		dispatch_gst_rate = flt(getattr(settings, "dispatch_gst_rate", 0))
		if not dispatch_gst_account:
			frappe.throw(_("Please set Dispatch GST Account in Cold Storage Settings"))
		if dispatch_gst_rate <= 0:
			frappe.throw(_("Please set Dispatch GST Rate greater than 0 in Cold Storage Settings"))

		handling_charges = sum(
			flt(row.qty) * flt(row.handling_rate) for row in self.items if flt(row.handling_rate)
		)
		if handling_charges <= 0:
			return

		gst_amount = flt(handling_charges * dispatch_gst_rate / 100.0)
		si.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": dispatch_gst_account,
				"description": _("GST ({0}%) on Handling Charges").format(dispatch_gst_rate),
				"tax_amount": gst_amount,
				"cost_center": frappe.get_cached_value("Company", settings.company, "cost_center"),
			},
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

	def _enqueue_whatsapp_notification(self) -> None:
		"""Queue WhatsApp notification after submit without blocking core transaction."""
		try:
			from cold_storage.cold_storage.integrations.whatsapp import (
				enqueue_document_whatsapp_notification,
			)

			enqueue_document_whatsapp_notification(self.doctype, self.name)
		except Exception:
			frappe.log_error(
				title=_("Cold Storage Outward WhatsApp Enqueue Failed"),
				message=frappe.get_traceback(),
			)

	def _store_submitted_qr_code_data_uri(self) -> None:
		"""Persist a QR image at submit time so print/sidebar can reuse it."""
		try:
			from cold_storage.cold_storage.utils import get_document_sidebar_qr_code_data_uri

			qr_data_uri = get_document_sidebar_qr_code_data_uri(self.doctype, self.name, scale=3)
			if not qr_data_uri:
				return

			self.submitted_qr_code_data_uri = qr_data_uri
			self.db_set("submitted_qr_code_data_uri", qr_data_uri, update_modified=False)
		except Exception:
			frappe.log_error(
				title=_("Cold Storage Outward QR Cache Failed"),
				message=frappe.get_traceback(),
			)
