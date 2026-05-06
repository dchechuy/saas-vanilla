from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    role = db.Column(db.String(80), nullable=False, default="member")
    avatar = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    must_change_password = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    @property
    def display_name(self) -> str:
        full_name = " ".join(part for part in [self.first_name, self.last_name] if part)
        return full_name or self.username

    def is_admin(self) -> bool:
        return self.role == "admin"

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Role(db.Model):
    __tablename__ = "role"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    is_system = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    permissions = db.relationship("Permission", backref="role", cascade="all, delete-orphan")

    @property
    def is_protected(self) -> bool:
        return self.name.lower() == "admin"

    def get_permission(self, page_slug: str) -> str:
        for permission in self.permissions:
            if permission.page_slug == page_slug:
                return permission.access_level
        return "no_access"


class Permission(db.Model):
    __tablename__ = "permission"

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False)
    page_slug = db.Column(db.String(80), nullable=False)
    access_level = db.Column(db.String(20), nullable=False, default="no_access")

    __table_args__ = (
        db.UniqueConstraint("role_id", "page_slug", name="uq_role_page"),
    )


class LlmModel(db.Model):
    __tablename__ = "llm_model"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    provider = db.Column(db.String(80), nullable=False, default="Azure OpenAI")
    deployment_name = db.Column(db.String(120), nullable=False)
    endpoint_url = db.Column(db.String(255), nullable=False)
    api_key_encrypted = db.Column(db.Text, nullable=False)
    model_type = db.Column(db.String(40), nullable=False, default="chat")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Attribute(db.Model):
    __tablename__ = "attribute"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("category", "name", name="uq_attribute_category_name"),
    )


class Integration(db.Model):
    __tablename__ = "integration"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    provider = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    api_key_encrypted = db.Column(db.Text, nullable=True)
    base_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)


class ReleaseNote(db.Model):
    __tablename__ = "release_note"

    id = db.Column(db.Integer, primary_key=True)
    version_major = db.Column(db.Integer, nullable=False, default=1)
    version_minor = db.Column(db.Integer, nullable=False, default=0)
    version_patch = db.Column(db.Integer, nullable=False, default=0)
    version_string = db.Column(db.String(20), nullable=False)
    release_type = db.Column(db.String(20), nullable=False, default="minor")
    title = db.Column(db.String(255), nullable=False)
    summary_markdown = db.Column(db.Text, nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    created_by = db.relationship("User", foreign_keys=[created_by_user_id])


def next_version(release_type: str, latest: ReleaseNote | None) -> tuple[int, int, int]:
    if latest is None:
        return (1, 0, 0)

    major = latest.version_major
    minor = latest.version_minor
    patch = latest.version_patch

    if release_type == "major":
        return (major + 1, 0, 0)
    if release_type == "patch":
        return (major, minor, patch + 1)
    return (major, minor + 1, 0)
