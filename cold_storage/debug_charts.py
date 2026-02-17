import frappe
from cold_storage.api.client_portal import get_portal_snapshot
import json

def execute():
    print("--- Debugging Analytics Data ---")
    # Get a customer from the system
    customer = frappe.db.get_value("Customer", {}, "name")
    if not customer:
        print("No customers found.")
        return

    print(f"Fetching snapshot for customer: {customer}")
    
    # Mocking session user for permission checks (bypass if possible or set user)
    # Since we are running via bench execute, we might need to bypass permissions or assume admin
    # The API checks permissions, so this might fail if not simulating a user.
    # Let's try to bypass the check by mocking
    
    original_user = frappe.session.user
    frappe.session.user = "Administrator" # Admin has access
    
    try:
        data = get_portal_snapshot(limit=100, customer=customer)
        analytics = data.get("analytics", {})
        
        print("\n[Stock Composition]")
        print(json.dumps(analytics.get("stock_composition"), indent=2))
        
        print("\n[Movement Trends]")
        print(json.dumps(analytics.get("movement_trends"), indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        frappe.session.user = original_user

if __name__ == "__main__":
    execute()
