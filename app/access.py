from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user

from .page_registry import ACCESS_LEVELS


def permission_required(page_slug: str, min_level: str = "view"):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role == "admin":
                return view_func(*args, **kwargs)

            from .models import Permission, Role

            role = Role.query.filter_by(name=current_user.role).first()
            permission = (
                Permission.query.filter_by(role_id=role.id, page_slug=page_slug).first()
                if role else None
            )
            level = permission.access_level if permission else "no_access"
            if ACCESS_LEVELS.index(level) < ACCESS_LEVELS.index(min_level):
                flash("You do not have permission to access this page.", "error")
                return redirect(url_for("main.dashboard"))
            return view_func(*args, **kwargs)

        return wrapped

    return decorator

