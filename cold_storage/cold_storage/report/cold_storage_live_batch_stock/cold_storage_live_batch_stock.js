frappe.query_reports["Cold Storage Live Batch Stock"] = {
	onload: async (query_report) => {
		const company_filter = query_report.get_filter("company", false);
		if (!company_filter) return;

		try {
			const configured_company = await frappe.db.get_single_value("Cold Storage Settings", "company");
			if (configured_company) {
				company_filter.df.default = configured_company;
				company_filter.df.read_only = 1;
				await company_filter.set_value(configured_company);
			} else {
				company_filter.df.read_only = 0;
			}
			company_filter.refresh();
		} catch (error) {
			console.warn("Unable to load Cold Storage Settings company for live batch stock filter", error);
			company_filter.df.read_only = 0;
			company_filter.refresh();
		}
	},
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "as_on_date",
			label: __("As On Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "item",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "batch_no",
			label: __("Batch"),
			fieldtype: "Link",
			options: "Batch",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
		{
			fieldname: "include_zero_balance",
			label: __("Include Zero/Negative Balance"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
