// Copyright (c) 2026, Umaish Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cold Storage Inward", {
	setup(frm) {
		enforce_settings_company(frm);

	    frm.set_query("warehouse", "items", () => {
	        const filters = {};
	        if (frm.doc.company) {
	            filters.company = frm.doc.company;
	        }
	        return { filters };
	    });

		frm.set_query("rack", "items", (doc, cdt, cdn) => {
			const row = locals[cdt] && locals[cdt][cdn];
			if (!row || !row.warehouse) {
				return {
					filters: {
						name: "__no_rack__",
					},
				};
			}
			return {
				filters: {
					warehouse: row.warehouse,
					is_active: 1,
				},
			};
		});

	    frm.set_query("batch_no", "items", (doc, cdt, cdn) => {
	        const row = locals[cdt] && locals[cdt][cdn];
	        const filters = {};

	        if (doc.customer) {
	            filters.custom_customer = doc.customer;
	        } else {
	            // Force selecting customer first before choosing a batch.
	            filters.name = "__no_batch__";
	        }

	        if (row && row.item) {
	            filters.item = row.item;
	        }

	        return { filters };
	    });
	},

	company(frm) {
		set_company_prefixed_series(frm);
	},

    onload(frm) {
		enforce_settings_company(frm);

        if (frm.fields_dict.items && frm.fields_dict.items.grid) {
            frm.fields_dict.items.grid.meta.editable_grid = true;
            frm.fields_dict.items.grid.edit_row = function () { };
        }
    },

    refresh(frm) {
        // Disable child table popup (Force inline edit)
        if (frm.fields_dict.items && frm.fields_dict.items.grid) {
            frm.fields_dict.items.grid.meta.editable_grid = true;
            frm.fields_dict.items.grid.edit_row = function () { };
        }

        // Draft inward docs should not carry linked accounting/stock refs.
        if (frm.doc.docstatus === 0) {
            const updates = {};
            if (frm.doc.sales_invoice) {
                updates.sales_invoice = "";
            }
            if (frm.doc.stock_entry) {
                updates.stock_entry = "";
            }
            if (frm.doc.journal_entry) {
                updates.journal_entry = "";
            }
            if (Object.keys(updates).length) {
                frm.set_value(updates);
            }
        }

		enforce_settings_company(frm);
		set_company_prefixed_series(frm);


        if (frm.doc.sales_invoice) {
            frm.add_custom_button(
                __("Sales Invoice"),
                () => frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice),
                __("View")
            );
			add_erpnext_payment_link_button(frm);
        }
        if (frm.doc.stock_entry) {
            frm.add_custom_button(
                __("Stock Entry"),
                () => frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry),
                __("View")
            );
        }
        if (frm.doc.journal_entry) {
            frm.add_custom_button(
                __("Journal Entry"),
                () => frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry),
                __("View")
            );
        }

		add_whatsapp_notification_button(frm);
		render_sidebar_qr_code(frm);
    },
});

async function enforce_settings_company(frm) {
	frm.set_df_property("company", "read_only", 1);

	try {
		const configured_company = await frappe.db.get_single_value(
			"Cold Storage Settings",
			"company"
		);
		if (!configured_company) {
			return;
		}

		const can_set_company = frm.is_new() || frm.doc.docstatus === 0 || !frm.doc.company;
		if (can_set_company && frm.doc.company !== configured_company) {
			await frm.set_value("company", configured_company);
		}
	} catch (error) {
		console.warn("Unable to load Cold Storage Settings company", error);
	}
}

function add_whatsapp_notification_button(frm) {
	if (frm.is_new() || frm.doc.docstatus !== 1) {
		return;
	}

	frm.add_custom_button(__("Send Notification"), () => {
		frappe.call({
			method: "cold_storage.cold_storage.integrations.whatsapp.send_whatsapp_for_document",
			args: {
				doctype: frm.doctype,
				docname: frm.doc.name,
			},
			freeze: true,
			freeze_message: __("Sending WhatsApp notification..."),
			callback: (r) => {
				const response = r.message || {};
				const toNumber = frappe.utils.escape_html(response.to_number || "");
				const messageId = frappe.utils.escape_html(response.message_id || __("N/A"));
				frappe.msgprint({
					title: __("WhatsApp Notification Sent"),
					indicator: "green",
					message: __(
						"Delivered to <b>{0}</b><br>Message ID: <code>{1}</code>",
						[toNumber, messageId]
					),
				});
			},
		});
	}, __("WhatsApp"));
}

function add_erpnext_payment_link_button(frm) {
	if (!frm.doc.sales_invoice) {
		return;
	}

	frm.add_custom_button(
		__("Payment Link"),
		() => {
			frappe.call({
				method: "cold_storage.cold_storage.payment_link.get_or_create_payment_link",
				args: {
					sales_invoice: frm.doc.sales_invoice,
				},
				freeze: true,
				freeze_message: __("Generating ERPNext payment link..."),
				callback: (r) => {
					const data = r.message || {};
					const paymentUrl = String(data.payment_url || "").trim();
					if (!paymentUrl) {
						frappe.msgprint(__("Unable to generate payment link."));
						return;
					}
					window.open(paymentUrl, "_blank", "noopener");
				},
			});
		},
		__("View")
	);
}

