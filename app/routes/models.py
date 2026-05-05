from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..access import permission_required
from ..crypto import decrypt_value, encrypt_value
from ..extensions import db
from ..models import Attribute, Integration, LlmModel

models_bp = Blueprint("models", __name__, url_prefix="/models")


@models_bp.route("/")
@login_required
@permission_required("models", "view")
def list_models():
    return render_template(
        "models/list.html",
        llm_models=LlmModel.query.order_by(LlmModel.name).all(),
        attributes=Attribute.query.order_by(Attribute.category, Attribute.name).all(),
        integrations=Integration.query.order_by(Integration.category, Integration.provider).all(),
        breadcrumbs=[
            {"label": "Home", "url": url_for("main.dashboard")},
            {"label": "System Config", "url": None},
        ],
    )


@models_bp.route("/llm/add", methods=["POST"])
@login_required
@permission_required("models", "edit")
def add_llm_model():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Model name is required.", "error")
        return redirect(url_for("models.list_models"))

    if LlmModel.query.filter_by(name=name).first():
        flash(f"Model '{name}' already exists.", "error")
        return redirect(url_for("models.list_models"))

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
        is_default=make_default,
    )
    db.session.add(model)
    db.session.commit()
    flash(f"Model '{name}' added.", "success")
    return redirect(url_for("models.list_models"))


@models_bp.route("/llm/<int:model_id>/toggle", methods=["POST"])
@login_required
@permission_required("models", "edit")
def toggle_llm_model(model_id):
    model = LlmModel.query.get_or_404(model_id)
    model.is_active = not model.is_active
    db.session.commit()
    flash(f"Model '{model.name}' {'activated' if model.is_active else 'deactivated'}.", "success")
    return redirect(url_for("models.list_models"))


@models_bp.route("/llm/<int:model_id>/default", methods=["POST"])
@login_required
@permission_required("models", "edit")
def set_default_llm_model(model_id):
    model = LlmModel.query.get_or_404(model_id)
    LlmModel.query.update({"is_default": False})
    model.is_default = True
    db.session.commit()
    flash(f"Model '{model.name}' set as default.", "success")
    return redirect(url_for("models.list_models"))


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
    return redirect(url_for("models.list_models") + "#attributes")


@models_bp.route("/attributes/<int:attribute_id>/toggle", methods=["POST"])
@login_required
@permission_required("attributes", "edit")
def toggle_attribute(attribute_id):
    attribute = Attribute.query.get_or_404(attribute_id)
    attribute.is_active = not attribute.is_active
    db.session.commit()
    flash(f"Attribute '{attribute.name}' updated.", "success")
    return redirect(url_for("models.list_models") + "#attributes")


@models_bp.route("/integrations/<int:integration_id>/save", methods=["POST"])
@login_required
@permission_required("integrations", "edit")
def save_integration(integration_id):
    integration = Integration.query.get_or_404(integration_id)
    integration.base_url = request.form.get("base_url", "").strip() or None
    api_key = request.form.get("api_key", "").strip()
    if api_key:
        integration.api_key_encrypted = encrypt_value(api_key)
    integration.is_active = request.form.get("is_active") == "1"
    db.session.commit()
    flash(f"Integration '{integration.provider}' saved.", "success")
    return redirect(url_for("models.list_models") + "#integrations")


@models_bp.app_template_filter("masked_key")
def masked_key(value: str) -> str:
    plain = decrypt_value(value) if value else ""
    if not plain:
        return "Not set"
    if len(plain) <= 8:
        return "*" * len(plain)
    return plain[:4] + "..." + plain[-4:]

