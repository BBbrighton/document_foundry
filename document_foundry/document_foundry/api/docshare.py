# Copyright (c) 2025, X-Desk and contributors
# For license information, please see license.txt

import base64
import os

import frappe
from frappe import _
from frappe.utils import now_datetime, add_days


@frappe.whitelist()
def get_share_settings(doctype):
	"""Get share settings for a DocType (if enabled and user has role)

	Args:
		doctype: The DocType to check

	Returns:
		dict: Settings for the DocType or None if not enabled/permitted
	"""
	settings = frappe.get_single("Document Share Settings")

	for row in settings.enabled_doctypes:
		if row.document_type == doctype:
			# Check if user has allowed role
			allowed_roles = [r.role for r in row.allowed_roles]
			if allowed_roles:
				user_roles = frappe.get_roles(frappe.session.user)
				if not any(role in user_roles for role in allowed_roles):
					return None

			return {
				"enabled": True,
				"default_expiry_days": row.default_expiry_days,
				"default_print_format": row.default_print_format,
				"allow_public": row.allow_public,
				"allow_password": row.allow_password,
				"allow_login": row.allow_login,
			}

	return None


@frappe.whitelist()
def create_share(doctype, docname, access_type, print_format=None, letterhead=None, password=None, expires_days=None):
	"""Create a share link for a document

	Args:
		doctype: Reference DocType
		docname: Reference document name
		access_type: Public / Password / Login Required
		print_format: Print format to use (optional)
		letterhead: Letterhead to use (optional)
		password: Password for password-protected shares
		expires_days: Number of days until expiry (optional)

	Returns:
		dict: Share link details including URL and token
	"""
	# Calculate expiry date
	expires_at = None
	if expires_days and int(expires_days) > 0:
		expires_at = add_days(now_datetime(), int(expires_days))

	# Get default print format if not specified
	if not print_format:
		settings = frappe.get_single("Document Share Settings")
		for row in settings.enabled_doctypes:
			if row.document_type == doctype:
				print_format = row.default_print_format
				break

	doc = frappe.get_doc({
		"doctype": "Document Share",
		"reference_doctype": doctype,
		"reference_name": docname,
		"access_type": access_type,
		"password": password,
		"print_format": print_format,
		"letterhead": letterhead,
		"expires_at": expires_at,
		"is_active": 1
	})
	doc.insert()

	return {
		"name": doc.name,
		"token": doc.share_token,
		"url": doc.get_share_url(),
		"access_type": doc.access_type,
		"expires_at": doc.expires_at
	}


@frappe.whitelist()
def get_share_links(doctype, docname):
	"""Get all active share links for a document

	Args:
		doctype: Reference DocType
		docname: Reference document name

	Returns:
		list: List of share link details
	"""
	shares = frappe.get_all(
		"Document Share",
		filters={
			"reference_doctype": doctype,
			"reference_name": docname,
			"is_active": 1
		},
		fields=[
			"name", "share_token", "access_type", "print_format",
			"expires_at", "view_count", "last_viewed", "created_by", "creation"
		],
		order_by="creation desc"
	)

	for share in shares:
		share["url"] = frappe.utils.get_url(f"/docshare/view?token={share['share_token']}")
		share["is_expired"] = share["expires_at"] and now_datetime() > share["expires_at"]

	return shares


@frappe.whitelist()
def revoke_share(share_name):
	"""Deactivate a share link

	Args:
		share_name: Name of the Document Share record

	Returns:
		dict: Success status
	"""
	doc = frappe.get_doc("Document Share", share_name)

	# Check permission - user must own the share or be System Manager
	if doc.created_by != frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(_("You don't have permission to revoke this share link"))

	doc.is_active = 0
	doc.save()

	return {"success": True}


