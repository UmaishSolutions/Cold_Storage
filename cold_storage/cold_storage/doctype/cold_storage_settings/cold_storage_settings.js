const DEFAULT_BODY_PARAMS = JSON.stringify(
	["{{ voucher_no }}", "{{ customer }}", "{{ posting_date }}", "{{ total_qty }}"],
	null,
	2
);

const DEFAULT_INWARD_TEXT_TEMPLATE = [
	"Cold Storage Inward submitted",
	"Company: {{ company }}",
	"Voucher: {{ voucher_no }}",
	"Customer: {{ customer }}",
	"Posting Date: {{ posting_date }}",
	"Total Qty: {{ total_qty }}",
].join("\n");

const DEFAULT_OUTWARD_TEXT_TEMPLATE = [
	"Cold Storage Outward submitted",
	"Company: {{ company }}",
	"Voucher: {{ voucher_no }}",
	"Customer: {{ customer }}",
	"Posting Date: {{ posting_date }}",
	"Total Qty: {{ total_qty }}",
].join("\n");

frappe.ui.form.on("Cold Storage Settings", {
	refresh(frm) {
		render_whatsapp_intro(frm);
		add_whatsapp_buttons(frm);
		style_urdu_text_inputs(frm);
	},

	onload_post_render(frm) {
		style_urdu_text_inputs(frm);
	},

	validate(frm) {
		const inwardValid = format_template_params_json(
			frm,
			"whatsapp_inward_template_body_params",
			__("Inward Template Body Params (JSON)")
		);
		const outwardValid = format_template_params_json(
			frm,
			"whatsapp_outward_template_body_params",
			__("Outward Template Body Params (JSON)")
		);
		if (!inwardValid || !outwardValid) {
			frappe.validated = false;
		}
	},
});

function add_whatsapp_buttons(frm) {
	frm.clear_custom_buttons();
	frm.add_custom_button(__("Check Setup"), () => check_whatsapp_setup(frm));
	frm.change_custom_button_type(__("Check Setup"), null, "primary");

	frm.add_custom_button(
		__("Fill Recommended Templates"),
		() => fill_recommended_templates(frm),
		__("WhatsApp")
	);

	frm.add_custom_button(
		__("Format Body Params JSON"),
		() => format_all_template_params_json(frm),
		__("WhatsApp")
	);

	frm.add_custom_button(__("Send WhatsApp Test"), () => send_whatsapp_test(frm), __("WhatsApp"));
}

function render_whatsapp_intro(frm) {
	if (!frm.doc.whatsapp_enabled) {
		frm.set_intro(
			__(
				"Enable WhatsApp Integration, add Meta credentials, then use Check Setup to validate before sending."
			),
			"orange"
		);
		return;
	}

	frm.set_intro(
		__(
			"Use Check Setup to verify credentials and template JSON. Use Send WhatsApp Test to confirm delivery."
		),
		"green"
	);
}

function style_urdu_text_inputs(frm) {
	apply_urdu_textarea_style(frm, "storage_terms_and_conditions", "شرائط و ضوابط اردو میں درج کریں");
	apply_urdu_textarea_style(frm, "portal_announcement", "پورٹل بینر اعلان اردو میں درج کریں");
}

function apply_urdu_textarea_style(frm, fieldname, placeholderText) {
	const field = frm.get_field(fieldname);
	if (!field || !field.$wrapper) {
		return;
	}

	const $textarea = field.$wrapper.find("textarea");
	if (!$textarea.length) {
		return;
	}

	$textarea
		.attr("dir", "rtl")
		.attr("lang", "ur")
		.attr("placeholder", placeholderText)
		.css({
			"text-align": "right",
			"font-family":
				'"Jameel Noori Nastaleeq", "Noori Nastaliq", "Noto Nastaliq Urdu", "Noto Naskh Arabic", serif',
			"font-size": "16px",
			"line-height": "1.6",
		});
}

function fill_recommended_templates(frm) {
	const templateFields = [
		"whatsapp_inward_text_template",
		"whatsapp_outward_text_template",
		"whatsapp_inward_template_body_params",
		"whatsapp_outward_template_body_params",
	];

	const hasExistingTemplates = templateFields.some((fieldname) =>
		((frm.doc[fieldname] || "") + "").trim()
	);

	const applyDefaults = () => {
		frm.set_value({
			whatsapp_inward_text_template: DEFAULT_INWARD_TEXT_TEMPLATE,
			whatsapp_outward_text_template: DEFAULT_OUTWARD_TEXT_TEMPLATE,
			whatsapp_inward_template_body_params: DEFAULT_BODY_PARAMS,
			whatsapp_outward_template_body_params: DEFAULT_BODY_PARAMS,
		});
		frappe.show_alert({
			message: __("Recommended WhatsApp templates applied"),
			indicator: "green",
		});
	};

	if (!hasExistingTemplates) {
		applyDefaults();
		return;
	}

	frappe.confirm(
		__("This will replace current WhatsApp templates and body params. Continue?"),
		applyDefaults
	);
}

