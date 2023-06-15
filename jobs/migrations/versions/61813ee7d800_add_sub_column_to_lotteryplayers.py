"""Add sub column to LotteryPlayers

Revision ID: 61813ee7d800
Revises: 
Create Date: 2023-06-15 21:54:19.779770

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "61813ee7d800"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("LotteryPlayers", sa.Column("sub", sa.Boolean, server_default="0"))


def downgrade() -> None:
    op.drop_column("LotteryPlayers", "sub")
