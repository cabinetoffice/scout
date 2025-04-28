from datetime import datetime
from typing import Optional
from fastapi import Request
from scout.DataIngest.models.schemas import AuditLogCreate
from scout.utils.storage import postgres_interface as interface
from uuid import UUID

async def create_audit_log(
    request: Request,
    user_id: UUID,
    action_type: str,
    details: Optional[dict] = None
) -> None:
    """Create an audit log entry."""
    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    audit_log = AuditLogCreate(
        user_id=user_id,
        action_type=action_type,
        details=details,
        ip_address=client_host,
        user_agent=user_agent
    )
    
    interface.get_or_create_item(audit_log)

async def log_llm_query(request: Request, user_id: UUID, query: str, response: dict):
    """Log an LLM query."""
    await create_audit_log(
        request,
        user_id,
        "llm_query",
        {
            "query": query,
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

async def log_file_operation(request: Request, user_id: UUID, operation: str, file_details: dict):
    """Log a file operation (upload/delete)."""
    await create_audit_log(
        request,
        user_id,
        f"file_{operation}",
        {
            "file": file_details,
            "timestamp": datetime.utcnow().isoformat()
        }
    )