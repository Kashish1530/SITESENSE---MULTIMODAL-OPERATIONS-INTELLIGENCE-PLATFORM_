"""Add site ownership and vector embeddings to policy documents."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision: str = "b7c9e2a41d63"
down_revision: Union[str, None] = "9642f2348088"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Assign policies to individual sites.
    # Existing policies remain unassigned (NULL).
    op.add_column(
        "policies",
        sa.Column("site_id", sa.Uuid(), nullable=True),
    )

    op.create_foreign_key(
        "fk_policies_site_id_sites",
        "policies",
        "sites",
        ["site_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_policies_site_id",
        "policies",
        ["site_id"],
        unique=False,
    )

    # Store normalized 384-dimensional embeddings for policy chunks.
    # Existing chunks remain valid with NULL embeddings.
    op.add_column(
        "policy_chunks",
        sa.Column("embedding", Vector(384), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("policy_chunks", "embedding")

    op.drop_index("ix_policies_site_id", table_name="policies")

    op.drop_constraint(
        "fk_policies_site_id_sites",
        "policies",
        type_="foreignkey",
    )

    op.drop_column("policies", "site_id")
