# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ColdStorageSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from cold_storage.cold_storage.doctype.charge_configuration.charge_configuration import (
			ChargeConfiguration,
		)

		charge_configurations: DF.Table[ChargeConfiguration]
		company: DF.Link | None
		cost_center: DF.Link | None
		default_income_account: DF.Link | None
		default_uom: DF.Link | None
		gst_template: DF.Link | None
		labour_account: DF.Link | None
		labour_manager_account: DF.Link | None
		transfer_expense_account: DF.Link | None
	# end: auto-generated types

	def validate(self) -> None:
		self._ensure_default_uom()
		self._validate_accounts_belong_to_company()
		self._validate_cost_center_belongs_to_company()
		self._validate_gst_template_company()

	def _ensure_default_uom(self) -> None:
		"""Keep default_uom linked to an existing UOM record."""
		if self.default_uom and frappe.db.exists("UOM", self.default_uom):
			return

		resolved_uom = resolve_default_uom(create_if_missing=False)
		if not resolved_uom:
			frappe.throw(_("Please create at least one UOM before saving Cold Storage Settings"))
		self.default_uom = resolved_uom

	def _validate_accounts_belong_to_company(self) -> None:
		"""Ensure all configured accounts belong to the selected company."""
		account_fields = [
			("labour_account", "Labour Account"),
			("labour_manager_account", "Labour Manager Account"),
			("transfer_expense_account", "Transfer Expense Account"),
			("default_income_account", "Default Income Account"),
		]
		for fieldname, label in account_fields:
			account = self.get(fieldname)
			if not account:
				continue
			account_company = frappe.db.get_value("Account", account, "company")
			if account_company != self.company:
				frappe.throw(
					frappe._("{0} ({1}) does not belong to Company {2}").format(label, account, self.company)
				)

	def _validate_cost_center_belongs_to_company(self) -> None:
		"""Ensure default cost center belongs to the selected company."""
		if not self.cost_center:
			return

		cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
		if cost_center_company != self.company:
			frappe.throw(
				_("{0} ({1}) does not belong to Company {2}").format(
					_("Default Cost Center"), self.cost_center, self.company
				)
			)

	def _validate_gst_template_company(self) -> None:
		"""Ensure GST template belongs to the selected company."""
		if not self.gst_template:
			return

		template_company = frappe.db.get_value(
			"Sales Taxes and Charges Template", self.gst_template, "company"
		)
		if template_company and template_company != self.company:
			frappe.throw(
				_("{0} ({1}) does not belong to Company {2}").format(
					_("GST Template"), self.gst_template, self.company
				)
			)


def get_settings() -> "ColdStorageSettings":
	"""Return the singleton Cold Storage Settings document."""
	return frappe.get_single("Cold Storage Settings")


def resolve_default_uom(*, create_if_missing: bool = False) -> str | None:
	"""Return a valid UOM for cold-storage transactions."""
	if frappe.db.exists("UOM", "Nos"):
		return "Nos"

	enabled_uom = frappe.db.get_value("UOM", {"enabled": 1}, "name")
	if enabled_uom:
		return enabled_uom

	any_uom = frappe.db.get_value("UOM", {}, "name")
	if any_uom:
		return any_uom

	if not create_if_missing:
		return None

	uom = frappe.get_doc(
		{
			"doctype": "UOM",
			"uom_name": "Nos",
			"enabled": 1,
			"must_be_whole_number": 1,
		}
	)
	uom.insert(ignore_permissions=True)
	return uom.name


def get_default_company() -> str:
	"""Return the default company configured for Cold Storage transactions."""
	company = get_settings().company
	if not company:
		frappe.throw(_("Please set Default Company in Cold Storage Settings"))
	return company


def validate_warehouse_company(
	warehouse: str | None,
	company: str,
	*,
	row_idx: int | None = None,
	label: str = "Warehouse",
) -> None:
	"""Validate that a warehouse belongs to the selected company."""
	if not warehouse:
		return

	warehouse_company = frappe.db.get_value("Warehouse", warehouse, "company")
	if warehouse_company and warehouse_company != company:
		prefix = _("Row {0}: ").format(row_idx) if row_idx else ""
		frappe.throw(_("{0}{1} {2} does not belong to Company {3}").format(prefix, label, warehouse, company))


def get_charge_rate(item_group: str, rate_field: str) -> float:
	"""Fetch a specific rate from the charge configuration table for the given Item Group.

	Args:
		item_group: The Item Group to look up.
		rate_field: One of 'unloading_rate', 'handling_rate', 'loading_rate',
		            'inter_warehouse_transfer_rate', 'intra_warehouse_transfer_rate'.

	Returns:
		The rate value, or 0.0 if no matching row is found.
	"""
	settings = get_settings()
	for row in settings.charge_configurations:
		if row.item_group == item_group:
			return float(row.get(rate_field) or 0)
	return 0.0


@frappe.whitelist()
def get_transfer_rate(item_group: str, transfer_type: str) -> float:
	"""Return transfer rate for Inter/Intra warehouse transfer from settings."""
	rate_field = {
		"Inter-Warehouse Transfer": "inter_warehouse_transfer_rate",
		"Intra-Warehouse Transfer": "intra_warehouse_transfer_rate",
	}.get(transfer_type)

	if not item_group or not rate_field:
		return 0.0

	return get_charge_rate(item_group, rate_field)


@frappe.whitelist()
def get_item_group_rates(item_group: str) -> dict[str, float]:
	"""Return configured charge rates for an item group."""
	if not item_group:
		return {
			"unloading_rate": 0.0,
			"handling_rate": 0.0,
			"loading_rate": 0.0,
			"inter_warehouse_transfer_rate": 0.0,
			"intra_warehouse_transfer_rate": 0.0,
		}

	return {
		"unloading_rate": get_charge_rate(item_group, "unloading_rate"),
		"handling_rate": get_charge_rate(item_group, "handling_rate"),
		"loading_rate": get_charge_rate(item_group, "loading_rate"),
		"inter_warehouse_transfer_rate": get_charge_rate(item_group, "inter_warehouse_transfer_rate"),
		"intra_warehouse_transfer_rate": get_charge_rate(item_group, "intra_warehouse_transfer_rate"),
	}
