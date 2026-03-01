# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

import json
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt
from frappe.utils.jinja import validate_template

DEFAULT_INWARD_TEMPLATE_BODY_PARAMS: tuple[str, ...] = (
	"{{ voucher_no }}",
	"{{ customer }}",
	"{{ posting_date }}",
	"{{ total_qty }}",
)
DEFAULT_OUTWARD_TEMPLATE_BODY_PARAMS: tuple[str, ...] = (
	"{{ voucher_no }}",
	"{{ customer }}",
	"{{ posting_date }}",
	"{{ total_qty }}",
)


class ColdStorageSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from cold_storage.cold_storage.doctype.charge_configuration.charge_configuration import ChargeConfiguration
		from cold_storage.cold_storage.doctype.cold_storage_dispatch_extra_charge.cold_storage_dispatch_extra_charge import ColdStorageDispatchExtraCharge
		from frappe.types import DF

		charge_configurations: DF.Table[ChargeConfiguration]
		company: DF.Link
		default_income_account: DF.Link
		default_uom: DF.Link
		dispatch_extra_charges: DF.Table[ColdStorageDispatchExtraCharge]
		dispatch_gst_account: DF.Link | None
		dispatch_gst_rate: DF.Percent
		enable_dispatch_gst_on_handling: DF.Check
		labour_account: DF.Link
		labour_manager_account: DF.Link
		portal_announcement: DF.SmallText | None
		storage_terms_and_conditions: DF.SmallText | None
		transfer_expense_account: DF.Link
		whatsapp_access_token: DF.Password | None
		whatsapp_api_version: DF.Data | None
		whatsapp_default_country_code: DF.Data | None
		whatsapp_enabled: DF.Check
		whatsapp_inward_template_body_params: DF.Code | None
		whatsapp_inward_template_name: DF.Data | None
		whatsapp_inward_text_template: DF.Code | None
		whatsapp_outward_template_body_params: DF.Code | None
		whatsapp_outward_template_name: DF.Data | None
		whatsapp_outward_text_template: DF.Code | None
		whatsapp_phone_number_id: DF.Data | None
		whatsapp_send_inward_on_submit: DF.Check
		whatsapp_send_outward_on_submit: DF.Check
		whatsapp_template_language: DF.Data | None
	# end: auto-generated types

	def validate(self) -> None:
		self._ensure_default_uom()
		self._validate_accounts_belong_to_company()
		self._validate_dispatch_gst_configuration()
		self._validate_dispatch_extra_charges_configuration()
		self._set_default_whatsapp_template_body_params()
		self._validate_whatsapp_configuration()

	def _set_default_whatsapp_template_body_params(self) -> None:
		"""Auto-fill template body params with Meta-compatible defaults when blank."""
		if not (self.whatsapp_inward_template_body_params or "").strip():
			self.whatsapp_inward_template_body_params = get_default_whatsapp_template_body_params_json(
				"Cold Storage Inward"
			)
		if not (self.whatsapp_outward_template_body_params or "").strip():
			self.whatsapp_outward_template_body_params = get_default_whatsapp_template_body_params_json(
				"Cold Storage Outward"
			)

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

	def _validate_dispatch_gst_configuration(self) -> None:
		"""Validate dispatch GST settings used for outward handling-only taxation."""
		if not cint(self.enable_dispatch_gst_on_handling):
			return

		if not self.dispatch_gst_account:
			frappe.throw(_("Dispatch GST Account is mandatory when Charge GST on Dispatch Handling is enabled"))

		dispatch_gst_rate = flt(self.dispatch_gst_rate)
		if dispatch_gst_rate <= 0:
			frappe.throw(_("Dispatch GST Rate must be greater than 0 when dispatch GST is enabled"))

		account_company = frappe.db.get_value("Account", self.dispatch_gst_account, "company")
		if account_company != self.company:
			frappe.throw(
				_("{0} ({1}) does not belong to Company {2}").format(
					_("Dispatch GST Account"), self.dispatch_gst_account, self.company
				)
			)

	def _validate_dispatch_extra_charges_configuration(self) -> None:
		"""Validate outward dispatch extra charge rows."""
		for row in self.dispatch_extra_charges or []:
			if not cint(row.is_active):
				continue

			charge_name = (row.charge_name or "").strip()
			if not charge_name:
				frappe.throw(_("Row {0}: Extra Charge Name is mandatory for active dispatch extra charge").format(row.idx))
			row.charge_name = charge_name

			description = (row.charge_description or "").strip()
			if not description:
				frappe.throw(_("Row {0}: Charge Description is mandatory for active dispatch extra charge").format(row.idx))
			row.charge_description = description

			if flt(row.charge_rate) <= 0:
				frappe.throw(_("Row {0}: Charge Rate (Per Qty) must be greater than 0").format(row.idx))

			if not row.credit_account:
				frappe.throw(_("Row {0}: Credit Account is mandatory for active dispatch extra charge").format(row.idx))

			credit_company = frappe.db.get_value("Account", row.credit_account, "company")
			if credit_company != self.company:
				frappe.throw(
					_("Row {0}: Credit Account {1} does not belong to Company {2}").format(
						row.idx, row.credit_account, self.company
					)
				)

	def _validate_whatsapp_configuration(self) -> None:
		"""Validate Meta WhatsApp configuration when integration is enabled."""
		if not cint(self.whatsapp_enabled):
			return

		missing: list[str] = []
		if not (self.whatsapp_phone_number_id or "").strip():
			missing.append(_("Phone Number ID"))
		if not (self.whatsapp_api_version or "").strip():
			missing.append(_("Meta Graph API Version"))
		if not self.get_password("whatsapp_access_token", raise_exception=False):
			missing.append(_("Permanent Access Token"))

		if missing:
			frappe.throw(
				_("Please configure {0} before enabling WhatsApp integration").format(
					", ".join(missing)
				)
			)

		api_version = (self.whatsapp_api_version or "").strip()
		if api_version and not re.fullmatch(r"v\d+\.\d+", api_version):
			frappe.throw(_("Meta Graph API Version must be in format v<major>.<minor> (example: v22.0)"))
		self.whatsapp_api_version = api_version

		phone_number_id = (self.whatsapp_phone_number_id or "").strip()
		if phone_number_id and not phone_number_id.isdigit():
			frappe.throw(_("Phone Number ID must contain digits only"))
		self.whatsapp_phone_number_id = phone_number_id

		country_code = (self.whatsapp_default_country_code or "").strip()
		if country_code:
			normalized_country_code = "".join(ch for ch in country_code if ch.isdigit())
			if not normalized_country_code:
				frappe.throw(_("Default Country Code must contain digits only"))
			self.whatsapp_default_country_code = normalized_country_code

		if self.whatsapp_template_language:
			self.whatsapp_template_language = self.whatsapp_template_language.strip()

		self._validate_whatsapp_message_templates()

	def _validate_whatsapp_message_templates(self) -> None:
		"""Validate Jinja message templates and JSON body-parameter overrides."""
		if self.whatsapp_inward_text_template:
			validate_template(self.whatsapp_inward_text_template)
		if self.whatsapp_outward_text_template:
			validate_template(self.whatsapp_outward_text_template)

		self._validate_template_body_params(
			fieldname="whatsapp_inward_template_body_params",
			label=_("Inward Template Body Params (JSON)"),
		)
		self._validate_template_body_params(
			fieldname="whatsapp_outward_template_body_params",
			label=_("Outward Template Body Params (JSON)"),
		)

	def _validate_template_body_params(self, *, fieldname: str, label: str) -> None:
		value = (self.get(fieldname) or "").strip()
		if not value:
			return

		try:
			payload = json.loads(value)
		except json.JSONDecodeError as exc:
			frappe.throw(_("{0} must be valid JSON. {1}").format(label, exc.msg))

		if not isinstance(payload, list):
			frappe.throw(_("{0} must be a JSON array of strings").format(label))

		for idx, entry in enumerate(payload, start=1):
			if not isinstance(entry, str):
				frappe.throw(_("{0}: row {1} must be a string").format(label, idx))
			validate_template(entry)


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


