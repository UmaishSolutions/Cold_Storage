import frappe

def execute():
    try:
        frappe.reload_doc("cold_storage", "doctype", "cold_storage_settings")
        print("Successfully reloaded Cold Storage Settings")
        
        # Verify
        meta = frappe.get_meta("Cold Storage Settings")
        # Try reading value
        val = frappe.db.get_single_value("Cold Storage Settings", "portal_announcement")
        print(f"Value read successfully: {val}")
             
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    execute()
