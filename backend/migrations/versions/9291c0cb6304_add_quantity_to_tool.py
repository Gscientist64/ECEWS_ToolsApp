"""add quantity to Tool

Revision ID: 9291c0cb6304
Revises: 431416d9cefe
Create Date: 2025-09-17 11:05:45.257299

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9291c0cb6304'
down_revision = '431416d9cefe'
branch_labels = None
depends_on = None

def upgrade():
    # 1) Add as nullable with a server default 0 so existing rows pass
    with op.batch_alter_table('tool', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('quantity', sa.Integer(), nullable=True, server_default='0')
        )

    # 2) Backfill any NULLs to 0 just in case (defensive)
    op.execute("UPDATE tool SET quantity = 0 WHERE quantity IS NULL;")

    # 3) Drop the server default and enforce NOT NULL
    with op.batch_alter_table('tool', schema=None) as batch_op:
        # On some PG setups, Alembic needs existing_server_default to be provided
        batch_op.alter_column(
            'quantity',
            existing_type=sa.Integer(),
            nullable=False,
            server_default=None
        )

def downgrade():
    with op.batch_alter_table('tool', schema=None) as batch_op:
        batch_op.drop_column('quantity')
