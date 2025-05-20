from datetime import datetime
from typing import Optional
from fastapi import Request, Depends
from scout.DataIngest.models.schemas import AuditLogCreate
from scout.utils.storage import postgres_interface as interface
from scout.utils.storage.postgres_models import ChatSession
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import update

# Import get_most_important_words locally to avoid circular imports
from .summarise import get_most_important_words

async def create_audit_log(
    request: Request,
    user_id: UUID,
    action_type: str,
    db: Session,
    details: Optional[dict] = None,
    chat_session_id: Optional[UUID] = None
) -> None:
    """Create an audit log entry."""
    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    audit_log = AuditLogCreate(
        user_id=user_id,
        action_type=action_type,
        details=details,
        ip_address=client_host,
        user_agent=user_agent,
        chat_session_id=chat_session_id
    )
    
    # Save the audit log
    interface.get_or_create_item(audit_log)

    # Update the chat session title if chat_session_id is provided
    if chat_session_id and details and "query" in details:
        query = details["query"]
        if len(query.split()) <= 3:
            new_title = query
        else:
            important_words = get_most_important_words(query, num_important_words=3)
            new_title = " ".join(important_words)

        db.query(ChatSession).filter(
            ChatSession.id == chat_session_id,
            ChatSession.title == 'New Chat'
        ).update({
            "title": new_title,
            "updated_datetime": datetime.utcnow()
        })
        db.commit()

async def log_llm_query(request: Request, user_id: UUID, project_name: str, query: str, db: Session, chat_session_id: UUID, model_id: str, response: dict):
    """Log an LLM query."""
    await create_audit_log(
        request,
        user_id,
        "llm_query",
        db,
        {
            "project_name": project_name,
            "model_id": model_id,
            "query": query,
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        },
        chat_session_id=chat_session_id
    )

async def log_file_operation(request: Request, user_id: UUID, operation: str, db: Session, file_details: dict):
    """Log a file operation (upload/delete)."""
    await create_audit_log(
        request,
        user_id,
        f"file_{operation}",
        db,
        {
            "file": file_details,
            "timestamp": datetime.utcnow().isoformat()
        }
    )