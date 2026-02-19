# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import Any, TypedDict, cast

import frappe
from frappe import _
from frappe.integrations.utils import make_post_request
from frappe.utils import cint, cstr, flt, formatdate

from cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings import (
	get_whatsapp_settings,
)

META_GRAPH_BASE_URL = "https://graph.facebook.com"
DEFAULT_API_VERSION = "v22.0"
SUPPORTED_DOCTYPES = frozenset(("Cold Storage Inward", "Cold Storage Outward"))


class WhatsAppSettings(TypedDict):
	enabled: int
	company: str | None
	api_version: str
	phone_number_id: str
	access_token: str
	default_country_code: str
	template_language: str
	inward_template_name: str
	inward_template_body_params: str
	inward_text_template: str
	outward_template_name: str
	outward_template_body_params: str
	outward_text_template: str
	send_inward_on_submit: int
	send_outward_on_submit: int


@frappe.whitelist()
def send_whatsapp_test_message(to_number: str, message: str | None = None) -> dict[str, str]:
	"""Send a test WhatsApp message using Cold Storage company-scoped Meta credentials."""
	frappe.only_for(("System Manager", "Cold Storage Admin"))

	settings = _get_enabled_settings(raise_if_disabled=True)
	normalized_number = _normalize_phone_number(to_number, settings["default_country_code"])
	if not normalized_number:
		frappe.throw(_("Please provide a valid destination WhatsApp number"))

	response = _send_text_message(
		settings=settings,
		to_number=normalized_number,
		message=message
		or _(
			"This is a Cold Storage WhatsApp test message from company {0}."
		).format(settings["company"]),
	)

	return {
		"status": "sent",
		"to_number": normalized_number,
		"message_id": _extract_message_id(response),
	}


@frappe.whitelist()
def send_whatsapp_for_document(doctype: str, docname: str) -> dict[str, str]:
	"""Send WhatsApp notification for an eligible Cold Storage document on demand."""
	frappe.only_for(("System Manager", "Cold Storage Admin", "Cold Storage Warehouse Manager"))

	response = send_document_whatsapp_notification(
		doctype=doctype,
		docname=docname,
		raise_exceptions=True,
	)
	if not response:
		frappe.throw(_("WhatsApp notification could not be sent for this document"))
	return response


@frappe.whitelist()
def get_whatsapp_setup_status() -> dict[str, Any]:
	"""Return actionable readiness diagnostics for WhatsApp setup in Cold Storage Settings."""
	frappe.only_for(("System Manager", "Cold Storage Admin", "Cold Storage Warehouse Manager"))

	settings = cast(WhatsAppSettings, get_whatsapp_settings())
	missing_fields = _get_missing_configuration_fields(settings)
	warnings: list[str] = []

	if not cint(settings.get("enabled")):
		warnings.append(_("WhatsApp Integration is disabled in Cold Storage Settings"))

	if not cstr(settings.get("default_country_code")).strip():
		warnings.append(_("Default Country Code is empty. Local numbers without country code may fail"))

	for doctype, label in (
		("Cold Storage Inward", _("Inward")),
		("Cold Storage Outward", _("Outward")),
	):
		body_params = _get_template_body_params_config(doctype, settings)
		if body_params:
			try:
				if not _parse_template_param_entries(body_params):
					warnings.append(_("{0} template body params JSON is empty").format(label))
			except Exception as exc:
				warnings.append(_("{0} template body params JSON has an error: {1}").format(label, cstr(exc)))

		if not _get_template_name(doctype, settings) and not _get_text_template(doctype, settings):
			warnings.append(
				_("{0} notification will use default fallback text. Configure a custom message if required").format(
					label
				)
			)

	api_version = cstr(settings.get("api_version")).strip() or DEFAULT_API_VERSION
	phone_number_id = cstr(settings.get("phone_number_id")).strip()
	endpoint = (
		f"{META_GRAPH_BASE_URL}/{api_version}/{phone_number_id}/messages" if phone_number_id else ""
	)
	enabled = bool(cint(settings.get("enabled")))

	return {
		"enabled": cint(settings.get("enabled")),
		"ready": enabled and not missing_fields,
		"company": cstr(settings.get("company")).strip(),
		"missing_fields": missing_fields,
		"warnings": warnings,
		"endpoint": endpoint,
	}


