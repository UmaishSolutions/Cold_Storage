// Copyright (c) 2026, Umaish Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cold Storage Outward", {
	setup(frm) {
		enforce_settings_company(frm);

	    frm.set_query("warehouse", "items", (doc, cdt, cdn) => {
	        const row = locals[cdt] && locals[cdt][cdn];
	        return {
	            query: "cold_storage.cold_storage.utils.search_warehouses_for_batch",
	            filters: {
	                company: doc.company || "",
	                customer: doc.customer || "",
	                batch_no: (row && row.batch_no) || "",
	                item: (row && row.item) || "",
	            },
	        };
	    });

	    frm.set_query("batch_no", "items", (doc, cdt, cdn) => {
	        const row = locals[cdt] && locals[cdt][cdn];
	        // If warehouse is selected, only show batches with positive balance there.
	        if (row && row.warehouse) {
	            return {
	                query: "cold_storage.cold_storage.utils.search_batches_for_customer_warehouse",
	                filters: {
	                    customer: doc.customer || "",
	                    warehouse: row.warehouse || "",
	                    item: row.item || "",
	                },
	            };
	        }

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

		frm.set_query("rack", "items", (doc, cdt, cdn) => {
			const row = locals[cdt] && locals[cdt][cdn];
			if (!row || !row.warehouse || !row.batch_no) {
				return {
					filters: {
						name: "__no_rack__",
					},
				};
			}
			return {
				query: "cold_storage.cold_storage.utils.search_racks_for_batch_warehouse_item",
				filters: {
					warehouse: row.warehouse,
					batch_no: row.batch_no,
					item: row.item || "",
				},
			};
		});
	},

	company(frm) {
		set_company_prefixed_series(frm);
	},

	customer(frm) {
		load_dispatch_charge_flags_from_customer(frm);
	},

	apply_dispatch_extra_charges(frm) {
		handle_dispatch_extra_charge_toggle(frm);
	},

	apply_dispatch_gst(frm) {
		recompute_dispatch_gst_total(frm);
	},

	select_dispatch_extra_charges(frm) {
		open_dispatch_extra_charge_selector(frm);
	},

	    onload(frm) {
		enforce_settings_company(frm);
		load_dispatch_charge_flags_from_customer(frm);
		load_dispatch_gst_settings(frm);

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

        // Draft outward docs should not carry linked accounting/stock refs.
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
		recompute_selected_extra_charges_total(frm);
		recompute_dispatch_gst_total(frm);
		ensure_outward_item_rates(frm);


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
		const series = `${abbr}-CS-OUT-.YYYY.-`;
		frm.set_df_property("naming_series", "options", series);
		if (frm.doc.naming_series !== series) {
			frm.set_value("naming_series", series);
		}
	});
}

async function load_dispatch_charge_flags_from_customer(frm) {
	if (!frm.doc.customer || frm.doc.docstatus !== 0) {
		return;
	}

	try {
		const response = await frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "Customer",
				name: frm.doc.customer,
			},
		});
		const message = (response && response.message) || {};
		await frm.set_value({
			apply_dispatch_gst: Number(message.custom_apply_dispatch_gst || 0) ? 1 : 0,
			apply_dispatch_extra_charges: Number(message.custom_apply_dispatch_extra_charges || 0) ? 1 : 0,
		});
		await handle_dispatch_extra_charge_toggle(frm);
		recompute_dispatch_totals(frm);
	} catch (error) {
		console.warn("Unable to load dispatch charge flags from customer", error);
	}
}

async function load_dispatch_gst_settings(frm) {
	try {
		const response = await frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "Cold Storage Settings",
				name: "Cold Storage Settings",
			},
		});
		const doc = (response && response.message) || {};
		frm._dispatch_gst_enabled = Number(doc.enable_dispatch_gst_on_handling || 0) === 1;
		frm._dispatch_gst_rate = flt(doc.dispatch_gst_rate || 0);
		recompute_dispatch_totals(frm);
	} catch (error) {
		console.warn("Unable to load dispatch GST settings", error);
		frm._dispatch_gst_enabled = false;
		frm._dispatch_gst_rate = 0;
		recompute_dispatch_totals(frm);
	}
}

async function handle_dispatch_extra_charge_toggle(frm) {
	if (frm.doc.docstatus !== 0) {
		return;
	}

	const enabled = Number(frm.doc.apply_dispatch_extra_charges || 0) === 1;
	if (!enabled) {
		await frm.set_value({
			dispatch_selected_extra_charges_json: "",
			selected_dispatch_extra_charges: "",
			total_selected_extra_charges: 0,
		});
		recompute_dispatch_totals(frm);
		return;
	}

	recompute_dispatch_totals(frm);
}

