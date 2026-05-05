import os

from flask import Flask
from flask_login import current_user

from .extensions import db, login_manager, migrate
from .page_registry import PAGES


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object("config.Config")

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["AVATAR_UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from .models import Attribute, Integration, LlmModel, Permission, ReleaseNote, Role, User  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    from .routes.auth import auth_bp
    from .routes.help import help_bp
    from .routes.main import main_bp
    from .routes.models import models_bp
    from .routes.permissions import permissions_bp
    from .routes.users import users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(help_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(permissions_bp)
    app.register_blueprint(users_bp)

    @app.context_processor
    def inject_permissions():
        def has_access(page_slug: str, min_level: str = "view") -> bool:
            if not current_user.is_authenticated:
                return False
            if current_user.role == "admin":
                return True

            from .models import Permission, Role
            from .page_registry import ACCESS_LEVELS

            role = Role.query.filter_by(name=current_user.role).first()
            permission = (
                Permission.query.filter_by(role_id=role.id, page_slug=page_slug).first()
                if role else None
            )
            level = permission.access_level if permission else "no_access"
            return ACCESS_LEVELS.index(level) >= ACCESS_LEVELS.index(min_level)

        return {"has_access": has_access}

    with app.app_context():
        db.create_all()
        _seed_defaults()

    return app


def _seed_defaults() -> None:
    from .models import Attribute, Integration, Permission, Role, User

    admin_role = Role.query.filter_by(name="admin").first()
    if not admin_role:
        admin_role = Role(name="admin", is_system=True)
        db.session.add(admin_role)
        db.session.flush()
        for page in PAGES:
            db.session.add(Permission(role_id=admin_role.id, page_slug=page["slug"], access_level="edit"))

    member_role = Role.query.filter_by(name="member").first()
    if not member_role:
        member_role = Role(name="member", is_system=True)
        db.session.add(member_role)
        db.session.flush()
        for page in PAGES:
            level = "view" if page["slug"] in {"dashboard", "help"} else "no_access"
            db.session.add(Permission(role_id=member_role.id, page_slug=page["slug"], access_level=level))

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

    default_integrations = [
        ("openai", "LLM", "OpenAI", "Store an OpenAI API key and endpoint details."),
        ("anthropic", "LLM", "Anthropic", "Store an Anthropic API key for future prototypes."),
        ("slack", "Collaboration", "Slack", "Store a Slack bot token or app secret."),
    ]
    for name, category, provider, description in default_integrations:
        exists = Integration.query.filter_by(name=name).first()
        if not exists:
            db.session.add(
                Integration(
                    name=name,
                    category=category,
                    provider=provider,
                    description=description,
                )
            )

    db.session.commit()

