"""create incidents table

Revision ID: 20260215_01
Revises:
Create Date: 2026-02-15
"""
from alembic import op
import sqlalchemy as sa

revision = "20260215_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "incidents" in inspector.get_table_names():
        return

    op.create_table(
        "incidents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("incident_number", sa.Integer(), autoincrement=True, nullable=True, unique=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("camera_id", sa.String(length=50), nullable=False),
        sa.Column("timestamp", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, default="active"),
        sa.Column("acknowledged", sa.Integer(), nullable=False, default=0),
        sa.Column("ack_by", sa.String(length=120), nullable=True),
        sa.Column("dispatched_to", sa.Text(), nullable=True),
        sa.Column("assigned_security", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, default=0.0),
        sa.Column("video_url", sa.String(length=512), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "incidents" in inspector.get_table_names():
        op.drop_table("incidents")
