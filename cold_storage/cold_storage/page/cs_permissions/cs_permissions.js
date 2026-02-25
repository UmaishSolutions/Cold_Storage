/**
 * CS Roles & Permissions — centralised permission matrix for all Cold Storage doctypes.
 */
frappe.pages["cs-permissions"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Cold Storage — Roles & Permissions",
        single_column: true,
    });

    page.set_indicator("Loading…", "orange");

    const $main = $(wrapper).find(".layout-main-section");
    $main.css({ padding: "20px", background: "var(--fg-color)" });

    frappe.call({
        method: "cold_storage.cold_storage.page.cs_permissions.cs_permissions.get_permissions_matrix",
        callback(r) {
            page.set_indicator("");
            if (r.message) {
                renderMatrix($main, r.message, page);
            }
        },
    });
};

function renderMatrix($container, data, page) {
    const { roles, perm_types, doctype_groups, matrix } = data;
    const isAdmin = frappe.user_roles.includes("System Manager");

    const permLabels = {
        read: "R", write: "W", create: "C", delete: "D",
        submit: "Sub", cancel: "Can", amend: "Am",
        report: "Rpt", export: "Exp", print: "Prt",
        share: "Shr", email: "Em",
    };
    const permTitles = {
        read: "Read", write: "Write", create: "Create", delete: "Delete",
        submit: "Submit", cancel: "Cancel", amend: "Amend",
        report: "Report", export: "Export", print: "Print",
        share: "Share", email: "Email",
    };

    const corePT = ["read", "write", "create", "delete"];
    const submitPT = ["submit", "cancel", "amend"];
    const otherPT = ["report", "export", "print", "share", "email"];

    let html = `
		<style>
			.cs-perm-wrapper { font-family: var(--font-stack); }
			.cs-perm-legend {
				display: flex; gap: 16px; flex-wrap: wrap;
				margin-bottom: 20px; padding: 12px 16px;
				background: var(--subtle-fg); border-radius: 8px;
			}
			.cs-perm-legend-item {
				display: flex; align-items: center; gap: 6px;
				font-size: 12px; color: var(--text-muted);
			}
			.cs-perm-legend-dot {
				width: 14px; height: 14px; border-radius: 3px; display: inline-block;
			}
			.cs-perm-group-header {
				font-size: 16px; font-weight: 700; color: var(--heading-color);
				margin: 24px 0 10px 0; padding-left: 10px;
				border-left: 4px solid #0dcaf0; padding: 0 4px 0 10px;
			}
			.cs-perm-group-header:first-child { margin-top: 0; }
			.cs-perm-table {
				width: 100%; border-collapse: separate; border-spacing: 0;
				border: 1px solid var(--border-color); border-radius: 8px;
				overflow: hidden; margin-bottom: 16px; font-size: 12px;
			}
			.cs-perm-table thead th {
				background: var(--subtle-fg); padding: 6px 4px;
				font-weight: 600; text-align: center;
				border-bottom: 2px solid var(--border-color);
				position: sticky; top: 0; z-index: 1;
				color: var(--heading-color); font-size: 11px;
			}
			.cs-perm-table thead th:first-child { text-align: left; padding-left: 12px; min-width: 180px; }
			.cs-perm-table thead th.role-header {
				border-left: 2px solid var(--border-color);
				font-size: 10px; font-weight: 700; color: #0dcaf0;
			}
			.cs-perm-table thead th.perm-subheader {
				font-size: 10px; font-weight: 500;
				color: var(--text-muted); padding: 3px 2px;
			}
			.cs-perm-table tbody tr { transition: background 0.15s; }
			.cs-perm-table tbody tr:hover { background: var(--subtle-fg); }
			.cs-perm-table tbody td {
				padding: 4px 2px; text-align: center;
				border-bottom: 1px solid var(--border-color);
			}
			.cs-perm-table tbody td:first-child {
				text-align: left; padding-left: 12px;
				font-weight: 500; color: var(--heading-color);
			}
			.cs-perm-table tbody td.role-start { border-left: 2px solid var(--border-color); }
			.cs-dot {
				width: 16px; height: 16px; border-radius: 3px;
				display: inline-block; cursor: default; transition: all 0.15s;
			}
			.cs-dot.granted { background: #0dcaf0; }
			.cs-dot.denied { background: var(--control-bg); border: 1px solid var(--border-color); }
			.cs-dot.na { background: transparent; }
			${isAdmin ? '.cs-dot.editable { cursor: pointer; } .cs-dot.editable:hover { transform: scale(1.3); box-shadow: 0 0 6px rgba(0,0,0,0.15); }' : ''}
			.cs-summary-cards {
				display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
				gap: 12px; margin-bottom: 24px;
			}
			.cs-summary-card {
				padding: 16px; border-radius: 8px; text-align: center;
				border: 1px solid var(--border-color); background: var(--card-bg);
			}
			.cs-summary-card .count { font-size: 28px; font-weight: 700; color: #0dcaf0; }
			.cs-summary-card .label { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
		</style>
		<div class="cs-perm-wrapper">
	`;

    // Summary cards
    const totalDoctypes = Object.keys(matrix).length;
    const totalRoles = roles.length;
    const totalGroups = Object.keys(doctype_groups).length;
    let totalGranted = 0;
    Object.values(matrix).forEach(dt => {
        Object.values(dt.permissions).forEach(rp => {
            perm_types.forEach(pt => { if (rp[pt]) totalGranted++; });
        });
    });

    html += `
		<div class="cs-summary-cards">
			<div class="cs-summary-card"><div class="count">${totalDoctypes}</div><div class="label">DocTypes</div></div>
			<div class="cs-summary-card"><div class="count">${totalRoles}</div><div class="label">Roles</div></div>
			<div class="cs-summary-card"><div class="count">${totalGroups}</div><div class="label">Groups</div></div>
			<div class="cs-summary-card"><div class="count">${totalGranted}</div><div class="label">Permissions Granted</div></div>
		</div>
		<div class="cs-perm-legend">
			<div class="cs-perm-legend-item"><span class="cs-perm-legend-dot" style="background:#0dcaf0;"></span> Granted</div>
			<div class="cs-perm-legend-item"><span class="cs-perm-legend-dot" style="background:var(--control-bg);border:1px solid var(--border-color);"></span> Not Granted</div>
			<div class="cs-perm-legend-item"><span class="cs-perm-legend-dot" style="background:transparent;border:1px dashed var(--border-color);"></span> N/A</div>
			${isAdmin ? '<div class="cs-perm-legend-item">💡 Click any cell to toggle (System Manager only)</div>' : ''}
		</div>
	`;

    // Render each group
    for (const [group, doctypes] of Object.entries(doctype_groups)) {
        html += `<div class="cs-perm-group-header">${group}</div>`;
        html += `<div style="overflow-x:auto;"><table class="cs-perm-table"><thead><tr><th rowspan="2">DocType</th>`;
        for (const role of roles) {
            const shortRole = role.replace("Cold Storage ", "CS ");
            const ptCount = corePT.length + submitPT.length + otherPT.length;
            html += `<th colspan="${ptCount}" class="role-header">${shortRole}</th>`;
        }
        html += `</tr><tr>`;
        for (const role of roles) {
            [...corePT, ...submitPT, ...otherPT].forEach((pt, i) => {
                const cls = i === 0 ? 'perm-subheader role-start' : 'perm-subheader';
                html += `<th class="${cls}" title="${permTitles[pt]}">${permLabels[pt]}</th>`;
            });
        }
        html += `</tr></thead><tbody>`;

        for (const dt of doctypes) {
            if (!matrix[dt]) continue;
            const dtData = matrix[dt];
            const dtLink = `<a href="/app/${frappe.router.slug(dt)}" style="color:var(--heading-color);">${dt}</a>`;
            html += `<tr><td>${dtLink}</td>`;
            for (const role of roles) {
                const rp = dtData.permissions[role] || {};
                [...corePT, ...submitPT, ...otherPT].forEach((pt, i) => {
                    const tdCls = i === 0 ? 'role-start' : '';
                    const isNA = submitPT.includes(pt) && !dtData.is_submittable;
                    let dotCls = "cs-dot";
                    if (isNA) dotCls += " na";
                    else if (rp[pt]) dotCls += " granted";
                    else dotCls += " denied";
                    if (isAdmin && !isNA) dotCls += " editable";
                    const attrs = isAdmin && !isNA
                        ? `data-doctype="${dt}" data-role="${role}" data-perm="${pt}" data-val="${rp[pt] ? 1 : 0}"`
                        : '';
                    html += `<td class="${tdCls}"><span class="${dotCls}" ${attrs} title="${permTitles[pt]}: ${isNA ? 'N/A' : (rp[pt] ? 'Yes' : 'No')}"></span></td>`;
                });
            }
            html += `</tr>`;
        }
        html += `</tbody></table></div>`;
    }

    // --- Client Portal Access Section ---
    const portalAccess = data.portal_access || [];
    if (portalAccess.length) {
        html += `
            <div class="cs-perm-group-header" style="border-left-color:#6f42c1;">
                ❄️ Client Portal Access <span style="font-size:12px;font-weight:400;color:var(--text-muted);">(Cold Storage Client Portal User)</span>
            </div>
            <p style="font-size:13px;color:var(--text-muted);margin:0 0 10px 14px;">
                Portal users access data through the <code>/cs-portal</code> API — all queries are automatically scoped to their linked Customer(s).
            </p>
            <div style="overflow-x:auto;">
            <table class="cs-perm-table">
                <thead>
                    <tr>
                        <th style="text-align:left;padding-left:12px;min-width:160px;">Feature</th>
                        <th style="text-align:left;min-width:280px;">Description</th>
                        <th style="text-align:left;min-width:200px;">API Endpoint</th>
                        <th style="text-align:left;min-width:180px;">Access Level</th>
                    </tr>
                </thead>
                <tbody>`;
        for (const item of portalAccess) {
            html += `
                <tr>
                    <td style="font-weight:600;">${item.feature}</td>
                    <td style="color:var(--text-muted);">${item.description}</td>
                    <td><code style="font-size:11px;background:var(--subtle-fg);padding:2px 6px;border-radius:3px;">${item.api}</code></td>
                    <td><span style="background:#6f42c1;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;">${item.access}</span></td>
                </tr>`;
        }
        html += `</tbody></table></div>`;
    }

    html += `</div>`;

    $container.html(html);

    // Click handler
    if (isAdmin) {
        $container.on("click", ".cs-dot.editable", function () {
            const $dot = $(this);
            const dt = $dot.data("doctype");
            const role = $dot.data("role");
            const perm = $dot.data("perm");
            const cur = $dot.data("val");
            const next = cur ? 0 : 1;
            frappe.call({
                method: "cold_storage.cold_storage.page.cs_permissions.cs_permissions.update_permission",
                args: { doctype: dt, role: role, perm_type: perm, value: next },
                callback() {
                    $dot.data("val", next);
                    if (next) { $dot.removeClass("denied").addClass("granted").attr("title", `${permTitles[perm]}: Yes`); }
                    else { $dot.removeClass("granted").addClass("denied").attr("title", `${permTitles[perm]}: No`); }
                },
            });
        });
    }

    // Refresh button
    page.set_primary_action("Refresh", () => {
        page.set_indicator("Refreshing…", "orange");
        frappe.call({
            method: "cold_storage.cold_storage.page.cs_permissions.cs_permissions.get_permissions_matrix",
            callback(r) { page.set_indicator(""); if (r.message) renderMatrix($container, r.message, page); },
        });
    }, "refresh");
}