function set_company_prefixed_series(frm) {
	if (!frm.is_new() || !frm.doc.company) {
		return;
	}

	frappe.db.get_value("Company", frm.doc.company, "abbr").then((r) => {
		const abbr = ((r && r.message && r.message.abbr) || frm.doc.company || "CO")
			.toString()
			.replace(/[^A-Za-z0-9]/g, "")
			.toUpperCase() || "CO";
		const series = `${abbr}-CS-IN-.YYYY.-`;
		frm.set_df_property("naming_series", "options", series);
		if (frm.doc.naming_series !== series) {
			frm.set_value("naming_series", series);
		}
	});
}

function render_sidebar_qr_code(frm) {
	if (!frm.sidebar || !frm.sidebar.sidebar) {
		return;
	}

	const sidebar = frm.sidebar.sidebar;
	sidebar.find(".cs-doc-qr-section").remove();

	if (frm.is_new()) {
		return;
	}

	const section = $(
		`<div class="sidebar-section cs-doc-qr-section border-bottom">
			<div class="cs-doc-qr-content text-center"></div>
		</div>`
	);

	sidebar.find(".sidebar-meta-details").after(section);
	const content = section.find(".cs-doc-qr-content");

	const docname = frm.doc.name;
	frappe.call({
		method: "cold_storage.cold_storage.utils.get_document_sidebar_qr_code_data_uri",
		args: {
			doctype: frm.doctype,
			docname,
			scale: 3,
		},
		callback(r) {
			if (frm.doc.name !== docname) {
				return;
			}

			const dataUri = r && r.message;
			if (!dataUri) {
				section.remove();
				return;
			}

			content.html(
				`<div class="text-center">
					<img src="${dataUri}" alt="Document QR" style="width: 100%; max-width: 170px; border: 1px solid var(--border-color); border-radius: 8px; padding: 6px; background: #fff;" />
				</div>`
			);
		},
	});
}

frappe.ui.form.on("Cold Storage Inward Item", {
    item(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.item) {
            frappe.db.get_value("Item", row.item, ["item_name", "item_group", "stock_uom"], (r) => {
                if (r) {
                    frappe.model.set_value(cdt, cdn, "item_name", r.item_name);
                    frappe.model.set_value(cdt, cdn, "item_group", r.item_group);
                    frappe.model.set_value(cdt, cdn, "uom", r.stock_uom);
                    // Fetch rate
                    if (r.item_group) {
                        frappe.call({
                            method: "cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.get_item_group_rates",
                            args: {
                                item_group: r.item_group,
                            },
                            callback(resp) {
                                if (resp.message) {
                                    frappe.model.set_value(cdt, cdn, "unloading_rate", flt(resp.message.unloading_rate));
                                }
                            },
                        });
                    }
                }
            });
        }
		fetch_inward_available_qty(cdt, cdn);
    },

	batch_no(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.batch_no) {
			frappe.model.set_value(cdt, cdn, "available_qty", 0);
			return;
		}
		frappe.db.get_value("Batch", row.batch_no, ["item", "custom_customer"], (r) => {
			if (r && r.item) {
				frappe.model.set_value(cdt, cdn, "item", r.item);
			}
			fetch_inward_available_qty(cdt, cdn);
		});
	},

	warehouse(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "rack", "");
		fetch_inward_available_qty(cdt, cdn);
	},

    qty(frm, cdt, cdn) {
        compute_row_amount(frm, cdt, cdn);
    },

    unloading_rate(frm, cdt, cdn) {
        compute_row_amount(frm, cdt, cdn);
    },

    items_remove(frm) {
        compute_inward_totals(frm);
    },
});

function compute_row_amount(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.unloading_rate));
    compute_inward_totals(frm);
}

function compute_inward_totals(frm) {
    let total_qty = 0;
    let total_charges = 0;
    (frm.doc.items || []).forEach((row) => {
        total_qty += flt(row.qty);
        total_charges += flt(row.amount);
    });
    frm.set_value("total_qty", total_qty);
	frm.set_value("total_unloading_charges", total_charges);
}

function fetch_inward_available_qty(cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.batch_no || !row.warehouse) {
		frappe.model.set_value(cdt, cdn, "available_qty", 0);
		return;
	}

	frappe.call({
		method: "cold_storage.cold_storage.utils.get_batch_balance",
		args: {
			batch_no: row.batch_no,
			warehouse: row.warehouse,
		},
		callback(r) {
			frappe.model.set_value(cdt, cdn, "available_qty", flt(r.message));
		},
	});
}
