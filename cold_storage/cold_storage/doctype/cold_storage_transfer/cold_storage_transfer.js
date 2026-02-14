// Copyright (c) 2026, Umaish Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cold Storage Transfer", {
	setup(frm) {
	    frm.set_query("source_warehouse", "items", (doc, cdt, cdn) => {
	        const row = locals[cdt] && locals[cdt][cdn];
	        const customer =
	            doc.transfer_type === "Ownership Transfer" ? doc.from_customer : doc.customer;
	        if (
	            (
	                doc.transfer_type === "Ownership Transfer" ||
	                doc.transfer_type === "Inter-Warehouse Transfer" ||
	                doc.transfer_type === "Intra-Warehouse Transfer"
	            ) &&
	            row &&
	            row.batch_no
	        ) {
	            return {
	                query: "cold_storage.cold_storage.utils.search_warehouses_for_batch",
	                filters: {
	                    company: doc.company || "",
	                    customer: customer || "",
	                    batch_no: row.batch_no,
	                },
	            };
	        }

	        const filters = {};
	        if (doc.company) {
	            filters.company = doc.company;
            }
            return { filters };
        });
        frm.set_query("target_warehouse", "items", () => {
            const filters = {};
	        if (frm.doc.company) {
	            filters.company = frm.doc.company;
	        }
	        return { filters };
	    });

	    frm.set_query("batch_no", "items", (doc, cdt, cdn) => {
	        const row = locals[cdt] && locals[cdt][cdn];
	        const customer =
	            doc.transfer_type === "Ownership Transfer" ? doc.from_customer : doc.customer;

	        if (doc.transfer_type === "Ownership Transfer") {
	            const filters = {};

	            if (customer) {
	                filters.custom_customer = customer;
	            } else {
	                // Force selecting customer first before choosing a batch.
	                filters.name = "__no_batch__";
	            }

	            if (row && row.item) {
	                filters.item = row.item;
	            }

	            return { filters };
	        }

	        // For location transfers, allow batch selection before source warehouse is chosen.
	        if (!(row && row.source_warehouse)) {
	            const filters = {};
	            if (customer) {
	                filters.custom_customer = customer;
	            } else {
	                filters.name = "__no_batch__";
	            }
	            if (row && row.item) {
	                filters.item = row.item;
	            }
	            return { filters };
	        }

	        return {
	            query: "cold_storage.cold_storage.utils.search_batches_for_customer_warehouse",
	            filters: {
	                customer: customer || "",
	                warehouse: (row && row.source_warehouse) || "",
	                item: (row && row.item) || "",
	            },
	        };
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

        // Draft transfer docs should not carry linked accounting/stock refs.
        if (frm.doc.docstatus === 0) {
            const updates = {};
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

        if (frm.doc.journal_entry) {
            frm.add_custom_button(
                __("Journal Entry"),
                () => frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry),
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
        apply_transfer_type_ui(frm);
    },

    transfer_type(frm) {
        const is_ownership = frm.doc.transfer_type === "Ownership Transfer";
        const is_intra = frm.doc.transfer_type === "Intra-Warehouse Transfer";

        if (is_ownership) {
            if (frm.doc.customer) {
                frm.set_value("customer", "");
            }
        } else {
            if (frm.doc.from_customer) {
                frm.set_value("from_customer", "");
            }
            if (frm.doc.to_customer) {
                frm.set_value("to_customer", "");
            }
        }

        apply_transfer_type_ui(frm);

        if (is_intra) {
            (frm.doc.items || []).forEach((row) => {
                const next_target = row.source_warehouse || "";
                if ((row.target_warehouse || "") !== next_target) {
                    frappe.model.set_value(row.doctype, row.name, "target_warehouse", next_target);
                }
            });
        }

        frm.trigger("fetch_all_rates");
        frm.refresh_fields("items");
        frm.fields_dict.items.grid.refresh();
    },

    fetch_all_rates(frm) {
        if (frm.doc.transfer_type === "Ownership Transfer") return;

        (frm.doc.items || []).forEach((row) => {
            fetch_transfer_rate(frm, row.doctype, row.name, row.item_group);
        });
    },
});

frappe.ui.form.on("Cold Storage Transfer Item", {
    item(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.item) {
            frappe.db.get_value("Item", row.item, ["item_name", "item_group", "stock_uom"], (r) => {
                if (r) {
                    frappe.model.set_value(cdt, cdn, "item_name", r.item_name);
                    frappe.model.set_value(cdt, cdn, "item_group", r.item_group);
                    frappe.model.set_value(cdt, cdn, "uom", r.stock_uom);

                    // Fetch transfer rate
                    fetch_transfer_rate(frm, cdt, cdn, r.item_group);
                }
            });
        }
		fetch_transfer_available_qty(cdt, cdn);
    },

	batch_no(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.batch_no) {
			frappe.model.set_value(cdt, cdn, "available_qty", 0);
			return;
		}
		frappe.db.get_value("Batch", row.batch_no, ["item"], (r) => {
			if (r && r.item) {
				frappe.model.set_value(cdt, cdn, "item", r.item);
			}
			fetch_transfer_available_qty(cdt, cdn);
		});
	},

	source_warehouse(frm, cdt, cdn) {
		if (frm.doc.transfer_type === "Intra-Warehouse Transfer") {
			const row = locals[cdt][cdn];
			const next_target = row.source_warehouse || "";
			if ((row.target_warehouse || "") !== next_target) {
				frappe.model.set_value(cdt, cdn, "target_warehouse", next_target);
			}
		}
		fetch_transfer_available_qty(cdt, cdn);
	},

    qty(frm, cdt, cdn) {
        compute_transfer_row(frm, cdt, cdn);
    },

    transfer_rate(frm, cdt, cdn) {
        compute_transfer_row(frm, cdt, cdn);
    },

    items_remove(frm) {
        compute_transfer_totals(frm);
    },
});



