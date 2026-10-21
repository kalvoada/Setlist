"""
Native music provider: the listener's chosen service, and cached cross-service
links on music items.

Revision ID: 0002_native_provider
Revises: 0001_initial
Create Date: 2026-09-25 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_native_provider'
down_revision: Union[str, Sequence[str], None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('native_provider', sa.String(length=30), nullable=True))

    with op.batch_alter_table('music_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('provider_links', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('links_resolved_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('music_items', schema=None) as batch_op:
        batch_op.drop_column('links_resolved_at')
        batch_op.drop_column('provider_links')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('native_provider')
