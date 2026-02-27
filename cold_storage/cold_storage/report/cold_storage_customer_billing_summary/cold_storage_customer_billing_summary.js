frappe.query_reports["Cold Storage Customer Billing Summary"] = {
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
		} catch (error) {
			console.warn("Unable to load Cold Storage Settings company for report filter", error);
			company_filter.df.read_only = 0;
		}

		company_filter.refresh();
	},
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			description: __("Filter by company."),
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			description: __("Filter by customer."),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			description: __("Filter by from date."),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			description: __("Filter by to date."),
		},
	],
};
