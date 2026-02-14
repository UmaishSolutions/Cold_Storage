// Copyright (c) 2026, Umaish Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cold Storage Outward", {
	setup(frm) {
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
	},

	company(frm) {
		set_company_prefixed_series(frm);
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

        // Draft outward docs should not carry linked accounting/stock refs.
        if (frm.doc.docstatus === 0) {
            const updates = {};
            if (frm.doc.sales_invoice) {
                updates.sales_invoice = "";
            }
            if (frm.doc.stock_entry) {
                updates.stock_entry = "";
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
		set_company_prefixed_series(frm);


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

    },
});

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

frappe.ui.form.on("Cold Storage Outward Item", {
    item(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.item) {
            frappe.db.get_value("Item", row.item, ["item_name", "item_group", "stock_uom"], (r) => {
                if (r) {
                    frappe.model.set_value(cdt, cdn, "item_name", r.item_name);
                    frappe.model.set_value(cdt, cdn, "item_group", r.item_group);
                    frappe.model.set_value(cdt, cdn, "uom", r.stock_uom);
                    if (r.item_group) {
                        frappe.call({
                            method: "frappe.client.get_list",
                            args: {
                                doctype: "Charge Configuration",
                                filters: { parent: "Cold Storage Settings", item_group: r.item_group },
                                fields: ["handling_rate", "loading_rate"],
                                limit_page_length: 1,
                            },
                            callback(resp) {
                                if (resp.message && resp.message.length) {
                                    frappe.model.set_value(cdt, cdn, "handling_rate", resp.message[0].handling_rate);
                                    frappe.model.set_value(cdt, cdn, "loading_rate", resp.message[0].loading_rate);
                                }
                            },
                        });
                    }
                }
            });
        }
		fetch_outward_available_qty(cdt, cdn);
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
			fetch_outward_available_qty(cdt, cdn);
		});
	},

	warehouse(frm, cdt, cdn) {
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
    let total_qty = 0;
    let total_charges = 0;
    (frm.doc.items || []).forEach((row) => {
        total_qty += flt(row.qty);
        total_charges += flt(row.amount);
    });
    frm.set_value("total_qty", total_qty);
	frm.set_value("total_charges", total_charges);
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
