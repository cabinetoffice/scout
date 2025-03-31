"""add GATE_5 to criterion_gate_enum

Revision ID: 58842de7cb9e
Revises: 586333ad0703
Create Date: 2025-03-28 17:42:09.144600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58842de7cb9e'
down_revision: Union[str, None] = '586333ad0703'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE criterion_gate_enum ADD VALUE 'GATE_5'")


def downgrade() -> None:
    pass
