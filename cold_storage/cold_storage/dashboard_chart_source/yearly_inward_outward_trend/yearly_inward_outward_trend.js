frappe.provide("frappe.dashboards.chart_sources");

const yearly_inward_outward_chart_source_name = "Yearly Inward Outward Trend";

frappe.dashboards.chart_sources[yearly_inward_outward_chart_source_name] = {
	method: "cold_storage.cold_storage.dashboard_chart_source.yearly_inward_outward_trend.yearly_inward_outward_trend.get",
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
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

frappe.after_ajax(async () => {
	const chart_source = frappe.dashboards.chart_sources[yearly_inward_outward_chart_source_name];
	const company_filter = (chart_source && chart_source.filters || []).find(
		(filter) => filter.fieldname === "company"
	);
	if (!company_filter) return;

	try {
		const configured_company = await frappe.db.get_single_value("Cold Storage Settings", "company");
		if (configured_company) {
			company_filter.default = configured_company;
			company_filter.read_only = 1;
		} else {
			company_filter.read_only = 0;
		}
	} catch (error) {
		console.warn("Unable to load Cold Storage Settings company for chart source filter", error);
		company_filter.read_only = 0;
	}
});