function compute_transfer_row(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.transfer_rate));
    compute_transfer_totals(frm);
}

function compute_transfer_totals(frm) {
    let total_qty = 0;
    let total_charges = 0;
    (frm.doc.items || []).forEach((row) => {
        total_qty += flt(row.qty);
        total_charges += flt(row.amount);
    });
    frm.set_value("total_qty", total_qty);
	frm.set_value("total_transfer_charges", total_charges);
}

function fetch_transfer_available_qty(cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.batch_no || !row.source_warehouse) {
		frappe.model.set_value(cdt, cdn, "available_qty", 0);
		return;
	}

	frappe.call({
		method: "cold_storage.cold_storage.utils.get_batch_balance",
		args: {
			batch_no: row.batch_no,
			warehouse: row.source_warehouse,
		},
		callback(r) {
			frappe.model.set_value(cdt, cdn, "available_qty", flt(r.message));
		},
	});
}

function fetch_transfer_rate(frm, cdt, cdn, item_group) {
	if (!item_group || frm.doc.transfer_type === "Ownership Transfer") {
		const row = locals[cdt] && locals[cdt][cdn];
		if (row && flt(row.transfer_rate) !== 0) {
			frappe.model.set_value(cdt, cdn, "transfer_rate", 0);
		}
		return;
	}

	frappe.call({
		method: "cold_storage.cold_storage.doctype.cold_storage_settings.cold_storage_settings.get_transfer_rate",
		args: {
			item_group,
			transfer_type: frm.doc.transfer_type,
		},
		callback(r) {
			const row = locals[cdt] && locals[cdt][cdn];
			const next_rate = flt(r.message);
			if (row && flt(row.transfer_rate) !== next_rate) {
				frappe.model.set_value(cdt, cdn, "transfer_rate", next_rate);
			}
		},
	});
}

function apply_transfer_type_ui(frm) {
	const is_ownership = frm.doc.transfer_type === "Ownership Transfer";
	const is_intra = frm.doc.transfer_type === "Intra-Warehouse Transfer";
	const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
	if (!grid) return;

	if (is_ownership) {
		grid.update_docfield_property("transfer_rate", "hidden", 1);
		grid.update_docfield_property("amount", "hidden", 1);
		grid.update_docfield_property("source_warehouse", "hidden", 0);
		grid.update_docfield_property("source_warehouse", "reqd", 1);
		grid.update_docfield_property("target_warehouse", "hidden", 1);
		grid.update_docfield_property("target_warehouse", "reqd", 0);
		grid.update_docfield_property("target_warehouse", "read_only", 0);
		frm.set_df_property("total_transfer_charges", "hidden", 1);
		return;
	}

	grid.update_docfield_property("transfer_rate", "hidden", 0);
	grid.update_docfield_property("amount", "hidden", 0);
	grid.update_docfield_property("source_warehouse", "hidden", 0);
	grid.update_docfield_property("target_warehouse", "hidden", 0);
	grid.update_docfield_property("source_warehouse", "reqd", 1);
	grid.update_docfield_property("target_warehouse", "reqd", is_intra ? 0 : 1);
	grid.update_docfield_property("target_warehouse", "read_only", is_intra ? 1 : 0);
	frm.set_df_property("total_transfer_charges", "hidden", 0);
}
