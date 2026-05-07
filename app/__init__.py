import os

import markdown as md_lib
from flask import Flask
from flask_login import current_user

from .access import user_has_access
from .extensions import db, login_manager, migrate
from .page_registry import PAGES


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object("config.Config")

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["AVATAR_UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["AGENT_AVATAR_UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from .models import (AiAgent, AgentConversation, AgentMessage,  # noqa: F401
                          Attribute, Integration, LlmModel,
                          LlmRequestLog, UserActivityLog, ApiRequestLog,
                          Permission, ReleaseNote, Role, User)

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    from .routes.agents import agents_bp
    from .routes.auth import auth_bp
    from .routes.help import help_bp
    from .routes.main import main_bp
    from .routes.models import models_bp
    from .routes.permissions import permissions_bp
    from .routes.reporting import reporting_bp
    from .routes.users import users_bp

    app.register_blueprint(agents_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(help_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(permissions_bp)
    app.register_blueprint(reporting_bp)
    app.register_blueprint(users_bp)

    @app.template_filter("md")
    def render_markdown(text: str) -> str:
        return md_lib.markdown(text or "", extensions=["tables", "fenced_code"])

    @app.context_processor
    def inject_permissions():
        return {"has_access": user_has_access}

    with app.app_context():
        _seed_defaults()

    return app


def _seed_defaults() -> None:
    from sqlalchemy import inspect as sa_inspect

    from .models import Attribute, Integration, Permission, Role, User

    # Guard: skip seeding if schema hasn't been created or migrated yet.
    # This prevents errors when the DB is stale (missing columns) or doesn't exist.
    # After `flask db upgrade`, the schema is up to date and seeding runs on next startup.
    inspector = sa_inspect(db.engine)
    if not inspector.has_table("user"):
        return
    existing_cols = {c["name"] for c in inspector.get_columns("user")}
    if "updated_at" not in existing_cols:
        return  # Schema is out of date — run `flask db upgrade` first
    if inspector.has_table("integration"):
        integration_cols = {c["name"] for c in inspector.get_columns("integration")}
        if "use_case" not in integration_cols:
            return  # Schema is out of date — run `flask db upgrade` first

    admin_role = Role.query.filter_by(name="admin").first()
    if not admin_role:
        admin_role = Role(name="admin", is_system=True)
        db.session.add(admin_role)
        db.session.flush()
        for page in PAGES:
            db.session.add(Permission(role_id=admin_role.id, page_slug=page["slug"], access_level="edit"))
    elif not admin_role.is_system:
        admin_role.is_system = True

    member_role = Role.query.filter_by(name="member").first()
    if not member_role:
        member_role = Role(name="member", is_system=False)
        db.session.add(member_role)
        db.session.flush()
        for page in PAGES:
            level = "view" if page["slug"] in {"dashboard", "help"} else "no_access"
            db.session.add(Permission(role_id=member_role.id, page_slug=page["slug"], access_level=level))
    elif member_role.is_system:
        member_role.is_system = False

    for role in Role.query.all():
        role.is_system = role.name.lower() == "admin"

    for role in Role.query.all():
        for page in PAGES:
            exists = Permission.query.filter_by(role_id=role.id, page_slug=page["slug"]).first()
            if not exists:
                default_level = "edit" if role.name == "admin" else "no_access"
                db.session.add(Permission(role_id=role.id, page_slug=page["slug"], access_level=default_level))

    admin_user = User.query.filter_by(username="admin").first()
    if not admin_user:
        admin_user = User(
            username="admin",
            email="admin@example.com",
            role="admin",
            first_name="System",
            last_name="Administrator",
            must_change_password=True,
        )
        admin_user.set_password("Changeme-123")
        db.session.add(admin_user)

    default_attributes = [
        ("Customer", "SMB", "Small and mid-sized business"),
        ("Customer", "Enterprise", "Larger strategic account"),
        ("Workflow", "Pilot", "Early prototype or validation workflow"),
    ]
    for category, name, description in default_attributes:
        exists = Attribute.query.filter_by(category=category, name=name).first()
        if not exists:
            db.session.add(Attribute(category=category, name=name, description=description))

    db.session.commit()
