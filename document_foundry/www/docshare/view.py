# Copyright (c) 2025, X-Desk and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime

no_cache = 1
allow_guest = True


def get_context(context):
	token = frappe.form_dict.get("token")

	if not token:
		context.error = _("No token provided")
		context.show_password_form = False
		return

	# Look up the share
	share = frappe.db.get_value(
		"Document Share",
		{"share_token": token},
		["name", "reference_doctype", "reference_name", "access_type",
		 "expires_at", "is_active", "print_format", "letterhead"],
		as_dict=True
	)

	if not share:
		context.error = _("Invalid share link")
		context.show_password_form = False
		return

	if not share.is_active:
		context.error = _("This share link has been revoked")
		context.show_password_form = False
		return

	if share.expires_at and now_datetime() > share.expires_at:
		context.error = _("This share link has expired")
		context.show_password_form = False
		return

	# Handle access type
	if share.access_type == "Login Required":
		if frappe.session.user == "Guest":
			frappe.local.flags.redirect_location = f"/login?redirect-to=/docshare/view?token={token}"
			raise frappe.Redirect

	if share.access_type == "Password":
		password = frappe.form_dict.get("password")
		if not password:
			context.show_password_form = True
			context.token = token
			return
		else:
			# Verify password
			doc = frappe.get_doc("Document Share", share.name)
			if not doc.verify_password(password):
				context.show_password_form = True
				context.token = token
				context.password_error = _("Incorrect password")
				return

	# Access granted - render document
	context.show_password_form = False
	context.error = None

	# Record view
	share_doc = frappe.get_doc("Document Share", share.name)
	share_doc.record_view()

	# Get document HTML - bypass permission checks since we validated the share token
	# Set flags to allow document access and print without permission checks
	frappe.flags.ignore_permissions = True
	frappe.flags.ignore_print_permissions = True
	try:
		# Use frappe.get_print which returns full HTML including Print/PDF toolbar
		context.document_html = frappe.get_print(
			share.reference_doctype,
			share.reference_name,
			print_format=share.print_format,
			letterhead=share.letterhead
		)
	finally:
		frappe.flags.ignore_permissions = False
		frappe.flags.ignore_print_permissions = False

	context.doctype = share.reference_doctype
	context.docname = share.reference_name
	context.token = token
	context.password = frappe.form_dict.get("password") or ""
	context.title = f"{share.reference_doctype}: {share.reference_name}"
