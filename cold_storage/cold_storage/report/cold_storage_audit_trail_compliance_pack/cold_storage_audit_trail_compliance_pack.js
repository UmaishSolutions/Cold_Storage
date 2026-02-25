const AUDIT_TRAIL_REPORT = "Cold Storage Audit Trail Compliance Pack";

const update_customer_item_cache = async (query_report) => {
	const report_config = frappe.query_reports[AUDIT_TRAIL_REPORT];
	if (!report_config) return;

	report_config.customer_item_codes = [];
	const customer = query_report.get_filter_value("customer");
	if (!customer) return;

	try {
		const batch_rows = await frappe.db.get_list("Batch", {
			fields: ["item"],
			filters: { custom_customer: customer },
			limit_page_length: 5000,
		});
		report_config.customer_item_codes = [
			...new Set((batch_rows || []).map((row) => row.item).filter(Boolean)),
		];
	} catch (error) {
		console.warn("Unable to load customer item cache for audit report", error);
	}
};

frappe.query_reports[AUDIT_TRAIL_REPORT] = {
	customer_item_codes: [],
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
			console.warn("Unable to load Cold Storage Settings company for report filter", error);
			company_filter.df.read_only = 0;
			company_filter.refresh();
		}

		await update_customer_item_cache(query_report);
	},
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			on_change: async (query_report) => {
				await update_customer_item_cache(query_report);
				const item_filter = query_report.get_filter("item", false);
				const batch_filter = query_report.get_filter("batch_no", false);

				if (item_filter) {
					item_filter.set_value("");
					item_filter.refresh();
				}
				if (batch_filter) {
					batch_filter.set_value("");
					batch_filter.refresh();
				}
				query_report.refresh();
			},
		},
		{
			fieldname: "item",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			get_query: () => {
				const customer = frappe.query_report.get_filter_value("customer");
				const customer_items = frappe.query_reports[AUDIT_TRAIL_REPORT].customer_item_codes || [];
				if (customer && customer_items.length) {
					return {
						filters: {
							name: ["in", customer_items],
						},
					};
				}
				return {};
			},
		},
		{
			fieldname: "batch_no",
			label: __("Batch"),
			fieldtype: "Link",
			options: "Batch",
			get_query: () => {
				const filters = {};
				const customer = frappe.query_report.get_filter_value("customer");
				const item = frappe.query_report.get_filter_value("item");
				if (customer) filters.custom_customer = customer;
				if (item) filters.item = item;
				return { filters };
			},
			reqd: 1,
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
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nSubmitted\nCancelled",
		},
		{
			fieldname: "include_user_actions",
			label: __("Include User Actions"),
			fieldtype: "Check",
			default: 1,
		},
	],
};
