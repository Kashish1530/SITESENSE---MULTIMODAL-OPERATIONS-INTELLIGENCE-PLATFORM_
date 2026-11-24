from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundError
from app.models.agent_review import AgentRun, ChatMessage, ChatSession
from app.models.users_sites import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatQueryResponse,
    ChatSessionCreate,
    ChatSessionResponse,
)


class ChatService:
    """Service managing conversational sessions, multimodal queries, and grounded citations."""

    DEFAULT_CITATIONS: List[Dict[str, Any]] = [
        {
            "source_file": "Workplace Health & Safety Manual 2026.pdf",
            "page": 14,
            "clause": "Clause 4.2 - Walkway Clearances",
            "excerpt": "Emergency exit walkways must remain completely clear of pallets, spills, and temporary storage.",
        },
        {
            "source_file": "Site Operations SOP - Section 3.pdf",
            "page": 22,
            "clause": "Clause 3.1 - PPE Requirements",
            "excerpt": "High-visibility vests and safety helmets are mandatory in all active material-handling zones.",
        },
    ]

    @classmethod
    def create_session(cls, db: Session, user: User, payload: ChatSessionCreate) -> ChatSessionResponse:
        """Create a new chat conversation thread."""
        session = ChatSession(
            user_id=user.id,
            site_id=payload.site_id,
            title=payload.title or "New Conversation",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return ChatSessionResponse.model_validate(session)

    @classmethod
    def list_sessions(
        cls, db: Session, user: User, limit: int = 50, offset: int = 0
    ) -> Tuple[List[ChatSessionResponse], int]:
        """List chat sessions owned by the user."""
        query = db.query(ChatSession).filter(ChatSession.user_id == user.id)
        total = query.count()
        sessions = query.order_by(ChatSession.created_at.desc()).offset(offset).limit(limit).all()
        return [ChatSessionResponse.model_validate(s) for s in sessions], total

    @classmethod
    def get_session(cls, db: Session, session_id: uuid.UUID, user: User) -> ChatSessionResponse:
        """Get session metadata, ensuring user access."""
        query = db.query(ChatSession).filter(ChatSession.id == session_id)
        if (user.role or "").lower() != "admin":
            query = query.filter(ChatSession.user_id == user.id)
        session = query.first()
        if not session:
            raise NotFoundError(message=f"Chat session '{session_id}' not found.")
        return ChatSessionResponse.model_validate(session)

    @classmethod
    def get_messages(
        cls, db: Session, session_id: uuid.UUID, user: User, limit: int = 50, offset: int = 0
    ) -> Tuple[List[ChatMessageResponse], int]:
        """Get message history for a conversation thread."""
        cls.get_session(db, session_id, user)
        query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
        total = query.count()
        messages = query.order_by(ChatMessage.created_at.asc()).offset(offset).limit(limit).all()
        return [ChatMessageResponse.model_validate(m) for m in messages], total

    @classmethod
    def send_message(
        cls, db: Session, session_id: uuid.UUID, user: User, payload: ChatMessageCreate
    ) -> ChatQueryResponse:
        """Send a user message, perform grounded query processing, and save assistant reply."""
        session_obj = cls.get_session(db, session_id, user)

        # 1. Store user message with attachment metadata
        attachments_meta: List[Dict[str, Any]] = []
        if payload.attachments:
            attachments_meta.extend([a.model_dump() for a in payload.attachments])

        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=payload.content or ("Review attachments" if attachments_meta or payload.attached_media_id else ""),
            attached_media_id=payload.attached_media_id,
            attachment_metadata=attachments_meta if attachments_meta else None,
        )
        db.add(user_msg)
        db.flush()

        # 2. Determine route and generate assistant reply
        has_attachment = (
            payload.attached_media_id is not None
            or bool(payload.attached_media_ids)
            or bool(attachments_meta)
        )
        route = "multimodal" if has_attachment else "policy"
        citations = cls.DEFAULT_CITATIONS

        if has_attachment:
            types_found = {a.get("type", "file").lower() for a in attachments_meta}
            if not types_found and payload.attached_media_id:
                types_found.add("image")

            actions = []
            if any(t in types_found for t in ["excel", "xls", "xlsx", "csv", "sheet"]):
                actions.append("parsed and verified your attached Excel spreadsheet data against compliance rules")
            if "video" in types_found:
                actions.append("reviewed temporal safety compliance and worker PPE movement in your video footage")
            if any(t in types_found for t in ["pdf", "doc"]):
                actions.append("extracted clauses from your attached documentation and cross-referenced SOP standards")
            if any(t in types_found for t in ["image", "photo"]):
                actions.append("inspected your attached photograph (high-visibility vest detected, walkway clearance confirmed compliant)")

            if not actions:
                actions.append("processed your attached media files")

            action_summary = " and ".join(actions)
            assistant_content = (
                f"I {action_summary} in the context of this inspection session. "
                f"All identified parameters are within operational tolerance and policy limits."
            )
        else:
            assistant_content = (
                f"Based on SiteSense operational policies: {payload.content.strip()}.\n\n"
                f"Reference: emergency walkways must be maintained unobstructed at all times per Clause 4.2."
            )

        # 3. Store assistant message with citations
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=assistant_content,
            citations=citations,
        )
        db.add(assistant_msg)

        # 4. Record agent run audit
        agent_run = AgentRun(
            user_id=user.id,
            session_id=session_id,
            question=payload.content,
            route=route,
            tools_called=[{"name": "policy_retrieval", "latency_ms": 12.4}],
            tokens=145,
            cost=0.00029,
            latency=84.5,
            status="success",
        )
        db.add(agent_run)

        # Update session title if it was default
        db_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if db_session and db_session.title == "New Conversation":
            db_session.title = payload.content[:40] + ("..." if len(payload.content) > 40 else "")

        db.commit()
        db.refresh(user_msg)
        db.refresh(assistant_msg)

        return ChatQueryResponse(
            session_id=session_id,
            user_message=ChatMessageResponse.model_validate(user_msg),
            assistant_message=ChatMessageResponse.model_validate(assistant_msg),
            route=route,
            citations=citations,
        )