async function open_dispatch_extra_charge_selector(frm) {
	if (frm.doc.docstatus !== 0) {
		return;
	}
	if (Number(frm.doc.apply_dispatch_extra_charges || 0) !== 1) {
		frappe.msgprint(__("Enable Apply Dispatch Extra Charges first."));
		return;
	}

	try {
		const rows = await fetch_active_dispatch_extra_charges();
		if (!Array.isArray(rows) || !rows.length) {
			frappe.msgprint(__("No active dispatch extra charges found in Cold Storage Settings."));
			return;
		}

		const currentRows = get_selected_dispatch_extra_charge_rows(frm);
		const currentKeys = new Set(currentRows.map((row) => get_extra_charge_key(row)));
		const options = rows.map((row, index) => ({
			label: `${row.charge_name || row.charge_description} (Rate ${format_currency(row.charge_rate)})`,
			value: String(index),
			checked: currentKeys.has(get_extra_charge_key(row)),
		}));

		const dialog = new frappe.ui.Dialog({
			title: __("Select Dispatch Extra Charges"),
			fields: [
				{
					fieldname: "charges",
					fieldtype: "MultiCheck",
					label: __("Extra Charges"),
					options,
				},
			],
			primary_action_label: __("Apply"),
			primary_action: async (values) => {
				const selectedIndexes = values.charges || [];
				const selectedRows = selectedIndexes
					.map((value) => rows[Number(value)])
					.filter(Boolean)
					.map((row) => ({
						is_active: 1,
						charge_name: row.charge_name || row.charge_description || "",
						charge_description: row.charge_description || "",
						charge_rate: flt(row.charge_rate),
						credit_account: row.credit_account || "",
					}));

				await set_selected_dispatch_extra_charge_rows(frm, selectedRows);
				dialog.hide();
			},
		});
		dialog.show();
	} catch (error) {
		console.warn("Unable to fetch dispatch extra charges for selector", error);
	}
}

async function fetch_active_dispatch_extra_charges() {
	const response = await frappe.call({
		method: "frappe.client.get",
		args: {
			doctype: "Cold Storage Settings",
			name: "Cold Storage Settings",
		},
	});
	const doc = (response && response.message) || {};
	const rows = Array.isArray(doc.dispatch_extra_charges) ? doc.dispatch_extra_charges : [];
	return rows
		.filter((row) => Number(row.is_active || 0) === 1)
		.map((row) => ({
			is_active: 1,
			charge_name: row.charge_name || row.charge_description || "",
			charge_description: row.charge_description || "",
			charge_rate: flt(row.charge_rate),
			credit_account: row.credit_account || "",
		}));
}

function get_selected_dispatch_extra_charge_rows(frm) {
	const payload = (frm.doc.dispatch_selected_extra_charges_json || "").trim();
	if (!payload) {
		return [];
	}
	try {
		const rows = JSON.parse(payload);
		return Array.isArray(rows) ? rows : [];
	} catch (_error) {
		return [];
	}
}

async function set_selected_dispatch_extra_charge_rows(frm, rows) {
	const safeRows = Array.isArray(rows) ? rows : [];
	const summary = safeRows
		.map((row) => `${row.charge_name || row.charge_description} (${format_currency(row.charge_rate)})`)
		.filter(Boolean)
		.join("\n");
	await frm.set_value({
		dispatch_selected_extra_charges_json: JSON.stringify(safeRows),
		selected_dispatch_extra_charges: summary,
	});
	recompute_dispatch_totals(frm);
}

function recompute_selected_extra_charges_total(frm) {
	recompute_dispatch_totals(frm);
}

function recompute_dispatch_gst_total(frm) {
	recompute_dispatch_totals(frm);
}

function get_dispatch_total_components(frm) {
	const totalQty = (frm.doc.items || []).reduce((acc, row) => acc + flt(row.qty), 0);
	const baseCharges = (frm.doc.items || []).reduce((acc, row) => acc + flt(row.amount), 0);

	let totalExtraCharges = 0;
	if (Number(frm.doc.apply_dispatch_extra_charges || 0) === 1) {
		const selectedRows = get_selected_dispatch_extra_charge_rows(frm);
		totalExtraCharges = selectedRows.reduce(
			(acc, row) => acc + (flt(row.charge_rate) * totalQty),
			0
		);
	}

	const applyDispatchGst = Number(frm.doc.apply_dispatch_gst || 0) === 1;
	const gstEnabled = Boolean(frm._dispatch_gst_enabled);
	const gstRate = flt(frm._dispatch_gst_rate || 0);
	let totalGstCharges = 0;
	if (applyDispatchGst && gstEnabled && gstRate > 0) {
		const handlingCharges = (frm.doc.items || []).reduce(
			(acc, row) => acc + (flt(row.qty) * flt(row.handling_rate)),
			0
		);
		totalGstCharges = flt((handlingCharges * gstRate) / 100.0);
	}

	return {
		totalQty,
		totalExtraCharges: flt(totalExtraCharges),
		totalGstCharges: flt(totalGstCharges),
		totalCharges: flt(baseCharges + totalExtraCharges + totalGstCharges),
	};
}

