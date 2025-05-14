"""add_chat_session_table

Revision ID: e83d12402e31
Revises: 37d192d5064c
Create Date: 2025-05-12 22:02:52.045894

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'e83d12402e31'
down_revision: Union[str, None] = '37d192d5064c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the chat_session table
    op.create_table(
        'chat_session',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('created_datetime', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_datetime', sa.DateTime(timezone=True), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False),
    )

    # Add the session_id column to the audit_log table
    op.add_column('audit_log', sa.Column('chat_session_id', UUID(as_uuid=True), 
                                         sa.ForeignKey('chat_session.id'), nullable=True))
    
    # Create an index on chat_session_id for better query performance
    op.create_index('ix_audit_log_chat_session_id', 'audit_log', ['chat_session_id'])

def downgrade() -> None:
    # Remove the foreign key and column from audit_log
    op.drop_index('ix_audit_log_chat_session_id', 'audit_log')
    op.drop_column('audit_log', 'chat_session_id')
    
    # Drop the chat_session table
    op.drop_table('chat_session')
