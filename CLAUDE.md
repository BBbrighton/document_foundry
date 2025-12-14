# Document Foundry - Project Guide

## Overview

Universal document sharing system for Frappe that allows users to generate shareable links for configured documents. Uses Frappe's existing Print Format system for rendering.

**Developer**: X-Desk (chotiputsilp.r@gmail.com)
**License**: MIT

---

## Session Summary (Dec 14, 2025)

### What Was Done

1. **App Created**: `document_foundry` app scaffolded and installed on `metal` site
2. **Issues Resolved**:
   - Removed stale `tub_suite` references from `apps.txt` that were blocking builds
   - Multiple attempts needed due to `bench new-app` failing mid-way on `bench build`
   - Final fix: Removed tub_suite entirely, recreated app, manually ran pip install and build

### Installation Commands Used
```bash
# Remove stale apps
rm -rf apps/tub_suite
sed -i '/^tub_suite$/d' sites/apps.txt

# Create new app
bench new-app document_foundry

# Manual fix when build failed
./env/bin/pip install -e apps/document_foundry
bench build --app document_foundry
bench --site metal install-app document_foundry
bench migrate
```

### Current State
- App installed on `metal` site
- Basic scaffold only - no DocTypes or features yet
- Ready for implementation

---

## Design Specification

### Key Features

- **Configurable DocTypes** - Settings page to enable/disable per DocType (like QR Foundry pattern)
- **Role-based permissions** - Only users with allowed roles can create share links
- **Configurable link duration** - Default expiry settings per DocType
- **Three access modes**: Public / Password Protected / Login Required
- **Uses existing Print Formats** for rendering
- **View tracking** - Count views, last viewed timestamp

### Architecture

```
Document Share Settings (Single)
        |
        v
Document Share DocType (Child Table - per DocType config)
        |
        v
Document Share (Individual share links)
        |
        v
/share/view?token=xxx (Public view page)
```

---

## DocTypes to Create

### 1. Document Share Settings (Single)

Global configuration.

| Field | Type | Description |
|-------|------|-------------|
| `enabled_doctypes` | Table | Child table of Document Share DocType |

### 2. Document Share DocType (Child Table)

Per-DocType configuration.

| Field | Type | Description |
|-------|------|-------------|
| `document_type` | Link: DocType | The DocType to enable |
| `default_expiry_days` | Int | Default link expiry (0 = never) |
| `allowed_roles` | Table MultiSelect | Roles that can create shares |
| `default_print_format` | Link: Print Format | Default format |
| `allow_public` | Check | Allow public shares |
| `allow_password` | Check | Allow password-protected shares |
| `allow_login` | Check | Allow login-required shares |

### 3. Document Share

Individual share link record.

| Field | Type | Description |
|-------|------|-------------|
| `reference_doctype` | Link: DocType | DocType being shared |
| `reference_name` | Dynamic Link | Specific document |
| `share_token` | Data | Unique URL token (auto-generated) |
| `access_type` | Select | Public / Password / Login Required |
| `password` | Password | Hashed password (if applicable) |
| `print_format` | Link: Print Format | Which format to use |
| `letterhead` | Link: Letter Head | Optional letterhead |
| `expires_at` | Datetime | Expiration |
| `is_active` | Check | Enable/disable |
| `view_count` | Int | Times viewed |
| `last_viewed` | Datetime | Last view timestamp |
| `created_by` | Link: User | Who created |

---

## API Endpoints (`api/share.py`)

```python
@frappe.whitelist()
def get_share_settings(doctype):
    """Get share settings for a DocType (if enabled, user has role)"""

@frappe.whitelist()
def create_share(doctype, docname, access_type, print_format=None,
                 password=None, expires_days=None):
    """Create a share link for a document"""

@frappe.whitelist()
def get_share_links(doctype, docname):
    """Get all active share links for a document"""

@frappe.whitelist()
def revoke_share(share_name):
    """Deactivate a share link"""

@frappe.whitelist(allow_guest=True)
def verify_access(token, password=None):
    """Verify access to shared document"""

@frappe.whitelist(allow_guest=True)
def get_document_html(token, password=None):
    """Get rendered document HTML for display"""

@frappe.whitelist(allow_guest=True)
def get_document_pdf(token, password=None):
    """Get document as PDF download"""
```

---

## File Structure (Target)

```
document_foundry/
├── document_foundry/
│   ├── doctype/
│   │   ├── document_share_settings/
│   │   │   ├── document_share_settings.json
│   │   │   └── document_share_settings.py
│   │   ├── document_share_doctype/
│   │   │   └── document_share_doctype.json
│   │   └── document_share/
│   │       ├── document_share.json
│   │       └── document_share.py
│   ├── api/
│   │   └── share.py
│   └── www/
│       └── share/
│           ├── view.html
│           └── view.py
├── public/
│   └── css/
│       └── document_share.css
└── hooks.py
```

---

## Security

1. **Token**: 32-byte URL-safe random token (`secrets.token_urlsafe(32)`)
2. **Password**: Hashed with `werkzeug.security.generate_password_hash`
3. **Role Check**: User must have allowed role to create shares
4. **Access Type Control**: Admin controls which access types are allowed per DocType
5. **Expiration**: Configurable default, checked on every access
6. **Audit**: Track creator, views, last accessed
7. **Revocation**: Instant deactivation via `is_active` flag

---

## Public View Flow (`/share/view?token=xxx`)

1. Extract token from URL
2. Look up Document Share record
3. Validate: exists, is_active, not expired
4. Check access:
   - **Public**: Render immediately
   - **Password**: Show password form → verify → render
   - **Login**: Redirect to `/login?redirect-to=/share/view?token=xxx`
5. Render document using `frappe.get_print()`
6. Increment view count

---

## Example Configuration

| DocType | Default Expiry | Allowed Roles | Access Types |
|---------|----------------|---------------|--------------|
| Sales Invoice | 30 days | Sales Manager | Public, Password, Login |
| POS Order | Never | POS Operator | Public, Password |
| Scrap Weight | 30 days | POS Operator | Public |

---

## Implementation Phases

### Phase 1: DocTypes
- [ ] Create Document Share Settings (Single)
- [ ] Create Document Share DocType (Child)
- [ ] Create Document Share (Main)

### Phase 2: Backend Logic
- [ ] Token generation in document_share.py
- [ ] Password hashing
- [ ] Validation against settings

### Phase 3: APIs
- [ ] Create api/share.py
- [ ] Guest endpoints for viewing

### Phase 4: Public View
- [ ] Create www/share/view.html
- [ ] Password form handling
- [ ] PDF download option

### Phase 5: Integration
- [ ] Add Share button to enabled DocTypes
- [ ] Update hooks.py

---

## Common Commands

```bash
# Build assets
bench build --app document_foundry

# Migrate after DocType changes
bench --site metal migrate

# Clear cache
bench --site metal clear-cache

# Export fixtures
bench --site metal export-fixtures --app document_foundry
```

---

## Notes

- Document state (cancelled, revised, etc.) is handled by source document
- Print formats already handle field visibility
- Multiple shares can exist for same document (different access types)
- Mirrors QR Foundry pattern for settings/configuration