function recompute_dispatch_totals(frm) {
	const totals = get_dispatch_total_components(frm);
	frm.set_value({
		total_qty: totals.totalQty,
		total_selected_extra_charges: totals.totalExtraCharges,
		total_gst_charges: totals.totalGstCharges,
		total_charges: totals.totalCharges,
	});
}

function recompute_dispatch_grand_total(frm) {
	recompute_dispatch_totals(frm);
}

function get_extra_charge_key(row) {
	return `${row.charge_name || ""}::${row.charge_description || ""}::${flt(row.charge_rate)}::${row.credit_account || ""}`;
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

	const sidebarMetaDetails = sidebar.find(".sidebar-meta-details");
	if (sidebarMetaDetails.length) {
		sidebarMetaDetails.after(section);
	} else {
		sidebar.prepend(section);
	}
	const content = section.find(".cs-doc-qr-content");
	const cachedQrDataUri = frm.doc.submitted_qr_code_data_uri;

	if (cachedQrDataUri) {
		content.html(
			`<div class="text-center">
				<img src="${cachedQrDataUri}" alt="Document QR" style="width: 100%; max-width: 170px; border: 1px solid var(--border-color); border-radius: 8px; padding: 6px; background: #fff;" />
			</div>`
		);
		return;
	}

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

frappe.ui.form.on("Cold Storage Outward Item", {
    item(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "rack", "");
        if (row.item) {
            frappe.db.get_value("Item", row.item, ["item_name", "item_group", "stock_uom"], (r) => {
                if (r) {
                    frappe.model.set_value(cdt, cdn, "item_name", r.item_name);
                    frappe.model.set_value(cdt, cdn, "item_group", r.item_group);
                    frappe.model.set_value(cdt, cdn, "uom", r.stock_uom);
                    populate_outward_rates(cdt, cdn, r.item_group);
                }
            });
        }
		fetch_outward_available_qty(cdt, cdn);
    },

	batch_no(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "rack", "");
		if (!row.batch_no) {
			frappe.model.set_value(cdt, cdn, "available_qty", 0);
			return;
		}
		frappe.db.get_value("Batch", row.batch_no, ["item", "custom_customer"], (r) => {
			if (r && r.item) {
				frappe.model.set_value(cdt, cdn, "item", r.item);
				// Ensure rates are refreshed when item is derived from batch selection.
				frappe.model.trigger("item", cdt, cdn);
			}
			fetch_outward_available_qty(cdt, cdn);
		});
	},

	warehouse(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "rack", "");
		fetch_outward_available_qty(cdt, cdn);
	},

    qty(frm, cdt, cdn) {
        compute_outward_row(frm, cdt, cdn);
    },

    handling_rate(frm, cdt, cdn) {
        compute_outward_row(frm, cdt, cdn);
    },

    loading_rate(frm, cdt, cdn) {
        compute_outward_row(frm, cdt, cdn);
    },

    items_remove(frm) {
        compute_outward_totals(frm);
    },
});



function compute_outward_row(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const amount = flt(row.qty) * (flt(row.handling_rate) + flt(row.loading_rate));
    frappe.model.set_value(cdt, cdn, "amount", amount);
    compute_outward_totals(frm);
}

function compute_outward_totals(frm) {
	recompute_dispatch_totals(frm);
}

function populate_outward_rates(cdt, cdn, item_group) {
	if (!item_group) {
		return;
	}
	frappe.call({
		method: "cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.get_item_group_rates",
		args: {
			item_group,
		},
		callback(resp) {
			if (resp.message) {
				frappe.model.set_value(cdt, cdn, "handling_rate", flt(resp.message.handling_rate));
				frappe.model.set_value(cdt, cdn, "loading_rate", flt(resp.message.loading_rate));
			}
		},
	});
}

function ensure_outward_item_rates(frm) {
	(frm.doc.items || []).forEach((row) => {
		if (!row.item_group) {
			return;
		}
		if (flt(row.handling_rate) || flt(row.loading_rate)) {
			return;
		}
		populate_outward_rates(row.doctype, row.name, row.item_group);
	});
}

function fetch_outward_available_qty(cdt, cdn) {
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
