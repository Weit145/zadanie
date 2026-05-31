"""init expense tracker

Revision ID: 20260531_0001
Revises:
Create Date: 2026-05-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260531_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="unique_user_name"),
    )
    op.create_index(op.f("ix_user_telegram_id"), "user", ["telegram_id"], unique=True)

    op.create_table(
        "expense",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("spent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_expense_category"), "expense", ["category"], unique=False)
    op.create_index(op.f("ix_expense_spent_at"), "expense", ["spent_at"], unique=False)
    op.create_index(op.f("ix_expense_user_id"), "expense", ["user_id"], unique=False)
    op.create_index("ix_expense_user_spent_at", "expense", ["user_id", "spent_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_expense_user_spent_at", table_name="expense")
    op.drop_index(op.f("ix_expense_user_id"), table_name="expense")
    op.drop_index(op.f("ix_expense_spent_at"), table_name="expense")
    op.drop_index(op.f("ix_expense_category"), table_name="expense")
    op.drop_table("expense")
    op.drop_index(op.f("ix_user_telegram_id"), table_name="user")
    op.drop_table("user")
