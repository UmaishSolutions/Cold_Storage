(() => {
	const PATCH_MARKER = "__cs_top_customers_horizontal_patch__";
	const STYLE_ID = "cs-top-customers-horizontal-style";
	const CHART_NAME = "Top Customers";

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
			.cs-hbar-empty {
				color: var(--text-muted);
				font-size: 12px;
				padding-top: 4px;
			}
		`;
		document.head.appendChild(style);
	};

	const renderHorizontalBars = (widget) => {
		if (!widget?.chart_doc || widget.chart_doc.name !== CHART_NAME) return;
		if (!widget.chart_wrapper || !widget.chart_wrapper.length) return;

		const labels = Array.isArray(widget.data?.labels) ? widget.data.labels : [];
		const values = Array.isArray(widget.data?.datasets?.[0]?.values)
			? widget.data.datasets[0].values
			: [];
		const points = labels
			.map((label, idx) => ({
				label: String(label ?? ""),
				value: safeFloat(values[idx]),
			}))
			.filter((point) => point.value > 0)
			.sort((left, right) => right.value - left.value)
			.slice(0, 8);

		const nativeChart = widget.chart_wrapper.find(".frappe-chart");
		if (nativeChart.length) {
			nativeChart.hide();
		}

		let container = widget.chart_wrapper.find(".cs-top-customers-horizontal");
		if (!container.length) {
			container = $('<div class="cs-top-customers-horizontal"></div>');
			widget.chart_wrapper.append(container);
		}

		if (!points.length) {
			const noDataText = __("No Data");
			container.html(`<div class="cs-hbar-empty">${escapeHtml(noDataText)}</div>`);
			return;
		}

		const maxValue = Math.max(...points.map((point) => point.value), 1);
		const rows = points
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

		container.html(rows);
	};

	const patchChartWidget = () => {
		const ChartWidget = frappe?.widget?.widget_factory?.chart;
		if (!ChartWidget || ChartWidget.prototype[PATCH_MARKER]) return false;

		const originalRender = ChartWidget.prototype.render;
		ChartWidget.prototype.render = async function (...args) {
			const result = await originalRender.apply(this, args);
			try {
				renderHorizontalBars(this);
			} catch (error) {
				console.warn("Cold Storage Top Customers horizontal render failed.", error);
			}
			return result;
		};

		ChartWidget.prototype[PATCH_MARKER] = true;
		return true;
	};

	const bootstrap = () => {
		injectStyles();

		if (patchChartWidget()) return;

		let attempts = 0;
		const interval = setInterval(() => {
			attempts += 1;
			if (patchChartWidget() || attempts > 30) {
				clearInterval(interval);
			}
		}, 400);
	};

	if (typeof frappe !== "undefined") {
		frappe.ready(bootstrap);
	} else {
		document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
	}
})();
