/**
 * Cold Storage – Top Customers horizontal bar chart.
 *
 * Replaces the native Frappe vertical bar chart for "Top Customers"
 * with custom horizontal bars rendered via DOM manipulation.
 */
(() => {
	"use strict";

	const CHART_NAME = "Top Customers";
	const STYLE_ID = "cs-hbar-style";
	const MARKER = "csHbarDone";

	/* ── Helpers ─────────────────────────────────── */

	const n = (v) => { const x = Number(v); return Number.isFinite(x) ? x : 0; };

	const fmt = (v) =>
		typeof frappe !== "undefined" && frappe.format_number
			? frappe.format_number(v, null, 2)
			: n(v).toFixed(2);

	const esc = (v) =>
		String(v ?? "")
			.replace(/&/g, "&amp;").replace(/</g, "&lt;")
			.replace(/>/g, "&gt;").replace(/"/g, "&quot;");

	/* ── CSS ─────────────────────────────────────── */

	const injectCSS = () => {
		if (document.getElementById(STYLE_ID)) return;
		const s = document.createElement("style");
		s.id = STYLE_ID;
		s.textContent = `
.cs-hbar-wrap{padding:12px 4px 4px}
.cs-hbar-row{display:grid;grid-template-columns:minmax(110px,1.5fr) minmax(120px,3fr) minmax(68px,.9fr);align-items:center;gap:10px;margin-bottom:10px}
.cs-hbar-label{font-size:12px;font-weight:500;color:var(--text-color);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cs-hbar-track{height:16px;border-radius:999px;background:var(--gray-100,#f3f3f3);overflow:hidden}
.cs-hbar-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#0ea5a4,#22c55e);transition:width .5s ease}
.cs-hbar-val{text-align:right;font-size:12px;font-weight:600;color:var(--text-muted);font-variant-numeric:tabular-nums}
`;
		document.head.appendChild(s);
	};

	/* ── Render bars ─────────────────────────────── */

	const renderBars = (container, labels, values) => {
		const pts = labels
			.map((l, i) => ({ l: String(l ?? ""), v: n(values[i]) }))
			.filter(p => p.v > 0)
			.sort((a, b) => b.v - a.v)
			.slice(0, 10);

		if (!pts.length) {
			container.innerHTML = '<div style="color:var(--text-muted);padding:8px">No Data</div>';
			return;
		}

		const mx = Math.max(...pts.map(p => p.v), 1);
		container.innerHTML = pts.map(p => {
			const pct = Math.max(2, (p.v / mx) * 100);
			return `<div class="cs-hbar-row">
				<div class="cs-hbar-label" title="${esc(p.l)}">${esc(p.l)}</div>
				<div class="cs-hbar-track"><div class="cs-hbar-fill" style="width:${pct}%"></div></div>
				<div class="cs-hbar-val">${esc(fmt(p.v))}</div>
			</div>`;
		}).join("");
	};

	/* ── Extract data from frappe-chart SVG ──────── */

	const extractFromSVG = (svgEl) => {
		const labels = [];
		const values = [];

		// x-axis labels
		svgEl.querySelectorAll(".x.axis text, .x-axis text").forEach(el => {
			const t = el.textContent.trim();
			if (t) labels.push(t);
		});

		// Bar heights → data values (from data-point-value attributes or bar tooltips)
		const bars = svgEl.querySelectorAll("rect.bar, .dataset-units rect");
		bars.forEach(bar => {
			const val = bar.getAttribute("data-value");
			if (val !== null) {
				values.push(n(val));
			}
		});

		return { labels, values };
	};

	/* ── Fetch data via API as fallback ──────────── */

	const fetchData = () => {
		return frappe.xcall("frappe.desk.query_report.run", {
			report_name: "Cold Storage Customer Register",
			filters: {},
			ignore_prepared_report: 1
		}).then(result => {
			if (result && result.chart && result.chart.data) {
				const d = result.chart.data;
				return {
					labels: d.labels || [],
					values: d.datasets?.[0]?.values || []
				};
			}
			return null;
		});
	};

	/* ── Find & replace the chart ────────────────── */

	const processChart = () => {
		// Try both possible widget-name values
		let widget = document.querySelector(`.widget[data-widget-name="${CHART_NAME}"]`);

		// If not found by exact name, search by title text
		if (!widget) {
			document.querySelectorAll(".widget .widget-title .ellipsis").forEach(el => {
				if (el.textContent.trim() === CHART_NAME) {
					widget = el.closest(".widget");
				}
			});
		}

		if (!widget) return;
		if (widget.dataset[MARKER]) return;

		// Check widget-body for a rendered chart
		const body = widget.querySelector(".widget-body");
		if (!body) return;

		const svgChart = body.querySelector(".frappe-chart");
		if (!svgChart) return; // Chart hasn't rendered yet

		// Mark immediately to prevent re-processing
		widget.dataset[MARKER] = "1";

		// Try to extract data from SVG first
		let { labels, values } = extractFromSVG(svgChart);

		if (labels.length && values.length && labels.length === values.length) {
			// Hide native chart, show horizontal bars
			svgChart.style.display = "none";
			const chartDiv = svgChart.closest("div");
			let wrap = chartDiv.querySelector(".cs-hbar-wrap");
			if (!wrap) {
				wrap = document.createElement("div");
				wrap.className = "cs-hbar-wrap";
				chartDiv.appendChild(wrap);
			}
			renderBars(wrap, labels, values);
		} else {
			// Fallback: fetch data via API
			fetchData().then(data => {
				if (!data || !data.labels.length) return;

				svgChart.style.display = "none";
				const chartDiv = svgChart.closest("div");
				let wrap = chartDiv.querySelector(".cs-hbar-wrap");
				if (!wrap) {
					wrap = document.createElement("div");
					wrap.className = "cs-hbar-wrap";
					chartDiv.appendChild(wrap);
				}
				renderBars(wrap, data.labels, data.values);
			}).catch(err => {
				console.warn("CS hbar: API fallback failed", err);
				// Remove marker so it can retry
				delete widget.dataset[MARKER];
			});
		}
	};

	/* ── Bootstrap ───────────────────────────────── */

	const start = () => {
		injectCSS();

		// MutationObserver for async chart rendering
		const obs = new MutationObserver(() => {
			processChart();
		});
		obs.observe(document.body, { childList: true, subtree: true });

		// Also poll periodically
		let ticks = 0;
		const iv = setInterval(() => {
			processChart();
			if (++ticks > 30) clearInterval(iv);
		}, 2000);

		// Re-process on SPA page changes
		if (typeof frappe !== "undefined") {
			$(document).on("page-change", () => {
				setTimeout(() => {
					// Remove old marker
					const w = document.querySelector(`.widget[data-widget-name="${CHART_NAME}"]`);
					if (w) delete w.dataset[MARKER];
					document.querySelectorAll(".widget .widget-title .ellipsis").forEach(el => {
						if (el.textContent.trim() === CHART_NAME) {
							const ww = el.closest(".widget");
							if (ww) delete ww.dataset[MARKER];
						}
					});
					processChart();
				}, 2000);
			});
		}
	};

	// frappe.ready() only exists on website pages, not in desk.
	// Use DOMContentLoaded or run immediately if DOM is already loaded.
	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", start, { once: true });
	} else {
		// Small delay to let Frappe initialize
		setTimeout(start, 500);
	}
})();
