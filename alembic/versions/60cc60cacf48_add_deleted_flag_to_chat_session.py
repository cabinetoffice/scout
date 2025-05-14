"""add_deleted_flag_to_chat_session

Revision ID: 60cc60cacf48
Revises: eac460d174ce
Create Date: 2025-05-14 09:16:39.538029

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60cc60cacf48'
down_revision: Union[str, None] = 'eac460d174ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add deleted column with default value of False
    op.add_column('chat_session',
                  sa.Column('deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    
    # Create an index on deleted for better query performance
    op.create_index('ix_chat_session_deleted', 'chat_session', ['deleted'])


def downgrade() -> None:
    # Drop the index first
    op.drop_index('ix_chat_session_deleted', table_name='chat_session')
    
    # Then drop the column
    op.drop_column('chat_session', 'deleted')
