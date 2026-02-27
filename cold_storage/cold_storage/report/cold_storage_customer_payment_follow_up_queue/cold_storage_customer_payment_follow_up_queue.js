frappe.query_reports["Cold Storage Customer Payment Follow-up Queue"] = {
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
			fieldname: "as_on_date",
			label: __("As On Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			description: __("Evaluate queue as of this date."),
		},
		{
			fieldname: "min_overdue_days",
			label: __("Minimum Overdue Days"),
			fieldtype: "Int",
			default: 0,
			description: __("Only show invoices overdue by at least this many days."),
		},
		{
			fieldname: "limit_rows",
			label: __("Top Queue Size"),
			fieldtype: "Int",
			default: 500,
			description: __("Limit report to top N follow-up entries by queue score."),
		},
	],
};
