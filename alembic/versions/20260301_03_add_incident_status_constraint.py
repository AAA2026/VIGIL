"""add incident status check constraint

Revision ID: 20260301_03
Revises: 20260301_02
Create Date: 2026-03-01
"""

from alembic import op
import sqlalchemy as sa

revision = "20260301_03"
down_revision = "20260301_02"
branch_labels = None
depends_on = None

TABLE_NAME = "incidents"
CONSTRAINT_NAME = "ck_incidents_status_enum"
CONDITION_SQL = "status IN ('active', 'acknowledged', 'dispatched', 'resolved')"


def _has_constraint(inspector) -> bool:
    for item in inspector.get_check_constraints(TABLE_NAME):
        if item.get("name") == CONSTRAINT_NAME:
            return True
    return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABLE_NAME not in inspector.get_table_names():
        return

    # SQLite cannot add check constraints with ALTER TABLE without table rebuild.
    if bind.dialect.name == "sqlite":
        return

    if not _has_constraint(inspector):
        op.create_check_constraint(CONSTRAINT_NAME, TABLE_NAME, CONDITION_SQL)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABLE_NAME not in inspector.get_table_names():
        return

    if bind.dialect.name == "sqlite":
        return

    if _has_constraint(inspector):
        op.drop_constraint(CONSTRAINT_NAME, TABLE_NAME, type_="check")
