"""Initial portfolio schema.

Revision ID: 20260730_0001
Revises:
Create Date: 2026-07-30
"""
from typing import Sequence, Union

from alembic import op

from app.core.database import Base
from app.models import entities  # noqa: F401

revision: str = "20260730_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())

