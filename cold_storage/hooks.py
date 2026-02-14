app_name = "cold_storage"
app_title = "Cold Storage"
app_publisher = "Umaish Solutions"
app_description = "Cold Storage App where the business model is Service-based (storing goods for others) rather than Trading-based"
app_email = "solutions@umaish.com"
app_license = "MIT"
app_logo_url = "/assets/cold_storage/images/cold-storage-logo.svg"
app_home = "/app/cold-storage"

# Apps
required_apps = ["erpnext"]

# Includes in <head>
# app_include_css = "/assets/cold_storage/css/cold_storage.css"
# app_include_js = "/assets/cold_storage/js/cold_storage.js"

desktop_data = "cold_storage.config.desktop.get_data"

add_to_apps_screen = [
	{
		"name": "cold_storage",
		"logo": app_logo_url,
		"title": app_title,
		"route": app_home,
	}
]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# Require all whitelisted methods to have type annotations
require_type_annotated_api_methods = True

after_install = "cold_storage.install.after_install"
after_migrate = "cold_storage.install.after_migrate"

fixtures = [
	{"dt": "Role", "filters": [["role_name", "like", "Cold Storage %"]]},
	{"dt": "Role Profile", "filters": [["role_profile", "like", "Cold Storage %"]]},
]

portal_menu_items = [
	{
		"title": "Cold Storage Portal",
		"route": "/client-portal",
		"reference_doctype": "Cold Storage Inward",
		"role": "Cold Storage Client Portal User",
	},
]

# ── Custom Fields ────────────────────────────────────────────────
# Add a "Customer" field to the standard ERPNext Batch DocType
# to enforce strict Batch → Customer ownership.

override_doctype_property = {
	"Batch": [
		{
			"fieldname": "batch_id",
			"property": "unique",
			"property_type": "Check",
			"value": "0",
		},
	],
}

custom_fields = {
	"Batch": [
		{
			"fieldname": "custom_customer",
			"fieldtype": "Link",
			"label": "Customer",
			"options": "Customer",
			"insert_after": "item_name",
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
	],
	"Warehouse": [
		{
			"fieldname": "custom_storage_capacity",
			"fieldtype": "Float",
			"label": "Storage Capacity",
			"insert_after": "warehouse_type",
			"in_standard_filter": 1,
			"non_negative": 1,
			"default": "0",
			"description": "Maximum storable quantity in this warehouse.",
		},
	],
}

# ── Document Events ─────────────────────────────────────────────
doc_events = {
	"Batch": {
		"validate": "cold_storage.events.batch.validate_batch_customer",
	},
	"Customer": {
		"on_update": "cold_storage.setup.client_portal_user_permissions.sync_customer_user_permissions_for_customer",
	},
	"GL Entry": {
		"autoname": "cold_storage.events.naming.autoname_cold_storage_gl_entry",
	},
}
