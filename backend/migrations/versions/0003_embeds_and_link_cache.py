"""
Players embedded in posts, and a fresh cross-service link cache.

Links are now looked up per service, and "no match" is stored per service too,
so the old cache (built by an older matcher) is cleared and rebuilt on demand.

Revision ID: 0003_embeds_and_link_cache
Revises: 0002_native_provider
Create Date: 2026-09-26 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_embeds_and_link_cache'
down_revision: Union[str, Sequence[str], None] = '0002_native_provider'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('music_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('embed_url', sa.String(length=500), nullable=True))

    op.execute("UPDATE music_items SET provider_links = NULL, links_resolved_at = NULL")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('music_items', schema=None) as batch_op:
        batch_op.drop_column('embed_url')