@frappe.whitelist(allow_guest=True)
def verify_access(token, password=None):
	"""Verify access to shared document

	Args:
		token: Share token
		password: Password for password-protected shares

	Returns:
		dict: Access status and document info
	"""
	share = frappe.db.get_value(
		"Document Share",
		{"share_token": token},
		["name", "reference_doctype", "reference_name", "access_type",
		 "password", "expires_at", "is_active", "print_format", "letterhead"],
		as_dict=True
	)

	if not share:
		return {"success": False, "error": "invalid_token", "message": _("Invalid share link")}

	if not share.is_active:
		return {"success": False, "error": "revoked", "message": _("This share link has been revoked")}

	if share.expires_at and now_datetime() > share.expires_at:
		return {"success": False, "error": "expired", "message": _("This share link has expired")}

	# Check access type
	if share.access_type == "Login Required":
		if frappe.session.user == "Guest":
			return {
				"success": False,
				"error": "login_required",
				"message": _("Please log in to view this document"),
				"redirect": f"/login?redirect-to=/docshare/view?token={token}"
			}

	if share.access_type == "Password":
		if not password:
			return {
				"success": False,
				"error": "password_required",
				"message": _("Password required")
			}
		# Verify password
		doc = frappe.get_doc("Document Share", share.name)
		if not doc.verify_password(password):
			return {"success": False, "error": "wrong_password", "message": _("Incorrect password")}

	return {
		"success": True,
		"doctype": share.reference_doctype,
		"docname": share.reference_name,
		"print_format": share.print_format,
		"letterhead": share.letterhead
	}


@frappe.whitelist(allow_guest=True)
def get_document_html(token, password=None):
	"""Get rendered document HTML for display

	Args:
		token: Share token
		password: Password for password-protected shares

	Returns:
		dict: Document HTML or error
	"""
	access = verify_access(token, password)

	if not access.get("success"):
		return access

	# Record the view
	share = frappe.get_doc("Document Share", {"share_token": token})
	share.record_view()

	# Get the rendered HTML
	html = frappe.get_print(
		access["doctype"],
		access["docname"],
		print_format=access.get("print_format"),
		letterhead=access.get("letterhead")
	)

	return {
		"success": True,
		"html": html,
		"doctype": access["doctype"],
		"docname": access["docname"]
	}


@frappe.whitelist(allow_guest=True)
def get_document_pdf(token, password=None):
	"""Get document as PDF download

	Args:
		token: Share token
		password: Password for password-protected shares

	Returns:
		PDF file response or error dict
	"""
	from frappe.utils.pdf import get_pdf

	access = verify_access(token, password)

	if not access.get("success"):
		frappe.throw(access.get("message") or "Access denied")

	# Record the view
	share = frappe.get_doc("Document Share", {"share_token": token})
	share.record_view()

	# Get HTML first
	html = frappe.get_print(
		access["doctype"],
		access["docname"],
		print_format=access.get("print_format"),
		letterhead=access.get("letterhead")
	)

	# Add Thai font embedded as base64 for PDF rendering
	# This ensures Thai text renders correctly without requiring system font installation
	thai_font_css = get_thai_font_css()

	# Inject Thai font CSS into HTML
	if '<head>' in html:
		html = html.replace('<head>', f'<head>{thai_font_css}')
	elif '<html>' in html:
		html = html.replace('<html>', f'<html><head>{thai_font_css}</head>')
	else:
		html = thai_font_css + html

	# Convert to PDF
	pdf_options = {
		"encoding": "UTF-8",
	}
	pdf = get_pdf(html, options=pdf_options)

	# Set response for auto-download (not inline viewing)
	frappe.local.response.filename = f"{access['docname']}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "download"


def get_thai_font_css():
	"""Get CSS with embedded Thai font (Noto Sans Thai) as base64 for PDF rendering"""
	# Path to the bundled font file
	font_path = os.path.join(
		frappe.get_app_path("document_foundry"),
		"public", "fonts", "NotoSansThai-Regular.ttf"
	)

	# Check if font file exists
	if not os.path.exists(font_path):
		# Fallback to system fonts if bundled font not found
		return """
		<style>
			* {
				font-family: 'Noto Sans Thai', 'Sarabun', 'TH Sarabun New', 'Garuda', sans-serif !important;
			}
		</style>
		"""

	# Read and encode font as base64
	with open(font_path, "rb") as f:
		font_data = base64.b64encode(f.read()).decode("utf-8")

	# Return CSS with embedded font
	return f"""
	<style>
		@font-face {{
			font-family: 'Noto Sans Thai';
			src: url(data:font/truetype;base64,{font_data}) format('truetype');
			font-weight: normal;
			font-style: normal;
		}}
		* {{
			font-family: 'Noto Sans Thai', sans-serif !important;
		}}
		body, p, span, div, td, th, table {{
			font-family: 'Noto Sans Thai', sans-serif !important;
		}}
	</style>
	"""
