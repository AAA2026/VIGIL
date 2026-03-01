"""Baseline revision matching current schema (tables already exist)."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Schema already created via application bootstrap; this baseline marks current state.
    pass


def downgrade() -> None:
    # No-op; baseline.
    pass
