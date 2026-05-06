from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..access import permission_required, user_has_access
from ..crypto import encrypt_value
from ..extensions import db
from ..models import Attribute, Integration, LlmModel

models_bp = Blueprint("models", __name__, url_prefix="/models")


def _redirect_to_system_config(anchor: str = "integrations"):
    return redirect(f"{url_for('models.list_models')}#{anchor}")


@models_bp.route("/")
@login_required
def list_models():
    can_view_models = user_has_access("models", "view")
    can_view_attributes = user_has_access("attributes", "view")
    can_view_integrations = user_has_access("integrations", "view")

    if not any([can_view_models, can_view_attributes, can_view_integrations]):
        flash("You do not have permission to access this page.", "error")
        return redirect(url_for("main.dashboard"))

    return render_template(
        "models/list.html",
        llm_models=LlmModel.query.order_by(LlmModel.name).all() if can_view_models else [],
        attributes=Attribute.query.order_by(Attribute.category, Attribute.name).all() if can_view_attributes else [],
        integrations=Integration.query.order_by(Integration.category, Integration.provider, Integration.name).all() if can_view_integrations else [],
        can_view_models=can_view_models,
        can_view_attributes=can_view_attributes,
        can_view_integrations=can_view_integrations,
        breadcrumbs=[
            {"label": "Home", "url": url_for("main.dashboard")},
            {"label": "Administration", "url": None},
        ],
    )


@models_bp.route("/llm/add", methods=["POST"])
@login_required
@permission_required("models", "edit")
def add_llm_model():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Model name is required.", "error")
        return _redirect_to_system_config()

    if LlmModel.query.filter_by(name=name).first():
        flash(f"Model '{name}' already exists.", "error")
        return _redirect_to_system_config()

    make_default = request.form.get("is_default") == "1"
    if make_default:
        LlmModel.query.update({"is_default": False})

    model = LlmModel(
        name=name,
        provider=request.form.get("provider", "Azure OpenAI").strip() or "Azure OpenAI",
        deployment_name=request.form.get("deployment_name", "").strip(),
        endpoint_url=request.form.get("endpoint_url", "").strip(),
        api_key_encrypted=encrypt_value(request.form.get("api_key", "").strip()),
        model_type=request.form.get("model_type", "chat").strip() or "chat",
        is_active=request.form.get("is_active", "1") == "1",
        is_default=make_default,
    )
    db.session.add(model)
    db.session.commit()
    flash(f"Model '{name}' added.", "success")
    return _redirect_to_system_config()


@models_bp.route("/llm/<int:model_id>/update", methods=["POST"])
@login_required
@permission_required("models", "edit")
def update_llm_model(model_id):
    model = db.get_or_404(LlmModel, model_id)
    name = request.form.get("name", "").strip()
    if not name:
        flash("Model name is required.", "error")
        return _redirect_to_system_config()

    duplicate = LlmModel.query.filter(LlmModel.name == name, LlmModel.id != model.id).first()
    if duplicate:
        flash(f"Model '{name}' already exists.", "error")
        return _redirect_to_system_config()

    make_default = request.form.get("is_default") == "1"
    if make_default:
        LlmModel.query.update({"is_default": False})

    model.name = name
    model.provider = request.form.get("provider", "Azure OpenAI").strip() or "Azure OpenAI"
    model.deployment_name = request.form.get("deployment_name", "").strip()
    model.endpoint_url = request.form.get("endpoint_url", "").strip()
    model.model_type = request.form.get("model_type", "chat").strip() or "chat"
    model.is_active = request.form.get("is_active") == "1"
    model.is_default = make_default

    api_key = request.form.get("api_key", "").strip()
    if api_key:
        model.api_key_encrypted = encrypt_value(api_key)

    db.session.commit()
    flash(f"Model '{model.name}' updated.", "success")
    return _redirect_to_system_config()


@models_bp.route("/attributes/add", methods=["POST"])
@login_required
@permission_required("attributes", "edit")
def add_attribute():
    category = request.form.get("category", "").strip()
    name = request.form.get("name", "").strip()
    if not category or not name:
        flash("Attribute category and name are required.", "error")
    elif Attribute.query.filter_by(category=category, name=name).first():
        flash("That attribute already exists.", "error")
    else:
        db.session.add(
            Attribute(
                category=category,
                name=name,
                description=request.form.get("description", "").strip() or None,
            )
        )
        db.session.commit()
        flash("Attribute added.", "success")
    return _redirect_to_system_config("attributes")


@models_bp.route("/attributes/<int:attribute_id>/toggle", methods=["POST"])
@login_required
@permission_required("attributes", "edit")
def toggle_attribute(attribute_id):
    attribute = db.get_or_404(Attribute, attribute_id)
    attribute.is_active = not attribute.is_active
    db.session.commit()
    flash(f"Attribute '{attribute.name}' updated.", "success")
    return _redirect_to_system_config("attributes")


@models_bp.route("/integrations/add", methods=["POST"])
@login_required
@permission_required("integrations", "edit")
def add_integration():
    name = request.form.get("name", "").strip()
    provider = request.form.get("provider", "").strip()
    category = request.form.get("category", "").strip()
    if not name or not provider or not category:
        flash("Integration name, provider, and category are required.", "error")
        return _redirect_to_system_config()

    if Integration.query.filter_by(name=name).first():
        flash(f"Integration '{name}' already exists.", "error")
        return _redirect_to_system_config()

    integration = Integration(
        name=name,
        provider=provider,
        category=category,
        description=request.form.get("description", "").strip() or None,
        base_url=request.form.get("base_url", "").strip() or None,
        is_active=request.form.get("is_active", "1") == "1",
    )
    api_key = request.form.get("api_key", "").strip()
    if api_key:
        integration.api_key_encrypted = encrypt_value(api_key)

    db.session.add(integration)
    db.session.commit()
    flash(f"Integration '{integration.provider}' added.", "success")
    return _redirect_to_system_config()


@models_bp.route("/integrations/<int:integration_id>/save", methods=["POST"])
@login_required
@permission_required("integrations", "edit")
def save_integration(integration_id):
    integration = db.get_or_404(Integration, integration_id)

    name = request.form.get("name", "").strip()
    provider = request.form.get("provider", "").strip()
    category = request.form.get("category", "").strip()
    if not name or not provider or not category:
        flash("Integration name, provider, and category are required.", "error")
        return _redirect_to_system_config()

    duplicate = Integration.query.filter(Integration.name == name, Integration.id != integration.id).first()
    if duplicate:
        flash(f"Integration '{name}' already exists.", "error")
        return _redirect_to_system_config()

    integration.name = name
    integration.provider = provider
    integration.category = category
    integration.description = request.form.get("description", "").strip() or None
    integration.base_url = request.form.get("base_url", "").strip() or None
    integration.is_active = request.form.get("is_active") == "1"

    api_key = request.form.get("api_key", "").strip()
    if api_key:
        integration.api_key_encrypted = encrypt_value(api_key)

    db.session.commit()
    flash(f"Integration '{integration.provider}' saved.", "success")
    return _redirect_to_system_config()
