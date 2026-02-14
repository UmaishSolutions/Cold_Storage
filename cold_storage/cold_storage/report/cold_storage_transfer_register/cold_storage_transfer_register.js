frappe.query_reports["Cold Storage Transfer Register"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "transfer_type",
			label: __("Transfer Type"),
			fieldtype: "Select",
			options: "\nOwnership Transfer\nInter-Warehouse Transfer\nIntra-Warehouse Transfer",
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "from_customer",
			label: __("From Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "to_customer",
			label: __("To Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nSubmitted\nCancelled",
		},
	],
};
