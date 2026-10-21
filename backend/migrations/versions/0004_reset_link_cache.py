"""
Forget cached cross-service links: lookups now fall back to the post's own
title and artist, so earlier "no match" answers may be wrong.

Revision ID: 0004_reset_link_cache
Revises: 0003_embeds_and_link_cache
Create Date: 2026-09-26 18:00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0004_reset_link_cache'
down_revision: Union[str, Sequence[str], None] = '0003_embeds_and_link_cache'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE music_items SET provider_links = NULL, links_resolved_at = NULL")


def downgrade() -> None:
    """Downgrade schema."""
