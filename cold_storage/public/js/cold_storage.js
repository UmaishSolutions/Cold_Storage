(() => {
	const PATCH_MARKER = "__cs_top_customers_horizontal_patch__";
	const STYLE_ID = "cs-top-customers-horizontal-style";
	const CHART_NAME = "Top Customers";
	const REPORT_NAME = "Cold Storage Customer Register";
	const LEGACY_AUDIT_REPORT_NAME = "Cold Storage Audit Trail & Compliance Pack";
	const AUDIT_REPORT_NAME = "Cold Storage Audit Trail Compliance Pack";
	const LEGACY_AUDIT_REPORT_ROUTE = `query-report/${LEGACY_AUDIT_REPORT_NAME}`;
	const AUDIT_REPORT_ROUTE = `query-report/${AUDIT_REPORT_NAME}`;
	const SIDEBAR_ROOT_SELECTOR = ".body-sidebar";
	const SIDEBAR_HEADER_LOGO_PATH = "/assets/cold_storage/images/cold-storage-logo.svg";
	const SIDEBAR_SECTION_COLOR_VARS = {
		Operations: "--cs-operations",
		Reports: "--cs-reports",
		Registers: "--cs-registers",
		"Inventory & Movement": "--cs-inventory",
		"Customer & Billing": "--cs-billing",
		"Compliance & Activity": "--cs-compliance",
		Setup: "--cs-setup",
		Masters: "--cs-masters",
	};
	const SIDEBAR_ITEM_COLOR_VARS = {
		Home: "--cs-home",
	};

	let hydrateInProgress = false;

	const registerLegacyAuditRoute = () => {
		if (typeof frappe === "undefined") return;
		frappe.re_route = frappe.re_route || {};
		frappe.re_route[LEGACY_AUDIT_REPORT_ROUTE] = AUDIT_REPORT_ROUTE;
	};

	const redirectLegacyAuditReportRoute = () => {
		if (typeof frappe === "undefined" || !frappe.get_route) return;
		const route = frappe.get_route() || [];
		if (route[0] !== "query-report" || route[1] !== LEGACY_AUDIT_REPORT_NAME) return;
		frappe.set_route("query-report", AUDIT_REPORT_NAME);
	};

	const safeFloat = (value) => {
		const number = Number(value);
		return Number.isFinite(number) ? number : 0;
	};

	const formatQty = (value) => {
		if (typeof frappe !== "undefined" && frappe.format_number) {
			return frappe.format_number(value, null, 2);
		}
		return safeFloat(value).toFixed(2);
	};

	const escapeHtml = (value) => {
		if (typeof frappe !== "undefined" && frappe.utils?.escape_html) {
			return frappe.utils.escape_html(String(value ?? ""));
		}
		return String(value ?? "")
			.replaceAll("&", "&amp;")
			.replaceAll("<", "&lt;")
			.replaceAll(">", "&gt;")
			.replaceAll('"', "&quot;")
			.replaceAll("'", "&#39;");
	};

	const injectStyles = () => {
		if (document.getElementById(STYLE_ID)) return;

		const style = document.createElement("style");
		style.id = STYLE_ID;
		style.textContent = `
			.cs-top-customers-horizontal {
				padding: 8px 2px 2px;
			}
			.cs-hbar-row {
				display: grid;
				grid-template-columns: minmax(120px, 1.6fr) minmax(140px, 3fr) minmax(72px, 0.9fr);
				align-items: center;
				gap: 10px;
				margin-bottom: 10px;
			}
			.cs-hbar-row:last-of-type {
				margin-bottom: 6px;
			}
			.cs-hbar-label {
				color: var(--text-color);
				font-size: 12px;
				font-weight: 500;
				overflow: hidden;
				text-overflow: ellipsis;
				white-space: nowrap;
			}
			.cs-hbar-track {
				height: 14px;
				border-radius: 999px;
				background: color-mix(in srgb, var(--gray-200) 80%, white 20%);
				overflow: hidden;
			}
			.cs-hbar-fill {
				height: 100%;
				border-radius: 999px;
				background: linear-gradient(90deg, #0ea5a4 0%, #22c55e 100%);
			}
			.cs-hbar-value {
				text-align: right;
				color: var(--text-muted);
				font-size: 12px;
				font-weight: 600;
				font-variant-numeric: tabular-nums;
			}
			.cs-hbar-axis {
				display: grid;
				grid-template-columns: minmax(120px, 1.6fr) minmax(140px, 3fr) minmax(72px, 0.9fr);
				gap: 10px;
				align-items: start;
				margin-top: 2px;
			}
			.cs-hbar-axis-label {
				color: var(--text-muted);
				font-size: 11px;
				font-weight: 600;
			}
			.cs-hbar-scale {
				position: relative;
				padding-top: 8px;
			}
			.cs-hbar-scale-line {
				height: 1px;
				background: color-mix(in srgb, var(--gray-400) 55%, white 45%);
			}
			.cs-hbar-scale-ticks {
				display: grid;
				grid-template-columns: repeat(5, 1fr);
				margin-top: 3px;
			}
			.cs-hbar-scale-tick {
				color: var(--text-muted);
				font-size: 10px;
				font-variant-numeric: tabular-nums;
			}
			.cs-hbar-scale-tick:first-child {
				text-align: left;
			}
			.cs-hbar-scale-tick:not(:first-child):not(:last-child) {
				text-align: center;
			}
			.cs-hbar-scale-tick:last-child {
				text-align: right;
			}
			.cs-hbar-empty {
				color: var(--text-muted);
				font-size: 12px;
				padding-top: 4px;
			}
		`;
		document.head.appendChild(style);
	};

	const toPoints = (labels, values) =>
		labels
			.map((label, idx) => ({
				label: String(label ?? ""),
				value: safeFloat(values[idx]),
			}))
			.filter((point) => point.value > 0)
			.sort((left, right) => right.value - left.value)
			.slice(0, 10);

	const hideNativeChart = (rootEl) => {
		rootEl.querySelectorAll(".frappe-chart").forEach((node) => {
			node.style.display = "none";
		});
	};

	const ensureHorizontalContainer = (rootEl) => {
		let container = rootEl.querySelector(".cs-top-customers-horizontal");
		if (!container) {
			container = document.createElement("div");
			container.className = "cs-top-customers-horizontal";
			rootEl.appendChild(container);
		}
		return container;
	};

	const renderPoints = (container, points) => {
		if (!points.length) {
			container.innerHTML = `<div class="cs-hbar-empty">${escapeHtml(__("No Data"))}</div>`;
			return;
		}

		const maxValue = Math.max(...points.map((point) => point.value), 1);
		const rowsHtml = points
			.map((point) => {
				const percent = Math.max(2, (point.value / maxValue) * 100);
				return `
					<div class="cs-hbar-row">
						<div class="cs-hbar-label" title="${escapeHtml(point.label)}">${escapeHtml(point.label)}</div>
						<div class="cs-hbar-track">
							<div class="cs-hbar-fill" style="width: ${percent}%"></div>
						</div>
						<div class="cs-hbar-value">${escapeHtml(formatQty(point.value))}</div>
					</div>
				`;
			})
			.join("");

		const tickValues = [0, 0.25, 0.5, 0.75, 1].map((factor) => formatQty(maxValue * factor));
		const axisHtml = `
			<div class="cs-hbar-axis">
				<div class="cs-hbar-axis-label">${escapeHtml(__("Customer (Y)"))}</div>
				<div class="cs-hbar-scale">
					<div class="cs-hbar-scale-line"></div>
					<div class="cs-hbar-scale-ticks">
						${tickValues.map((value) => `<div class="cs-hbar-scale-tick">${escapeHtml(value)}</div>`).join("")}
					</div>
				</div>
				<div class="cs-hbar-axis-label" style="text-align: right;">${escapeHtml(__("Qty (X)"))}</div>
			</div>
		`;

		container.innerHTML = rowsHtml + axisHtml;
	};

	const renderHorizontalBars = (rootEl, labels, values) => {
		const points = toPoints(labels, values);
		hideNativeChart(rootEl);
		renderPoints(ensureHorizontalContainer(rootEl), points);
	};

	const renderFromWidgetInstance = (widget) => {
		if (!widget?.chart_doc || widget.chart_doc.name !== CHART_NAME) return;
		const rootEl = widget.chart_wrapper?.[0] || widget.chart_wrapper;
		if (!rootEl) return;

		const labels = Array.isArray(widget.data?.labels) ? widget.data.labels : [];
		const values = Array.isArray(widget.data?.datasets?.[0]?.values)
			? widget.data.datasets[0].values
			: [];
		renderHorizontalBars(rootEl, labels, values);
	};

	const patchChartWidget = () => {
		const ChartWidget = frappe?.widget?.widget_factory?.chart;
		if (!ChartWidget || ChartWidget.prototype[PATCH_MARKER]) return false;

		const originalRender = ChartWidget.prototype.render;
		ChartWidget.prototype.render = async function (...args) {
			const result = await originalRender.apply(this, args);
			try {
				renderFromWidgetInstance(this);
			} catch (error) {
				console.warn("Cold Storage Top Customers horizontal render failed.", error);
			}
			return result;
		};

		ChartWidget.prototype[PATCH_MARKER] = true;
		return true;
	};

	const getTopCustomersWidgetBody = () => {
		const widgets = document.querySelectorAll(".widget");
		for (const widget of widgets) {
			const titleEl = widget.querySelector(".widget-title");
			if ((titleEl?.textContent || "").trim() === CHART_NAME) {
				return widget.querySelector(".widget-body");
			}
		}
		return null;
	};

	const hydrateCurrentPageWidget = async () => {
		if (hydrateInProgress) return;

		const body = getTopCustomersWidgetBody();
		if (!body) return;

		if (body.querySelector(".cs-top-customers-horizontal")) {
			hideNativeChart(body);
			return;
		}

		hydrateInProgress = true;
		try {
			const result = await frappe.xcall("frappe.desk.query_report.run", {
				report_name: REPORT_NAME,
				filters: {},
				ignore_prepared_report: 1,
			});
			const labels = result?.chart?.data?.labels || [];
			const values = result?.chart?.data?.datasets?.[0]?.values || [];
			renderHorizontalBars(body, labels, values);
		} catch (error) {
			console.warn("Cold Storage Top Customers hydrate failed.", error);
		} finally {
			hydrateInProgress = false;
		}
	};

	const ensurePatchedEventually = (attempt = 0) => {
		if (patchChartWidget()) return;
		if (attempt >= 180) return;
		setTimeout(() => ensurePatchedEventually(attempt + 1), 1000);
	};

	const isColdStorageSidebar = (sidebar) => {
		if (!sidebar) return false;
		const title = (sidebar.getAttribute("data-title") || "").trim().toLowerCase();
		return (
			title === "cold storage" ||
			title === "cold-storage" ||
			title === "cold_storage" ||
			title.includes("cold storage")
		);
	};

	const paintIcon = (element, color) => {
		if (!element || !color) return;
		element.style.setProperty("color", color, "important");
		element.style.setProperty("stroke", color, "important");
	};

	const resolveColorFromVar = (sidebar, variableName, fallback) => {
		const value = getComputedStyle(sidebar).getPropertyValue(variableName).trim();
		return value || fallback;
	};

	const applyColoredSidebarIcons = () => {
		const sidebar = document.querySelector(SIDEBAR_ROOT_SELECTOR);
		if (!isColdStorageSidebar(sidebar)) return;

		const allItems = sidebar.querySelectorAll(".sidebar-item-container");
		allItems.forEach((item) => {
			const label = (item.getAttribute("item-name") || "").trim();
			const icon = item.querySelector(".item-anchor > .sidebar-item-icon");
			if (!icon) return;

			if (SIDEBAR_ITEM_COLOR_VARS[label]) {
				const color = resolveColorFromVar(sidebar, SIDEBAR_ITEM_COLOR_VARS[label], "#0284c7");
				paintIcon(icon, color);
			}
		});

		Object.entries(SIDEBAR_SECTION_COLOR_VARS).forEach(([sectionLabel, colorVar]) => {
			const section = sidebar.querySelector(
				`.sidebar-item-container[item-name="${sectionLabel}"]`
			);
			if (!section) return;
			const color = resolveColorFromVar(sidebar, colorVar, "#0ea5e9");

			paintIcon(section.querySelector(".item-anchor > .sidebar-item-icon"), color);
			section
				.querySelectorAll(".nested-container .sidebar-item-icon")
				.forEach((nestedIcon) => paintIcon(nestedIcon, color));
		});
	};

	const applyColoredSidebarHeaderIcon = () => {
		const sidebar = document.querySelector(SIDEBAR_ROOT_SELECTOR);
		if (!isColdStorageSidebar(sidebar)) return;

		const headerLogo = sidebar.querySelector(".sidebar-header .header-logo");
		if (!headerLogo) return;

		if (!headerLogo.querySelector("img[data-cs-header-logo='1']")) {
			headerLogo.innerHTML = `<img data-cs-header-logo="1" src="${SIDEBAR_HEADER_LOGO_PATH}" alt="Cold Storage" style="width: 18px; height: 18px; object-fit: contain;" />`;
		}
	};

	const scheduleSidebarIconColoring = () => {
		[0, 300, 900].forEach((delay) => {
			setTimeout(() => {
				applyColoredSidebarIcons();
				applyColoredSidebarHeaderIcon();
			}, delay);
		});
	};

	const bootstrap = () => {
		registerLegacyAuditRoute();
		redirectLegacyAuditReportRoute();
		injectStyles();
		ensurePatchedEventually();
		scheduleSidebarIconColoring();
		setTimeout(hydrateCurrentPageWidget, 1200);

		if (frappe.router?.on) {
			frappe.router.on("change", () => {
				redirectLegacyAuditReportRoute();
				scheduleSidebarIconColoring();
			});
		}

		if (typeof $ !== "undefined") {
			$(document).on("sidebar_setup", () => {
				scheduleSidebarIconColoring();
			});
			$(document).on("page-change", () => {
				redirectLegacyAuditReportRoute();
				setTimeout(() => {
					ensurePatchedEventually();
					hydrateCurrentPageWidget();
					scheduleSidebarIconColoring();
				}, 800);
			});
		}
	};

	if (typeof frappe !== "undefined") {
		frappe.ready(bootstrap);
	} else {
		document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
	}
})();
