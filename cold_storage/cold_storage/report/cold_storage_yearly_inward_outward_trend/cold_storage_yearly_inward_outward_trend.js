frappe.query_reports["Cold Storage Yearly Inward Outward Trend"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "from_year",
			label: __("From Year"),
			fieldtype: "Int",
			default: new Date().getFullYear() - 5,
		},
		{
			fieldname: "to_year",
			label: __("To Year"),
			fieldtype: "Int",
			default: new Date().getFullYear(),
		},
	],
};
