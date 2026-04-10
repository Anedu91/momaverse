"""add skipped_tag_removed to extracted_event_status enum

Revision ID: a1b2c3d4e5f6
Revises: 428076a8a9f8
Create Date: 2026-04-10 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "428076a8a9f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Postgres disallows ``ALTER TYPE ... ADD VALUE`` inside a transaction,
    so we run the statement in an autocommit block.
    """
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE extracted_event_status "
            "ADD VALUE IF NOT EXISTS 'skipped_tag_removed'"
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres does not support removing values from an enum type, so this
    # downgrade is intentionally a no-op. Rolling back would require
    # recreating the enum and rewriting all dependent columns.
    pass
