frappe.query_reports["Cold Storage Client Portal Access Log"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
		description: __("Filter by from date."),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		description: __("Filter by to date."),
		},
		{
			fieldname: "user",
			label: __("User"),
			fieldtype: "Link",
			options: "User",
		description: __("Filter by user."),
		},
		{
			fieldname: "source",
			label: __("Source"),
			fieldtype: "Select",
			options: "\ncs-portal-api\ncs-portal-server",
		description: __("Filter by source."),
		},
	],
};
