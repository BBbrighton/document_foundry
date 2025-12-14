# Copyright (c) 2025, X-Desk and contributors
# For license information, please see license.txt

import secrets
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class DocumentShare(Document):
	def before_insert(self):
		# Generate unique token
		self.share_token = secrets.token_urlsafe(32)

		# Set created_by
		self.created_by = frappe.session.user

	def after_insert(self):
		# Set the share URL after insert (once we have the token)
		self.db_set("share_url", self.get_share_url())

	def validate(self):
		self.validate_doctype_enabled()
		self.validate_access_type_allowed()
		self.validate_user_role()
		self.validate_password_required()

	def validate_doctype_enabled(self):
		"""Check if sharing is enabled for this DocType"""
		settings = frappe.get_single("Document Share Settings")
		enabled_doctypes = [row.document_type for row in settings.enabled_doctypes]

		if self.reference_doctype not in enabled_doctypes:
			frappe.throw(
				_("Sharing is not enabled for {0}").format(self.reference_doctype)
			)

	def validate_access_type_allowed(self):
		"""Check if the selected access type is allowed for this DocType"""
		settings = frappe.get_single("Document Share Settings")

		for row in settings.enabled_doctypes:
			if row.document_type == self.reference_doctype:
				if self.access_type == "Public" and not row.allow_public:
					frappe.throw(_("Public sharing is not allowed for {0}").format(self.reference_doctype))
				if self.access_type == "Password" and not row.allow_password:
					frappe.throw(_("Password-protected sharing is not allowed for {0}").format(self.reference_doctype))
				if self.access_type == "Login Required" and not row.allow_login:
					frappe.throw(_("Login-required sharing is not allowed for {0}").format(self.reference_doctype))
				break

	def validate_user_role(self):
		"""Check if user has permission to create share links"""
		settings = frappe.get_single("Document Share Settings")

		for row in settings.enabled_doctypes:
			if row.document_type == self.reference_doctype:
				allowed_roles = [r.role for r in row.allowed_roles]

				if allowed_roles:
					user_roles = frappe.get_roles(frappe.session.user)
					if not any(role in user_roles for role in allowed_roles):
						frappe.throw(
							_("You don't have permission to create share links for {0}").format(
								self.reference_doctype
							)
						)
				break

	def validate_password_required(self):
		"""Ensure password is provided for password-protected shares"""
		if self.access_type == "Password" and not self.password:
			frappe.throw(_("Password is required for password-protected shares"))

	def get_share_url(self):
		"""Get the full share URL"""
		return frappe.utils.get_url(f"/docshare/view?token={self.share_token}")

	def verify_password(self, password):
		"""Verify the provided password against stored password"""
		if self.access_type != "Password":
			return True
		return self.password == password

	def record_view(self):
		"""Record a view of the shared document"""
		frappe.db.set_value(
			"Document Share",
			self.name,
			{
				"view_count": self.view_count + 1,
				"last_viewed": now_datetime()
			},
			update_modified=False
		)

	def is_expired(self):
		"""Check if the share link has expired"""
		if not self.expires_at:
			return False
		return now_datetime() > self.expires_at

	def is_valid(self):
		"""Check if share link is valid (active and not expired)"""
		return self.is_active and not self.is_expired()
