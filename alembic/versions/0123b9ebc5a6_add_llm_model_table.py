"""add_llm_model_table

Revision ID: 0123b9ebc5a6
Revises: c22a95b7ae29
Create Date: 2025-05-19 13:22:59.450662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0123b9ebc5a6'
down_revision: Union[str, None] = 'c22a95b7ae29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'llm_model',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('model_id', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('is_default', sa.Boolean(), default=False),
        sa.Column('created_datetime', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_datetime', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_id')
    )
    
    # Add default models
    op.execute(
        """
        INSERT INTO llm_model (id, name, model_id, description, is_default)
        VALUES 
        (gen_random_uuid(), 'Claude 3 Sonnet', 'anthropic.claude-3-sonnet-20240229-v1:0', 'Powerful, balanced model for enterprise use cases', TRUE),
        (gen_random_uuid(), 'Claude 3 Haiku', 'anthropic.claude-3-haiku-20240307-v1:0', 'Fast and efficient model for quick interactions', FALSE),
        (gen_random_uuid(), 'Llama 3 70B Instruct', 'meta.llama3-70b-instruct-v1:0', 'Meta Llama 3 is an accessible, open large language model (LLM) designed for developers, researchers, and businesses', FALSE),
        (gen_random_uuid(), 'Mistral Large (24.02)', 'mistral.mistral-large-2402-v1:0', 'The most advanced Mistral AI Large Language model capable of handling any language task including complex multilingual reasoning, text understanding, transformation, and code generation', FALSE)
        """
    )


def downgrade() -> None:
    op.drop_table('llm_model')
