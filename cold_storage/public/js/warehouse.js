frappe.ui.form.on("Warehouse", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.is_group) {
			return;
		}

		frm.add_custom_button(__("Create Cold Storage Racks"), () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Create Racks for {0}", [frm.doc.name]),
				fields: [
					{
						fieldname: "prefix",
						fieldtype: "Data",
						label: __("Rack Prefix"),
						default: "R-",
						reqd: 1,
					},
					{
						fieldname: "count",
						fieldtype: "Int",
						label: __("How Many Racks"),
						default: 10,
						reqd: 1,
					},
					{
						fieldname: "start_from",
						fieldtype: "Int",
						label: __("Start Number"),
						default: 1,
						reqd: 1,
					},
					{
						fieldname: "digits",
						fieldtype: "Int",
						label: __("Number Padding"),
						default: 3,
						reqd: 1,
					},
				],
				primary_action_label: __("Create"),
				primary_action(values) {
					frappe.call({
						method: "cold_storage.cold_storage.doctype.cold_storage_rack.cold_storage_rack.create_racks_for_warehouse",
						args: {
							warehouse: frm.doc.name,
							count: values.count,
							prefix: values.prefix,
							start_from: values.start_from,
							digits: values.digits,
						},
						freeze: true,
						freeze_message: __("Creating rack masters..."),
						callback: (r) => {
							const result = r.message || {};
							frappe.show_alert(
								{
									message: __(
										"Created: {0}, Skipped Existing: {1}",
										[result.created_count || 0, result.skipped_existing_count || 0]
									),
									indicator: "green",
								},
								7
							);
							dialog.hide();
						},
					});
				},
			});

			dialog.show();
		});

		frm.add_custom_button(__("Create Cold Storage Rack"), () => {
			frappe.new_doc("Cold Storage Rack", {
				warehouse: frm.doc.name,
				is_active: 1,
			});
		});
	},
});
