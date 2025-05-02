"""create role enum and role table

Revision ID: 37d192d5064c
Revises: 5793838d774d
Create Date: 2025-05-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '37d192d5064c'
down_revision: Union[str, None] = '5793838d774d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:

    op.create_table(
        'role',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', postgresql.ENUM('USER', 'ADMIN', 'UPLOADER', name='role_enum'), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_datetime', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_datetime', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Add role_id to user table
    op.add_column('user', sa.Column('role_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_user_role_id', 'user', 'role', ['role_id'], ['id'])

    # Migrate existing role data
    op.execute("""
        WITH new_roles AS (
            INSERT INTO role (id, name, description)
            VALUES 
                (gen_random_uuid(), 'USER', 'Regular user'),
                (gen_random_uuid(), 'ADMIN', 'Administrator with full access'),
                (gen_random_uuid(), 'UPLOADER', 'Can upload and manage files')
            RETURNING id, name
        )
        UPDATE "user" u
        SET role_id = nr.id
        FROM new_roles nr
        WHERE u.role = nr.name::text
    """)

    # Drop the old role column
    op.drop_column('user', 'role')

def downgrade() -> None:
    # Add back the role column
    op.add_column('user', sa.Column('role', sa.String(), nullable=True))

    # Migrate role data back
    op.execute("""
        UPDATE "user" u
        SET role = r.name::text
        FROM role r
        WHERE u.role_id = r.id
    """)

    # Drop the foreign key constraint
    op.drop_constraint('fk_user_role_id', 'user', type_='foreignkey')
    
    # Drop the role_id column
    op.drop_column('user', 'role_id')
    
    # Drop the role table
    op.drop_table('role')
    
    # Drop the role_enum type
    op.execute('DROP TYPE role_enum')
