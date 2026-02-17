import frappe
from cold_storage.api.client_portal import _get_total_outstanding

def execute():
    print("--- Debugging Outstanding Amount ---")
    
    # 1. Check all Sales Invoices with outstanding > 0
    print("\n[All Outstanding Invoices]")
    invoices = frappe.db.sql("""
        select name, customer, outstanding_amount, docstatus 
        from `tabSales Invoice` 
        where outstanding_amount > 0
    """, as_dict=True)
    
    if not invoices:
        print("No invoices with outstanding amount found in the entire system.")
    else:
        for inv in invoices:
            print(f"- {inv.name}: {inv.customer} | Amount: {inv.outstanding_amount} | Status: {inv.docstatus}")

    # 2. Check total per customer using the function
    print("\n[Total per Customer using API logic]")
    customers = frappe.get_all("Customer", pluck="name")
    for customer in customers:
        total = _get_total_outstanding([customer])
        print(f"- {customer}: {total}")

if __name__ == "__main__":
    execute()
