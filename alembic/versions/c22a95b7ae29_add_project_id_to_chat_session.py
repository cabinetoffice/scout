"""add_project_id_to_chat_session

Revision ID: c22a95b7ae29
Revises: 60cc60cacf48
Create Date: 2025-05-16 13:20:47.323772

"""
from typing import Sequence, Union
import uuid
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Column, Table, String, DateTime, ForeignKey, Boolean, func, select, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# revision identifiers, used by Alembic.
revision: str = 'c22a95b7ae29'
down_revision: Union[str, None] = '60cc60cacf48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

Base = declarative_base()

# Define the project_users association table
project_users = Table(
    'project_users',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('user.id'), primary_key=True),
    Column('project_id', UUID(as_uuid=True), ForeignKey('project.id'), primary_key=True)
)

# Define models needed for the migration
class Project(Base):
    __tablename__ = 'project'
    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)

class User(Base):
    __tablename__ = 'user'
    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String, nullable=False)
    projects = relationship("Project", secondary=project_users)

class ChatSession(Base):
    __tablename__ = 'chat_session'
    id = Column(UUID(as_uuid=True), primary_key=True)
    created_datetime = Column(DateTime(timezone=True))
    updated_datetime = Column(DateTime(timezone=True), nullable=True)
    title = Column(String)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'))
    deleted = Column(Boolean, default=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey('project.id'), nullable=True)
    user = relationship("User")

class AuditLog(Base):
    __tablename__ = 'audit_log'
    id = Column(UUID(as_uuid=True), primary_key=True)
    timestamp = Column(DateTime(timezone=True))
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'))
    action_type = Column(String)
    details = Column(JSONB)
    chat_session_id = Column(UUID(as_uuid=True), ForeignKey('chat_session.id'))
    user = relationship("User")

def upgrade() -> None:
    # Add project_id column (nullable at first)
    op.add_column('chat_session',
                  sa.Column('project_id', UUID(as_uuid=True), nullable=True))
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_chat_session_project_id',
        'chat_session', 'project',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Create a session to run the data migration
    connection = op.get_bind()
    Session = sessionmaker(bind=connection)
    session = Session()
    
    try:
        # Get all chat sessions with no project_id
        chat_sessions = session.query(ChatSession).filter(ChatSession.project_id.is_(None)).all()
        
        for chat_session in chat_sessions:
            # Try to find project information from audit logs
            audit_log = session.query(AuditLog).filter(
                AuditLog.chat_session_id == chat_session.id,
                AuditLog.action_type == 'llm_query',
                AuditLog.details.has_key('project_name')  # JSONB query
            ).first()
            
            if audit_log and audit_log.details and 'project_name' in audit_log.details:
                project_name = audit_log.details['project_name']
                
                # Find project by name
                project = session.query(Project).filter(Project.name == project_name).first()
                
                if project:
                    # Set the project ID
                    chat_session.project_id = project.id
                    continue
            
            # If we couldn't find a project from audit logs, use first project from user
            if chat_session.user and chat_session.user.projects:
                chat_session.project_id = chat_session.user.projects[0].id
        
        # Commit the changes
        session.commit()
        
        # Now, make project_id not nullable
        op.alter_column('chat_session', 'project_id',
                       existing_type=UUID(as_uuid=True),
                       nullable=False)
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def downgrade() -> None:
    # Drop foreign key constraint first
    op.drop_constraint('fk_chat_session_project_id', 'chat_session', type_='foreignkey')
    
    # Drop the column
    op.drop_column('chat_session', 'project_id')
