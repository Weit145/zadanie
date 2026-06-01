"""expand finance entities

Revision ID: 20260601_0002
Revises: 20260531_0001
Create Date: 2026-06-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260601_0002"
down_revision: str | None = "20260531_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "category",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="unique_category_user_name"),
    )
    op.create_index(op.f("ix_category_user_id"), "category", ["user_id"], unique=False)

    op.create_table(
        "payment_method",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("method_type", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="unique_payment_method_user_name"),
    )
    op.create_index(
        op.f("ix_payment_method_user_id"),
        "payment_method",
        ["user_id"],
        unique=False,
    )

    op.add_column("expense", sa.Column("category_id", sa.Uuid(), nullable=True))
    op.add_column("expense", sa.Column("payment_method_id", sa.Uuid(), nullable=True))
    op.add_column(
        "expense",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        op.f("ix_expense_category_id"),
        "expense",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_expense_payment_method_id"),
        "expense",
        ["payment_method_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_expense_category_id_category",
        "expense",
        "category",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_expense_payment_method_id_payment_method",
        "expense",
        "payment_method",
        ["payment_method_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "monthly_budget",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("amount > 0", name="ck_monthly_budget_amount_positive"),
        sa.CheckConstraint("month >= 1 AND month <= 12", name="ck_monthly_budget_month"),
        sa.CheckConstraint("year >= 2000 AND year <= 2100", name="ck_monthly_budget_year"),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "category_id",
            "year",
            "month",
            name="unique_budget_user_category_month",
        ),
    )
    op.create_index(
        op.f("ix_monthly_budget_category_id"),
        "monthly_budget",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_monthly_budget_user_id"),
        "monthly_budget",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_monthly_budget_unique_total",
        "monthly_budget",
        ["user_id", "year", "month"],
        unique=True,
        postgresql_where=sa.text("category_id IS NULL"),
        sqlite_where=sa.text("category_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_monthly_budget_unique_total", table_name="monthly_budget")
    op.drop_index(op.f("ix_monthly_budget_user_id"), table_name="monthly_budget")
    op.drop_index(op.f("ix_monthly_budget_category_id"), table_name="monthly_budget")
    op.drop_table("monthly_budget")

    op.drop_constraint(
        "fk_expense_payment_method_id_payment_method",
        "expense",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_expense_category_id_category",
        "expense",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_expense_payment_method_id"), table_name="expense")
    op.drop_index(op.f("ix_expense_category_id"), table_name="expense")
    op.drop_column("expense", "updated_at")
    op.drop_column("expense", "payment_method_id")
    op.drop_column("expense", "category_id")

    op.drop_index(op.f("ix_payment_method_user_id"), table_name="payment_method")
    op.drop_table("payment_method")

    op.drop_index(op.f("ix_category_user_id"), table_name="category")
    op.drop_table("category")

    op.drop_column("user", "updated_at")