def enqueue_document_whatsapp_notification(doctype: str, docname: str) -> None:
	"""Queue WhatsApp notification to run after DB commit for submit events."""
	if doctype not in SUPPORTED_DOCTYPES:
		return

	frappe.enqueue(
		"cold_storage.cold_storage.integrations.whatsapp.send_document_whatsapp_notification",
		queue="short",
		enqueue_after_commit=True,
		doctype=doctype,
		docname=docname,
	)


def send_document_whatsapp_notification(
	doctype: str,
	docname: str,
	*,
	raise_exceptions: bool = False,
) -> dict[str, str] | None:
	"""Send a WhatsApp notification for submitted Inward/Outward documents."""
	if doctype not in SUPPORTED_DOCTYPES:
		if raise_exceptions:
			frappe.throw(_("Unsupported doctype for WhatsApp notification: {0}").format(doctype))
		return None

	try:
		settings = _get_enabled_settings(raise_if_disabled=raise_exceptions)
		if not settings:
			return None

		doc = frappe.get_doc(doctype, docname)
		if _is_doctype_notification_disabled(doctype, settings):
			return None

		doc_company = cstr(doc.get("company")).strip()
		_ensure_company_scope(doc_company, cstr(settings["company"]).strip())

		customer = cstr(doc.get("customer")).strip()
		if not customer:
			if raise_exceptions:
				frappe.throw(_("Customer is required to send WhatsApp notifications"))
			return None

		raw_mobile = _get_customer_mobile(customer)
		normalized_number = _normalize_phone_number(raw_mobile, settings["default_country_code"])
		if not normalized_number:
			if raise_exceptions:
				frappe.throw(
					_("No valid mobile number found for customer {0}").format(customer)
				)
			return None

		template_name = _get_template_name(doctype, settings)
		if template_name:
			response = _send_template_message(
				settings=settings,
				to_number=normalized_number,
				template_name=template_name,
				language_code=settings["template_language"],
				body_parameters=_build_template_parameters(doc, doctype, settings),
			)
		else:
			response = _send_text_message(
				settings=settings,
				to_number=normalized_number,
				message=_build_document_message(doc, doctype, settings),
			)

		message_id = _extract_message_id(response)
		return {
			"status": "sent",
			"doctype": doctype,
			"docname": docname,
			"to_number": normalized_number,
			"message_id": message_id,
		}
	except Exception:
		if raise_exceptions:
			raise
		frappe.log_error(
			title=_("Cold Storage WhatsApp Notification Failed"),
			message=frappe.get_traceback(),
		)
		return None


def _get_enabled_settings(*, raise_if_disabled: bool = False) -> WhatsAppSettings | None:
	settings = cast(WhatsAppSettings, get_whatsapp_settings())

	if not settings["enabled"]:
		if raise_if_disabled:
			frappe.throw(_("Enable WhatsApp Integration in Cold Storage Settings"))
		return None

	missing = _get_missing_configuration_fields(settings)

	if missing:
		if raise_if_disabled:
			frappe.throw(_("Missing WhatsApp configuration: {0}").format(", ".join(missing)))
		return None

	return settings


def _get_missing_configuration_fields(settings: WhatsAppSettings) -> list[str]:
	missing: list[str] = []
	if not cstr(settings.get("phone_number_id")).strip():
		missing.append(_("Phone Number ID"))
	if not cstr(settings.get("access_token")).strip():
		missing.append(_("Permanent Access Token"))
	if not cstr(settings.get("api_version")).strip():
		missing.append(_("Meta Graph API Version"))
	return missing


