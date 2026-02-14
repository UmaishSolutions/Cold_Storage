frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Yearly Inward Outward Trend"] = {
	method: "cold_storage.cold_storage.dashboard_chart_source.yearly_inward_outward_trend.yearly_inward_outward_trend.get",
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_year",
			label: __("From Year"),
			fieldtype: "Int",
			default: new Date().getFullYear(),
		},
		{
			fieldname: "to_year",
			label: __("To Year"),
			fieldtype: "Int",
			default: new Date().getFullYear(),
		},
	],
};
