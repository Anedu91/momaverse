"""add extracted_event_logs table

Revision ID: aa7d45d2cf62
Revises: 50e1159260e2
Create Date: 2026-03-22 12:47:12.830140

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'aa7d45d2cf62'
down_revision: Union[str, Sequence[str], None] = '50e1159260e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


extracted_event_status = sa.Enum(
    'created', 'merged', 'skipped_no_location',
    'skipped_no_occurrences', 'skipped_duplicate',
    name='extracted_event_status',
)


def upgrade() -> None:
    """Upgrade schema."""
    extracted_event_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'extracted_event_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('extracted_event_id', sa.Integer(), nullable=False),
        sa.Column('status', extracted_event_status, nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['extracted_event_id'],
            ['extracted_events.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['event_id'],
            ['events.id'],
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('extracted_event_logs')
    extracted_event_status.drop(op.get_bind(), checkfirst=True)
