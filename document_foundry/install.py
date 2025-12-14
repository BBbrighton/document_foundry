# Copyright (c) 2025, X-Desk and contributors
# For license information, please see license.txt

import os
import shutil
import subprocess

import frappe


def after_install():
	"""Install Thai fonts for PDF generation after app installation"""
	install_thai_fonts()


def install_thai_fonts():
	"""Copy bundled Thai fonts to user's local fonts directory for wkhtmltopdf"""
	try:
		# Source font path (bundled with app)
		app_path = frappe.get_app_path("document_foundry")
		font_src = os.path.join(app_path, "public", "fonts", "NotoSansThai-Regular.ttf")

		if not os.path.exists(font_src):
			frappe.log_error("Thai font file not found in app bundle", "Font Installation")
			return

		# Destination: user's local fonts directory
		home_dir = os.path.expanduser("~")
		fonts_dir = os.path.join(home_dir, ".local", "share", "fonts")

		# Create fonts directory if it doesn't exist
		os.makedirs(fonts_dir, exist_ok=True)

		# Copy font file
		font_dest = os.path.join(fonts_dir, "NotoSansThai-Regular.ttf")
		shutil.copy2(font_src, font_dest)

		# Refresh font cache
		try:
			subprocess.run(["fc-cache", "-f", fonts_dir], check=True, capture_output=True)
			print(f"✓ Thai font installed successfully to {fonts_dir}")
		except subprocess.CalledProcessError:
			print(f"✓ Thai font copied to {fonts_dir} (font cache refresh skipped)")
		except FileNotFoundError:
			print(f"✓ Thai font copied to {fonts_dir} (fc-cache not available)")

	except Exception as e:
		# Don't fail installation if font copy fails
		frappe.log_error(f"Failed to install Thai fonts: {str(e)}", "Font Installation")
		print(f"⚠ Could not install Thai fonts: {str(e)}")
