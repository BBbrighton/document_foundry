# Document Foundry - Project Guide

## Overview

Universal document sharing system for Frappe that allows users to generate shareable links for configured documents. Uses Frappe's existing Print Format system for rendering.

**Developer**: X-Desk (chotiputsilp.r@gmail.com)
**License**: MIT
**Version**: 1.0.0
**Repository**: https://github.com/BBbrighton/document_foundry

---

## Status: v1.0.0 Released

### Completed Features

- [x] **DocTypes**: All three DocTypes created and working
  - Document Share Settings (Single) - global configuration
  - Document Share DocType (Child) - per-DocType settings
  - Document Share - individual share link records
- [x] **Backend Logic**: Token generation, password verification, validation
- [x] **APIs**: All endpoints in `api/docshare.py` working
- [x] **Public View**: `/docshare/view?token=xxx` with professional X-DESK branding
- [x] **Access Modes**: Public, Password Protected, Login Required
- [x] **PDF Download**: Auto-download with Thai font support
- [x] **View Tracking**: Count and last viewed timestamp
- [x] **Share URL Field**: Full URL shown in Document Share form

### Pending (Phase 5: UI Integration)

- [ ] **Share Button on Forms**: Add dedicated "Share" button to enabled DocTypes for quick access to create share links (similar to QR Foundry pattern)
- [ ] **Custom JS**: `doctype_js` hook to inject share button into document forms
- [ ] **Share Dialog**: Modal dialog to configure and create share links directly from document view

---

## Installation

```bash
bench get-app https://github.com/BBbrighton/document_foundry
bench --site <site-name> install-app document_foundry
bench --site <site-name> migrate
```

---

## Configuration

1. Go to **Document Share Settings**
2. Add DocTypes to enable sharing for
3. Configure per-DocType:
   - Default expiry days
   - Allowed roles
   - Default print format
   - Allowed access types (Public/Password/Login)

---

## Usage

1. Create a **Document Share** record manually, or (future) use the Share button
2. Select reference DocType and document
3. Choose access type and set password if needed
4. Copy the **Share URL** and send to recipient

---

## File Structure

```
document_foundry/
├── document_foundry/
│   ├── __init__.py              # Version 1.0.0
│   ├── hooks.py                 # App hooks
│   ├── install.py               # Post-install Thai font setup
│   ├── document_foundry/
│   │   ├── api/
│   │   │   └── docshare.py      # API endpoints
│   │   └── doctype/
│   │       ├── document_share/
│   │       ├── document_share_doctype/
│   │       └── document_share_settings/
│   ├── public/
│   │   └── fonts/
│   │       └── NotoSansThai-Regular.ttf
│   └── www/
│       └── docshare/
│           ├── view.html        # Public share view page
│           └── view.py
└── pyproject.toml
```

---

## API Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `get_share_settings(doctype)` | User | Get share settings for a DocType |
| `create_share(...)` | User | Create a new share link |
| `get_share_links(doctype, docname)` | User | Get all shares for a document |
| `revoke_share(share_name)` | User | Deactivate a share link |
| `verify_access(token, password)` | Guest | Verify access to shared document |
| `get_document_html(token, password)` | Guest | Get rendered HTML |
| `get_document_pdf(token, password)` | Guest | Download PDF |

---

## Next Steps (v1.1.0)

To add the Share button to enabled DocTypes (like QR Foundry):

1. Create `public/js/document_share.js` with button injection logic
2. Add to `hooks.py`:
   ```python
   doctype_js = {
       # Dynamically populated based on Document Share Settings
   }
   ```
3. Or use `app_include_js` with dynamic checking of enabled DocTypes
4. Create Share dialog modal for quick link creation

---

## Common Commands

```bash
# Build assets
bench build --app document_foundry

# Migrate after DocType changes
bench --site metal migrate

# Clear cache
bench --site metal clear-cache

# Check version
bench version
```
