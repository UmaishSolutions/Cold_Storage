import os

# Paths
LIB_PATH = "/home/frappe/frappe-bench/apps/frappe/node_modules/frappe-charts/dist/frappe-charts.umd.js"
TARGET_PATH = "/home/frappe/frappe-bench/apps/cold_storage/cold_storage/www/client-portal.html"

def execute():
    try:
        # Read Library
        with open(LIB_PATH, "r") as f:
            lib_content = f.read()
        
        # Read Target
        with open(TARGET_PATH, "r") as f:
            target_content = f.read()
            
        # Check if already injected
        if "var frappe=frappe||{};frappe.Chart=Chart;" in target_content:
             print("Library already seems to be injected.")
             return

        # Prepare Injection
        # We inject it inside block page_content
        injection = f"""<script>
{lib_content}
// Ensure frappe.Chart alias matches standard
var frappe=frappe||{{}};
if(!frappe.Chart && window.Chart) frappe.Chart = window.Chart;
console.log("[DEBUG] Inlined Chart lib loaded");
</script>
"""
        
        # Find insertion point
        search_str = "{% block page_content %}"
        insert_idx = target_content.find(search_str)
        
        if insert_idx == -1:
            print("Could not find block page_content")
            return
            
        final_content = target_content[:insert_idx + len(search_str)] + "\n" + injection + target_content[insert_idx + len(search_str):]
        
        # Write back
        with open(TARGET_PATH, "w") as f:
            f.write(final_content)
            
        print("Successfully inlined frappe-charts library.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    execute()