function format_all_template_params_json(frm) {
	const inwardValid = format_template_params_json(
		frm,
		"whatsapp_inward_template_body_params",
		__("Inward Template Body Params (JSON)")
	);
	const outwardValid = format_template_params_json(
		frm,
		"whatsapp_outward_template_body_params",
		__("Outward Template Body Params (JSON)")
	);
	if (inwardValid && outwardValid) {
		frappe.show_alert({
			message: __("Template body params JSON formatted"),
			indicator: "green",
		});
	}
}

function format_template_params_json(frm, fieldname, label) {
	const raw = ((frm.doc[fieldname] || "") + "").trim();
	if (!raw) {
		return true;
	}

	try {
		const parsed = JSON.parse(raw);
		if (!Array.isArray(parsed)) {
			throw new Error(__("must be a JSON array of strings"));
		}
		frm.set_value(fieldname, JSON.stringify(parsed, null, 2));
		return true;
	} catch (error) {
		frappe.msgprint({
			title: __("Invalid JSON"),
			indicator: "red",
			message: __("{0}: {1}", [label, error.message || __("Invalid JSON")]),
		});
		return false;
	}
}

function check_whatsapp_setup(frm) {
	if (!ensure_saved_before_whatsapp_action(frm)) {
		return;
	}

	frappe.call({
		method: "cold_storage.cold_storage.integrations.whatsapp.get_whatsapp_setup_status",
		freeze: true,
		freeze_message: __("Checking WhatsApp setup..."),
		callback: (r) => {
			const status = r.message || {};
			const missingFields = status.missing_fields || [];
			const warnings = status.warnings || [];
			const endpoint = status.endpoint || "";

			const toList = (entries) =>
				entries.map((entry) => `<li>${frappe.utils.escape_html(entry)}</li>`).join("");

			const parts = [];
			if (missingFields.length) {
				parts.push(`<p><b>${__("Missing Required Fields")}:</b></p><ul>${toList(missingFields)}</ul>`);
			}
			if (warnings.length) {
				parts.push(`<p><b>${__("Warnings")}:</b></p><ul>${toList(warnings)}</ul>`);
			}
			if (endpoint) {
				parts.push(
					`<p><b>${__("Meta Endpoint")}:</b><br><code>${frappe.utils.escape_html(endpoint)}</code></p>`
				);
			}
			if (!parts.length) {
				parts.push(`<p>${__("Setup looks good.")}</p>`);
			}

			frappe.msgprint({
				title: status.ready ? __("WhatsApp Setup Ready") : __("WhatsApp Setup Needs Attention"),
				indicator: status.ready ? "green" : "orange",
				message: parts.join(""),
			});
		},
	});
}

function send_whatsapp_test(frm) {
	if (!ensure_saved_before_whatsapp_action(frm)) {
		return;
	}

	if (!frm.doc.whatsapp_enabled) {
		frappe.msgprint({
			title: __("WhatsApp Disabled"),
			message: __("Enable WhatsApp Integration before sending a test message."),
			indicator: "orange",
		});
		return;
	}

	const countryCode = ((frm.doc.whatsapp_default_country_code || "") + "").replace(/\D/g, "");
	const suggestedNumber = countryCode ? `+${countryCode}` : "";

	frappe.prompt(
		[
			{
				fieldtype: "Data",
				fieldname: "to_number",
				label: __("To Number"),
				reqd: 1,
				default: suggestedNumber,
				description: __("Provide customer WhatsApp number. Example: +923001234567"),
			},
			{
				fieldtype: "Small Text",
				fieldname: "message",
				label: __("Message"),
				description: __("Optional. Leave blank to use default test message."),
			},
		],
		(values) => {
			frappe.call({
				method: "cold_storage.cold_storage.integrations.whatsapp.send_whatsapp_test_message",
				args: {
					to_number: values.to_number,
					message: values.message,
				},
				freeze: true,
				freeze_message: __("Sending WhatsApp test message..."),
				callback: (r) => {
					const response = r.message || {};
					const toNumber = frappe.utils.escape_html(response.to_number || values.to_number || "");
					const messageId = frappe.utils.escape_html(response.message_id || __("N/A"));
					frappe.msgprint({
						title: __("WhatsApp Message Sent"),
						indicator: "green",
						message: __(
							"Delivered to <b>{0}</b><br>Message ID: <code>{1}</code>",
							[toNumber, messageId]
						),
					});
				},
			});
		},
		__("Send WhatsApp Test"),
		__("Send")
	);
}

function ensure_saved_before_whatsapp_action(frm) {
	if (!frm.is_dirty()) {
		return true;
	}

	frappe.msgprint({
		title: __("Save Required"),
		indicator: "orange",
		message: __("Save Cold Storage Settings before running WhatsApp checks or sending test messages."),
	});
	return false;
}
