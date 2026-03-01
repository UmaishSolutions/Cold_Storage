# Copyright (c) 2026, Umaish Solutions and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt


@frappe.whitelist()
def get_or_create_payment_link(sales_invoice: str) -> dict[str, str]:
	"""Return ERPNext built-in payment link for Sales Invoice, creating Payment Request when needed."""
	sales_invoice = cstr(sales_invoice).strip()
	if not sales_invoice:
		frappe.throw(_("Sales Invoice is required"), frappe.ValidationError)
	if not frappe.db.exists("Sales Invoice", sales_invoice):
		frappe.throw(_("Sales Invoice not found"), frappe.DoesNotExistError)

	if not frappe.has_permission("Sales Invoice", "read", sales_invoice):
		frappe.throw(_("You are not allowed to access this Sales Invoice"), frappe.PermissionError)

	invoice = frappe.db.get_value(
		"Sales Invoice",
		sales_invoice,
		["name", "customer", "docstatus", "outstanding_amount"],
		as_dict=True,
	)
	if not invoice or cint(invoice.get("docstatus")) != 1:
		frappe.throw(_("Only submitted Sales Invoices are eligible for payment links"), frappe.ValidationError)

	if flt(invoice.get("outstanding_amount")) <= 0:
		return {
			"payment_url": _to_sales_invoice_route(sales_invoice),
			"source": "sales_invoice",
			"status": "paid",
		}

	existing = _get_existing_payment_request(sales_invoice)
	if existing:
		return {
			"payment_url": cstr(existing.get("payment_url")).strip()
			or _to_payment_request_route(existing.get("name")),
			"source": "payment_request",
			"status": "existing",
		}

	created = _create_payment_request(sales_invoice, cstr(invoice.get("customer")))
	if created.get("payment_url") or created.get("name"):
		return {
			"payment_url": cstr(created.get("payment_url")).strip()
			or _to_payment_request_route(created.get("name")),
			"source": "payment_request",
			"status": "created",
		}

	return {
		"payment_url": _to_sales_invoice_route(sales_invoice),
		"source": "sales_invoice",
		"status": "fallback",
	}


def _get_existing_payment_request(sales_invoice: str) -> frappe._dict | None:
	return frappe.db.get_value(
		"Payment Request",
		{
			"reference_doctype": "Sales Invoice",
			"reference_name": sales_invoice,
			"docstatus": 1,
		},
		["name", "payment_url", "status"],
		as_dict=True,
		order_by="modified desc",
	)


def _create_payment_request(sales_invoice: str, customer: str) -> frappe._dict:
	from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request

	original_user = frappe.session.user
	try:
		if not frappe.has_permission("Payment Request", "create", user=original_user):
			frappe.set_user("Administrator")

		payment_request = make_payment_request(
			dt="Sales Invoice",
			dn=sales_invoice,
			party_type="Customer",
			party=customer,
			submit_doc=1,
			return_doc=1,
			mute_email=1,
		)
		return frappe._dict(
			{
				"name": payment_request.name,
				"payment_url": cstr(payment_request.get("payment_url")).strip(),
			}
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Cold Storage ERPNext Payment Link")
		return frappe._dict({})
	finally:
		if frappe.session.user != original_user:
			frappe.set_user(original_user)


def _to_sales_invoice_route(docname: str | None) -> str:
	if not docname:
		return ""
	return f"/app/sales-invoice/{docname}"


def _to_payment_request_route(docname: str | None) -> str:
	if not docname:
		return ""
	return f"/app/payment-request/{docname}"
