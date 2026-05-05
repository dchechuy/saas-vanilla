from pathlib import Path

import markdown
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..access import permission_required
from ..extensions import db
from ..models import ReleaseNote, next_version

help_bp = Blueprint("help", __name__, url_prefix="/help")

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"

DOC_FILES = {
    "quick_start": "QUICK_START.md",
    "user_manual": "USER_MANUAL.md",
    "architecture": "ARCHITECTURE.md",
    "dependencies": "PYTHON_DEPENDENCIES.md",
}


def _render_doc(name: str) -> str:
    content = (DOCS_DIR / DOC_FILES[name]).read_text(encoding="utf-8")
    return markdown.markdown(content, extensions=["tables", "fenced_code"])


@help_bp.route("/")
@login_required
@permission_required("help", "view")
def index():
    return redirect(url_for("help.release_notes"))


@help_bp.route("/release-notes")
@login_required
@permission_required("help", "view")
def release_notes():
    notes = ReleaseNote.query.order_by(
        ReleaseNote.version_major.desc(),
        ReleaseNote.version_minor.desc(),
        ReleaseNote.version_patch.desc(),
    ).all()
    return render_template("help/release_notes.html", notes=notes, active_tab="release_notes")


@help_bp.route("/release-notes/generate", methods=["POST"])
@login_required
@permission_required("help", "edit")
def generate_release_note():
    release_type = request.form.get("release_type", "minor")
    title = request.form.get("title", "").strip()
    summary = request.form.get("summary_markdown", "").strip()

    if current_user.role != "admin":
        return redirect(url_for("main.dashboard"))
    if not title or not summary:
        flash("Title and summary are required.", "error")
        return redirect(url_for("help.release_notes"))

    latest = ReleaseNote.query.order_by(
        ReleaseNote.version_major.desc(),
        ReleaseNote.version_minor.desc(),
        ReleaseNote.version_patch.desc(),
    ).first()
    major, minor, patch = next_version(release_type, latest)
    version_string = f"{major}.{minor}.{patch}"

    note = ReleaseNote(
        version_major=major,
        version_minor=minor,
        version_patch=patch,
        version_string=version_string,
        release_type=release_type,
        title=title,
        summary_markdown=summary,
        created_by_user_id=current_user.id,
    )
    db.session.add(note)
    db.session.commit()
    flash(f"Release note v{version_string} created.", "success")
    return redirect(url_for("help.release_notes"))


@help_bp.route("/quick-start")
@login_required
@permission_required("help", "view")
def quick_start():
    return render_template("help/doc_page.html", active_tab="quick_start", content_html=_render_doc("quick_start"))


@help_bp.route("/user-manual")
@login_required
@permission_required("help", "view")
def user_manual():
    return render_template("help/doc_page.html", active_tab="user_manual", content_html=_render_doc("user_manual"))


@help_bp.route("/architecture")
@login_required
@permission_required("help", "view")
def architecture():
    return render_template("help/doc_page.html", active_tab="architecture", content_html=_render_doc("architecture"))


@help_bp.route("/dependencies")
@login_required
@permission_required("help", "view")
def dependencies():
    return render_template("help/doc_page.html", active_tab="dependencies", content_html=_render_doc("dependencies"))

