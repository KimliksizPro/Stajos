"""faz5 ai state

Revision ID: f5a13c9d7e21
Revises: a2059b2bee86
Create Date: 2026-09-14 20:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f5a13c9d7e21"
down_revision = "a2059b2bee86"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE ai_status ADD VALUE IF NOT EXISTS 'PROCESSING'")

    with op.batch_alter_table("daily_logs", schema=None) as batch_op:
        if bind.dialect.name == "sqlite":
            batch_op.alter_column(
                "ai_status",
                existing_type=sa.String(length=8),
                type_=sa.Enum(
                    "PENDING",
                    "PROCESSING",
                    "REFINED",
                    "ACCEPTED",
                    "REJECTED",
                    "ERROR",
                    name="ai_status",
                ),
                existing_nullable=False,
            )
        batch_op.add_column(
            sa.Column("ai_suggested_technologies", sa.JSON(), nullable=True)
        )
        batch_op.add_column(sa.Column("ai_suggested_topics", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("ai_suggested_tags", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "ai_processing_started_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        processing_rows = bind.execute(
            sa.text("SELECT 1 FROM daily_logs WHERE ai_status = 'PROCESSING' LIMIT 1")
        ).first()
        if processing_rows:
            raise RuntimeError("PROCESSING rows must be resolved before downgrade")

        op.execute("ALTER TYPE ai_status RENAME TO ai_status_with_processing")
        op.execute(
            "CREATE TYPE ai_status AS ENUM "
            "('PENDING', 'REFINED', 'ACCEPTED', 'REJECTED', 'ERROR')"
        )
        op.execute(
            "ALTER TABLE daily_logs ALTER COLUMN ai_status TYPE ai_status "
            "USING ai_status::text::ai_status"
        )
        op.execute("DROP TYPE ai_status_with_processing")

    with op.batch_alter_table("daily_logs", schema=None) as batch_op:
        if bind.dialect.name == "sqlite":
            batch_op.alter_column(
                "ai_status",
                existing_type=sa.Enum(
                    "PENDING",
                    "PROCESSING",
                    "REFINED",
                    "ACCEPTED",
                    "REJECTED",
                    "ERROR",
                    name="ai_status",
                ),
                type_=sa.Enum(
                    "PENDING",
                    "REFINED",
                    "ACCEPTED",
                    "REJECTED",
                    "ERROR",
                    name="ai_status",
                ),
                existing_nullable=False,
            )
        batch_op.drop_column("ai_processing_started_at")
        batch_op.drop_column("ai_suggested_tags")
        batch_op.drop_column("ai_suggested_topics")
        batch_op.drop_column("ai_suggested_technologies")
