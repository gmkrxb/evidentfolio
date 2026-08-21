"""Project albums and media-rich sections.

Revision ID: 20260730_0002
Revises: 20260730_0001
Create Date: 2026-07-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models import ProjectAlbum, ProjectAlbumAsset

revision: str = "20260730_0002"
down_revision: Union[str, Sequence[str], None] = "20260730_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    section_columns = _columns("project_sections")
    if "display_mode" not in section_columns:
        op.add_column(
            "project_sections",
            sa.Column("display_mode", sa.String(length=40), nullable=False, server_default="text"),
        )
    if "asset_uuids" not in section_columns:
        op.add_column(
            "project_sections",
            sa.Column("asset_uuids", sa.JSON(), nullable=False, server_default="[]"),
        )
    if "album_uuid" not in section_columns:
        op.add_column(
            "project_sections",
            sa.Column("album_uuid", sa.String(length=36), nullable=True),
        )
        op.create_index(
            "ix_project_sections_album_uuid",
            "project_sections",
            ["album_uuid"],
            unique=False,
        )
    ProjectAlbum.__table__.create(bind=bind, checkfirst=True)
    ProjectAlbumAsset.__table__.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    ProjectAlbumAsset.__table__.drop(bind=bind, checkfirst=True)
    ProjectAlbum.__table__.drop(bind=bind, checkfirst=True)
    columns = _columns("project_sections")
    with op.batch_alter_table("project_sections") as batch:
        if "album_uuid" in columns:
            batch.drop_index("ix_project_sections_album_uuid")
            batch.drop_column("album_uuid")
        if "asset_uuids" in columns:
            batch.drop_column("asset_uuids")
        if "display_mode" in columns:
            batch.drop_column("display_mode")
