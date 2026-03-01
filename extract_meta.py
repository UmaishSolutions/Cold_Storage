import frappe
import json

def get_app_meta():
    cold_storage_doctypes = frappe.get_all("DocType", filters={"module": "Cold Storage"}, pluck="name")
    
    output = {"doctypes": {}, "reports": {}}
    for dt in cold_storage_doctypes:
        meta = frappe.get_meta(dt)
        fields = []
        for f in meta.fields:
            fields.append({
                "fieldname": f.fieldname,
                "label": f.label,
                "fieldtype": f.fieldtype,
                "description": f.description
            })
        output["doctypes"][dt] = {
            "description": meta.description,
            "fields": fields
        }
        
    cold_storage_reports = frappe.get_all("Report", filters={"module": "Cold Storage"}, pluck="name")
    for rep in cold_storage_reports:
        doc = frappe.get_doc("Report", rep)
        columns = []
        if doc.json:
            try:
                parsed_json = json.loads(doc.json)
                if "columns" in parsed_json:
                    columns = parsed_json["columns"]
            except:
                pass
        
        output["reports"][rep] = {
            "description": doc.report_type,
            "columns": columns,
            "filters": [f.fieldname for f in doc.filters] if getattr(doc, "filters", None) else []
        }
        
    with open("/home/frappe/frappe-bench/apps/cold_storage/meta_dump.json", "w") as f:
        json.dump(output, f, indent=2)