def get_default_whatsapp_template_body_params_json(doctype: str) -> str:
	"""Return default Meta template body params JSON for cold storage transactions."""
	default_map = {
		"Cold Storage Inward": DEFAULT_INWARD_TEMPLATE_BODY_PARAMS,
		"Cold Storage Outward": DEFAULT_OUTWARD_TEMPLATE_BODY_PARAMS,
	}
	params = default_map.get(doctype, DEFAULT_INWARD_TEMPLATE_BODY_PARAMS)
	return json.dumps(list(params), ensure_ascii=True)


def get_whatsapp_settings() -> dict[str, str | int | None]:
	"""Return WhatsApp (Meta Cloud API) settings scoped to the configured Cold Storage company."""
	settings = get_settings()
	return {
		"enabled": cint(settings.whatsapp_enabled),
		"company": settings.company,
		"api_version": settings.whatsapp_api_version or "v22.0",
		"phone_number_id": settings.whatsapp_phone_number_id or "",
		"access_token": settings.get_password("whatsapp_access_token", raise_exception=False) or "",
		"default_country_code": settings.whatsapp_default_country_code or "",
		"template_language": settings.whatsapp_template_language or "en",
		"inward_template_name": settings.whatsapp_inward_template_name or "",
		"inward_template_body_params": settings.whatsapp_inward_template_body_params
		or get_default_whatsapp_template_body_params_json("Cold Storage Inward"),
		"inward_text_template": settings.whatsapp_inward_text_template or "",
		"outward_template_name": settings.whatsapp_outward_template_name or "",
		"outward_template_body_params": settings.whatsapp_outward_template_body_params
		or get_default_whatsapp_template_body_params_json("Cold Storage Outward"),
		"outward_text_template": settings.whatsapp_outward_text_template or "",
		"send_inward_on_submit": cint(settings.whatsapp_send_inward_on_submit),
		"send_outward_on_submit": cint(settings.whatsapp_send_outward_on_submit),
	}


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


@frappe.whitelist()
def get_active_dispatch_extra_charges() -> list[dict[str, str | float | int]]:
	"""Return active dispatch extra charge rows from Cold Storage Settings."""
	settings = get_settings()
	rows: list[dict[str, str | float | int]] = []
	for row in settings.dispatch_extra_charges or []:
		if not cint(row.is_active):
			continue
		rows.append(
			{
				"is_active": 1,
				"charge_name": (row.charge_name or "").strip(),
				"charge_description": (row.charge_description or "").strip(),
				"charge_rate": float(row.charge_rate or 0),
				"credit_account": row.credit_account or "",
			}
		)
	return rows
