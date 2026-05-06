# Changelog

## [2026-05-06] - Initial cleanup — align with skunkBOX principles

- Removed unauthenticated `/bootstrap/reset-admin` endpoint (security hole)
- Fixed deprecated SQLAlchemy patterns: `Model.query.get()` → `db.session.get()`, `get_or_404()` → `db.get_or_404()`
- Added `is_admin()` method to User model — use instead of `role == "admin"` string comparison
- Added `updated_at` column to User, Role, and LlmModel models
- Added `last_login` column to User model; populated on successful login
- Initialized Flask-Migrate; created initial schema migration (`db2364c230d4`)
- Removed `db.create_all()` from app factory — schema now managed via migrations
- Added schema guard to `_seed_defaults()` so it skips gracefully before `flask db upgrade` is run
- Extracted shared permission helper `user_has_access()` to `app/access.py` — eliminates duplicate logic in models route and `__init__.py` context processor
- Passed `PAGES` from routes to templates — no more hardcoded page lists in Jinja
- Added `.local-time` UTC→local timestamp conversion pattern to all templates (matches skunkBOX convention)
- Added UTC→local JS handler to `app.js`
- Created `CLAUDE.md` with project conventions aligned with skunkBOX
- Fixed `DESIGN_SYSTEM.md` — CSS variable names now match the actual `style.css`
