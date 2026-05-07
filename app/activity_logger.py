"""Lightweight helper for writing UserActivityLog rows.

Usage:
    from .activity_logger import log_activity
    log_activity(user=current_user, action="user.login", page="System")

The `page` parameter is a human-readable label shown in Reporting.
Keep action strings in the format  "resource.verb"  (e.g. "user.login").
"""
from flask import request as _flask_request

# Map action strings to a display label for the Reporting UI
ACTION_LABELS: dict[str, str] = {
    "user.login":    "Logged In",
    "user.logout":   "Logged Out",
    "user.created":  "Created User",
    "user.updated":  "Updated User",
    "user.deleted":  "Deleted User",
    "user.password_changed": "Changed Password",
}


def log_activity(user, action: str, page: str | None = None) -> None:
    """Append one UserActivityLog row. Safe to call inside a request context.

    Args:
        user:   A User model instance (or None for anonymous).
        action: Dot-namespaced action string, e.g. "user.login".
        page:   Optional human-readable page / section name.
    """
    try:
        from .extensions import db
        from .models import UserActivityLog

        ip = None
        try:
            ip = _flask_request.remote_addr
        except RuntimeError:
            pass  # outside request context

        log = UserActivityLog(
            user_id=user.id if user else None,
            action=action,
            page=page,
            ip_address=ip,
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        # Never let logging failures crash the main request
        pass
