import uuid
import requests as http_requests
from flask import (Blueprint, abort, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required

from ..access import permission_required
from ..crypto import decrypt_value
from ..extensions import db
from ..models import AgentConversation, AgentMessage, AiAgent

agents_bp = Blueprint("agents", __name__, url_prefix="/agents")

_SKUNK_TIMEOUT = 30  # seconds


def _call_skunkbox(integration, skunkbox_agent_id: int,
                   message: str, session_id: str,
                   user_full_name: str = "", username: str = "") -> dict:
    """POST to skunkBOX /api/v1/chat/messages. Returns the JSON body or raises."""
    base_url = (integration.base_url or "").rstrip("/")
    # Normalise: strip trailing /api/v1 so the path below never doubles it
    if base_url.endswith("/api/v1"):
        base_url = base_url[:-len("/api/v1")]
    if not base_url:
        raise ValueError("Integration has no base URL configured.")

    api_key = decrypt_value(integration.api_key_encrypted or "")
    if not api_key:
        raise ValueError("Integration has no API key configured.")

    payload = {
        "persona_id": skunkbox_agent_id,
        "session_id": session_id,
        "user_full_name": user_full_name,
        "username": username,
        "message": message,
    }

    resp = http_requests.post(
        f"{base_url}/api/v1/chat/messages",
        json=payload,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        timeout=_SKUNK_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# Conversations list
# ─────────────────────────────────────────────────────────────────────────────

@agents_bp.route("/")
@login_required
@permission_required("agents", "view")
def list_conversations():
    ai_agents = AiAgent.query.filter_by(is_active=True).order_by(AiAgent.name).all()
    conversations = (
        AgentConversation.query
        .filter_by(user_id=current_user.id, is_archived=False)
        .order_by(AgentConversation.updated_at.desc())
        .all()
    )
    return render_template(
        "agents/list.html",
        ai_agents=ai_agents,
        conversations=conversations,
        breadcrumbs=[
            {"label": "Home", "url": url_for("main.dashboard")},
            {"label": "AI Agents", "url": url_for("agents.list_conversations")},
            {"label": "Conversations", "url": None},
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Start a new conversation
# ─────────────────────────────────────────────────────────────────────────────

@agents_bp.route("/new", methods=["POST"])
@login_required
@permission_required("agents", "view")
def new_conversation():
    agent_id = request.form.get("agent_id", "").strip()
    if not agent_id:
        flash("Please select an agent.", "error")
        return redirect(url_for("agents.list_conversations"))

    agent = db.session.get(AiAgent, int(agent_id))
    if not agent or not agent.is_active:
        abort(404)

    conv = AgentConversation(
        ai_agent_id=agent.id,
        user_id=current_user.id,
        title=f"Conversation with {agent.name}",
        skunkbox_session_id=str(uuid.uuid4()),
    )
    db.session.add(conv)
    db.session.commit()
    return redirect(url_for("agents.view_conversation", conversation_id=conv.id))


# ─────────────────────────────────────────────────────────────────────────────
# View / chat in a conversation
# ─────────────────────────────────────────────────────────────────────────────

@agents_bp.route("/<int:conversation_id>")
@login_required
@permission_required("agents", "view")
def view_conversation(conversation_id):
    conv = db.get_or_404(AgentConversation, conversation_id)
    if conv.user_id != current_user.id:
        abort(403)

    messages = conv.messages.order_by(AgentMessage.created_at).all()
    return render_template(
        "agents/conversation.html",
        conv=conv,
        agent=conv.agent,
        messages=messages,
        breadcrumbs=[
            {"label": "Home", "url": url_for("main.dashboard")},
            {"label": "AI Agents", "url": url_for("agents.list_conversations")},
            {"label": "Conversations", "url": url_for("agents.list_conversations")},
            {"label": conv.title or conv.agent.name, "url": None},
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Send a message  (AJAX — returns JSON)
# ─────────────────────────────────────────────────────────────────────────────

@agents_bp.route("/<int:conversation_id>/send", methods=["POST"])
@login_required
@permission_required("agents", "view")
def send_message(conversation_id):
    conv = db.get_or_404(AgentConversation, conversation_id)
    if conv.user_id != current_user.id:
        return jsonify({"ok": False, "error": "Forbidden"}), 403

    data = request.get_json(force=True) or {}
    content = (data.get("message") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "Message is empty."}), 400

    agent = conv.agent
    if not agent or not agent.is_active:
        return jsonify({"ok": False, "error": "Agent is not available."}), 400

    # Persist the user message immediately
    user_msg = AgentMessage(
        conversation_id=conv.id,
        role="user",
        content=content,
    )
    db.session.add(user_msg)

    # Auto-title the conversation from the first user message
    if not conv.title or conv.title == f"Conversation with {agent.name}":
        conv.title = content[:80]

    db.session.commit()

    # Call skunkBOX
    try:
        result = _call_skunkbox(
            integration=agent.integration,
            skunkbox_agent_id=agent.skunkbox_agent_id,
            message=content,
            session_id=conv.skunkbox_session_id,
            user_full_name=current_user.display_name or current_user.username,
            username=current_user.username,
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502

    # Persist session_id for continuity (skunkBOX returns it)
    new_session_id = result.get("session_id") or result.get("sessionId")
    if new_session_id and new_session_id != conv.skunkbox_session_id:
        conv.skunkbox_session_id = str(new_session_id)

    # Extract the assistant reply
    reply_text = (
        result.get("response")
        or result.get("message")
        or result.get("content")
        or result.get("text")
        or "[No response]"
    )

    assistant_msg = AgentMessage(
        conversation_id=conv.id,
        role="assistant",
        content=reply_text,
    )
    db.session.add(assistant_msg)
    db.session.commit()

    return jsonify({
        "ok": True,
        "user_message_id": user_msg.id,
        "assistant": {
            "id": assistant_msg.id,
            "content": reply_text,
            "created_at": assistant_msg.created_at.isoformat(),
        },
    })


# ─────────────────────────────────────────────────────────────────────────────
# Archive a conversation
# ─────────────────────────────────────────────────────────────────────────────

@agents_bp.route("/<int:conversation_id>/archive", methods=["POST"])
@login_required
@permission_required("agents", "view")
def archive_conversation(conversation_id):
    conv = db.get_or_404(AgentConversation, conversation_id)
    if conv.user_id != current_user.id:
        abort(403)
    conv.is_archived = True
    db.session.commit()
    flash("Conversation archived.", "success")
    return redirect(url_for("agents.list_conversations"))
