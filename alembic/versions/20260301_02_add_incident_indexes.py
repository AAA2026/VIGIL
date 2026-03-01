"""add incident indexes for production query patterns

Revision ID: 20260301_02
Revises: 20260215_01
Create Date: 2026-03-01
"""

from alembic import op
import sqlalchemy as sa

revision = "20260301_02"
down_revision = "20260215_01"
branch_labels = None
depends_on = None


INDEX_DEFS = (
    ("ix_incidents_timestamp", ["timestamp"]),
    ("ix_incidents_camera_timestamp", ["camera_id", "timestamp"]),
    ("ix_incidents_status_timestamp", ["status", "timestamp"]),
    ("ix_incidents_type_timestamp", ["type", "timestamp"]),
)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "incidents" not in inspector.get_table_names():
        return

    existing = {idx["name"] for idx in inspector.get_indexes("incidents")}
    for name, columns in INDEX_DEFS:
        if name not in existing:
            op.create_index(name, "incidents", columns, unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "incidents" not in inspector.get_table_names():
        return

    existing = {idx["name"] for idx in inspector.get_indexes("incidents")}
    for name, _ in INDEX_DEFS:
        if name in existing:
            op.drop_index(name, table_name="incidents")