def _ensure_company_scope(document_company: str, configured_company: str) -> None:
	"""Ensure WhatsApp integration is limited to Cold Storage configured company."""
	if not configured_company:
		frappe.throw(_("Default Company is not configured in Cold Storage Settings"))
	if document_company and document_company != configured_company:
		frappe.throw(
			_(
				"WhatsApp integration is restricted to company {0}. Document company {1} is not allowed"
			).format(configured_company, document_company)
		)


def _is_doctype_notification_disabled(doctype: str, settings: WhatsAppSettings) -> bool:
	if doctype == "Cold Storage Inward":
		return not settings["send_inward_on_submit"]
	if doctype == "Cold Storage Outward":
		return not settings["send_outward_on_submit"]
	return True


def _get_template_name(doctype: str, settings: WhatsAppSettings) -> str:
	if doctype == "Cold Storage Inward":
		return cstr(settings["inward_template_name"]).strip()
	if doctype == "Cold Storage Outward":
		return cstr(settings["outward_template_name"]).strip()
	return ""


def _get_template_body_params_config(doctype: str, settings: WhatsAppSettings) -> str:
	if doctype == "Cold Storage Inward":
		return cstr(settings.get("inward_template_body_params", "")).strip()
	if doctype == "Cold Storage Outward":
		return cstr(settings.get("outward_template_body_params", "")).strip()
	return ""

def _get_text_template(doctype: str, settings: WhatsAppSettings) -> str:
	if doctype == "Cold Storage Inward":
		return cstr(settings.get("inward_text_template", "")).strip()
	if doctype == "Cold Storage Outward":
		return cstr(settings.get("outward_text_template", "")).strip()
	return ""


def _build_template_parameters(doc: Any, doctype: str, settings: WhatsAppSettings) -> list[str]:
	configured_params = _get_template_body_params_config(doctype, settings)
	if configured_params:
		entries = _parse_template_param_entries(configured_params)
		return [_render_jinja_template(entry, doc) for entry in entries]

	return [
		cstr(doc.name),
		cstr(doc.get("customer")),
		formatdate(doc.get("posting_date")),
		str(flt(doc.get("total_qty"))),
	]


def _build_document_message(doc: Any, doctype: str, settings: WhatsAppSettings) -> str:
	custom_template = _get_text_template(doctype, settings)
	if custom_template:
		rendered = _render_jinja_template(custom_template, doc).strip()
		if rendered:
			return rendered

	doc_type_label = "Inward" if doc.doctype == "Cold Storage Inward" else "Outward"
	return _(
		"Cold Storage {0} submitted\n"
		"Company: {1}\n"
		"Voucher: {2}\n"
		"Customer: {3}\n"
		"Posting Date: {4}\n"
		"Total Qty: {5}"
	).format(
		doc_type_label,
		cstr(doc.get("company")),
		cstr(doc.name),
		cstr(doc.get("customer")),
		formatdate(doc.get("posting_date")),
		flt(doc.get("total_qty")),
	)


def _parse_template_param_entries(value: str) -> list[str]:
	try:
		payload = json.loads(value)
	except json.JSONDecodeError as exc:
		frappe.throw(_("Template body params must be valid JSON. {0}").format(exc.msg))

	if not isinstance(payload, list):
		frappe.throw(_("Template body params must be a JSON array of strings"))

	entries: list[str] = []
	for idx, entry in enumerate(payload, start=1):
		if not isinstance(entry, str):
			frappe.throw(_("Template body params row {0} must be a string").format(idx))
		entries.append(entry)

	return entries


def _render_jinja_template(template_text: str, doc: Any) -> str:
	context = {
		"doc": doc,
		"voucher_no": cstr(doc.name),
		"customer": cstr(doc.get("customer")),
		"company": cstr(doc.get("company")),
		"posting_date": formatdate(doc.get("posting_date")),
		"total_qty": flt(doc.get("total_qty")),
	}
	return cstr(frappe.render_template(template_text, context))


