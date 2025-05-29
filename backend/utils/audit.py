from datetime import datetime
from typing import Optional
from fastapi import Request, Depends
from scout.DataIngest.models.schemas import AuditLogCreate
from scout.utils.storage import postgres_interface as interface
from scout.utils.storage.postgres_models import ChatSession
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from scout.utils.storage.postgres_models import project_users

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

    # Check if the chat session already exists
    existing_session = db.query(ChatSession).filter(ChatSession.id == chat_session_id).first()
    if not existing_session:

        # Update the chat session title if chat_session_id is provided
        if chat_session_id and details and "query" in details:
            query = details["query"]
            if len(query.split()) <= 3:
                new_title = query
            else:
                important_words = get_most_important_words(query, num_important_words=3)
                new_title = " ".join(important_words)

            result = db.execute(
                select(project_users.c.project_id).where(project_users.c.user_id == user_id)
            ).fetchall()
            project_ids = [row[0] for row in result]

            new_session = ChatSession(
                id=chat_session_id,
                created_datetime=datetime.utcnow(),
                updated_datetime=datetime.utcnow(),
                title=new_title,
                user_id=user_id,
                project_id=project_ids[0],
                deleted=False
            )

            db.add(new_session)
            db.commit()
            db.refresh(new_session)

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

async def log_llm_query(request: Request, user_id: UUID, project_name: str, query: str, db: Session, chat_session_id: UUID, model_id: str, response: dict, custom_system_prompt: Optional[str] = None):
    """Log an LLM query."""
    details = {
        "project_name": project_name,
        "model_id": model_id,
        "query": query,
        "response": response,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add custom system prompt to details if provided
    if custom_system_prompt:
        details["custom_system_prompt"] = custom_system_prompt
    
    await create_audit_log(
        request,
        user_id,
        "llm_query",
        db,
        details,
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