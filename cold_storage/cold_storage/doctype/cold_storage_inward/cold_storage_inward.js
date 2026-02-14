// Copyright (c) 2026, Umaish Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cold Storage Inward", {
	setup(frm) {
	    frm.set_query("warehouse", "items", () => {
	        const filters = {};
	        if (frm.doc.company) {
	            filters.company = frm.doc.company;
	        }
	        return { filters };
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

    onload(frm) {
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

        // Fetch default Company from Cold Storage Settings if not set
        if (frm.is_new() && !frm.doc.company) {
            frappe.db.get_single_value("Cold Storage Settings", "company").then((company) => {
                if (company) {
                    frm.set_value("company", company);
                }
            });
        }


        if (frm.doc.sales_invoice) {
            frm.add_custom_button(
                __("Sales Invoice"),
                () => frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice),
                __("View")
            );
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
    },
});

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
                            method: "frappe.client.get_list",
                            args: {
                                doctype: "Charge Configuration",
                                filters: { parent: "Cold Storage Settings", item_group: r.item_group },
                                fields: ["unloading_rate"],
                                limit_page_length: 1,
                            },
                            callback(resp) {
                                if (resp.message && resp.message.length) {
                                    frappe.model.set_value(cdt, cdn, "unloading_rate", resp.message[0].unloading_rate);
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
