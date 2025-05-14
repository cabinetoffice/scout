"""populate_chat_session_ids

Revision ID: eac460d174ce
Revises: e83d12402e31
Create Date: 2025-05-12 22:38:11.966071

"""
from typing import Sequence, Union
import uuid
from datetime import datetime
from collections import defaultdict

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Column, ForeignKey, String, DateTime, func, and_, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# revision identifiers, used by Alembic.
revision: str = 'eac460d174ce'
down_revision: Union[str, None] = 'e83d12402e31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String)

class AuditLog(Base):
    __tablename__ = 'audit_log'
    id = Column(UUID(as_uuid=True), primary_key=True)
    timestamp = Column(DateTime(timezone=True))
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'))
    action_type = Column(String)
    details = Column(JSONB)
    chat_session_id = Column(UUID(as_uuid=True), ForeignKey('chat_session.id'), nullable=True)

class ChatSession(Base):
    __tablename__ = 'chat_session'
    id = Column(UUID(as_uuid=True), primary_key=True)
    created_datetime = Column(DateTime(timezone=True))
    updated_datetime = Column(DateTime(timezone=True), nullable=True)
    title = Column(String)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'))
    audit_logs = relationship('AuditLog')


def extract_title_from_first_query(audit_log):
    """Extract a title from the first query in a chat session"""
    try:
        query = audit_log.details.get('query', '')
        # Use the first line or first 30 characters as the title
        title = query.split('\n')[0][:30]
        if not title:
            title = "Chat from " + audit_log.timestamp.strftime("%Y-%m-%d")
        return title
    except (AttributeError, TypeError):
        return "Chat from " + audit_log.timestamp.strftime("%Y-%m-%d")


def upgrade() -> None:
    # Create a connection and session
    connection = op.get_bind()
    Session = sessionmaker(bind=connection)
    session = Session()
    
    try:
        # Get all audit logs with action_type='llm_query'
        llm_query_logs = session.query(AuditLog).filter(
            AuditLog.action_type == 'llm_query'
        ).order_by(AuditLog.timestamp).all()
        
        if not llm_query_logs:
            return  # No logs to process
            
        # Group audit logs by user_id
        user_logs = defaultdict(list)
        for log in llm_query_logs:
            user_logs[log.user_id].append(log)
            
        # Create chat sessions for each user and update audit logs
        for user_id, logs in user_logs.items():
            # For simplicity, we'll create one session per user
            # A more complex approach would analyze timestamps to group by conversation
            session_id = uuid.uuid4()
            title = extract_title_from_first_query(logs[0]) if logs else "Chat History"
            
            # Create new chat session
            chat_session = ChatSession(
                id=session_id,
                created_datetime=logs[0].timestamp if logs else datetime.now(),
                updated_datetime=logs[-1].timestamp if logs else None,
                title=title,
                user_id=user_id
            )
            session.add(chat_session)
            
            # Update audit logs with the session ID
            for log in logs:
                log.chat_session_id = session_id
                
        # Commit the changes
        session.commit()
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def downgrade() -> None:
    # Just set all chat_session_id values to NULL
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE audit_log SET chat_session_id = NULL WHERE action_type = 'llm_query'")
    )
