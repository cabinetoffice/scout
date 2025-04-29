"""change_audit_log_details_to_jsonb

Revision ID: 5793838d774d
Revises: 35abeecc307e
Create Date: 2025-04-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5793838d774d'
down_revision: Union[str, None] = '35abeecc307e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert details column from JSON to JSONB
    op.alter_column('audit_log', 'details',
                    type_=postgresql.JSONB(),
                    existing_type=sa.JSON(),
                    postgresql_using='details::jsonb',
                    existing_nullable=True)


def downgrade() -> None:
    # Convert details column back to JSON from JSONB
    op.alter_column('audit_log', 'details',
                    type_=sa.JSON(),
                    existing_type=postgresql.JSONB(),
                    postgresql_using='details::json',
                    existing_nullable=True)
