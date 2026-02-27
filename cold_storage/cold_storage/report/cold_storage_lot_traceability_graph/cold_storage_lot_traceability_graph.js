frappe.query_reports["Cold Storage Lot Traceability Graph"] = {
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
			fieldname: "item",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			get_query: () => ({
				query: "cold_storage.cold_storage.utils.search_items_for_customer_movement",
				filters: {
					customer: frappe.query_report.get_filter_value("customer"),
				},
			}),
			description: __("Filter by item."),
		},
		{
			fieldname: "batch_no",
			label: __("Batch"),
			fieldtype: "Link",
			options: "Batch",
			reqd: 1,
			get_query: () => ({
				query: "cold_storage.cold_storage.utils.search_batches_for_customer_item",
				filters: {
					customer: frappe.query_report.get_filter_value("customer"),
					item: frappe.query_report.get_filter_value("item"),
				},
			}),
			description: __("Select lot/batch to trace end-to-end lineage."),
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: () => ({
				query: "cold_storage.cold_storage.utils.search_warehouses_for_batch",
				filters: {
					company: frappe.query_report.get_filter_value("company"),
					customer: frappe.query_report.get_filter_value("customer"),
					item: frappe.query_report.get_filter_value("item"),
					batch_no: frappe.query_report.get_filter_value("batch_no"),
				},
			}),
			description: __("Optional warehouse-level trace filter."),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			description: __("Optional start date for lineage events."),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			description: __("Optional end date for lineage events."),
		},
	],
};