def _get_customer_mobile(customer: str) -> str:
	customer_doc = frappe.get_doc("Customer", customer)
	for fieldname in ("whatsapp_no", "mobile_no", "mobile_number", "phone"):
		value = cstr(customer_doc.get(fieldname)).strip()
		if value:
			return value

	rows = frappe.db.sql(
		"""
		select c.mobile_no, c.phone
		from `tabContact` c
		inner join `tabDynamic Link` dl
			on dl.parent = c.name
			and dl.parenttype = 'Contact'
		where dl.link_doctype = 'Customer'
			and dl.link_name = %(customer)s
		order by c.is_primary_contact desc, c.modified desc
		""",
		{"customer": customer},
		as_dict=True,
	)
	for row in rows:
		for fieldname in ("mobile_no", "phone"):
			value = cstr(row.get(fieldname)).strip()
			if value:
				return value

	return ""


def _normalize_phone_number(number: str, default_country_code: str = "") -> str:
	value = cstr(number).strip()
	if not value:
		return ""

	has_explicit_prefix = value.startswith("+") or value.startswith("00")
	digits = "".join(ch for ch in value if ch.isdigit())
	if value.startswith("00") and digits.startswith("00"):
		digits = digits[2:]

	if not digits:
		return ""

	normalized_country_code = "".join(ch for ch in cstr(default_country_code) if ch.isdigit())
	if (
		normalized_country_code
		and not has_explicit_prefix
		and (len(digits) <= 10 or digits.startswith("0"))
	):
		trimmed = digits.lstrip("0")
		digits = f"{normalized_country_code}{trimmed or digits}"

	return digits


def _send_text_message(*, settings: WhatsAppSettings, to_number: str, message: str) -> dict[str, Any]:
	payload = {
		"messaging_product": "whatsapp",
		"recipient_type": "individual",
		"to": to_number,
		"type": "text",
		"text": {"preview_url": False, "body": message},
	}
	return _send_meta_message(settings, payload)


def _send_template_message(
	*,
	settings: WhatsAppSettings,
	to_number: str,
	template_name: str,
	language_code: str,
	body_parameters: list[str] | None = None,
) -> dict[str, Any]:
	template_payload: dict[str, Any] = {
		"name": template_name,
		"language": {"code": cstr(language_code or "en").strip() or "en"},
	}
	if body_parameters:
		template_payload["components"] = [
			{
				"type": "body",
				"parameters": [{"type": "text", "text": cstr(value)} for value in body_parameters],
			}
		]

	payload = {
		"messaging_product": "whatsapp",
		"recipient_type": "individual",
		"to": to_number,
		"type": "template",
		"template": template_payload,
	}
	return _send_meta_message(settings, payload)


def _send_meta_message(settings: WhatsAppSettings, payload: dict[str, Any]) -> dict[str, Any]:
	api_version = cstr(settings["api_version"]).strip() or DEFAULT_API_VERSION
	phone_number_id = cstr(settings["phone_number_id"]).strip()
	access_token = cstr(settings["access_token"]).strip()

	url = f"{META_GRAPH_BASE_URL}/{api_version}/{phone_number_id}/messages"
	response = make_post_request(
		url=url,
		headers={
			"Authorization": f"Bearer {access_token}",
			"Content-Type": "application/json",
		},
		json=payload,
	)
	if isinstance(response, dict):
		return response
	return {}


def _extract_message_id(response: dict[str, Any]) -> str:
	messages = response.get("messages") if isinstance(response, dict) else None
	if not isinstance(messages, list) or not messages:
		return ""
	first_message = messages[0] if isinstance(messages[0], dict) else {}
	return cstr(first_message.get("id")).strip()
