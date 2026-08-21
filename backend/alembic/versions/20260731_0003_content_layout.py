"""Unified project content layout and section presentation options."""

from alembic import op
import sqlalchemy as sa


revision = "20260731_0003"
down_revision = "20260730_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    project_columns = {column["name"] for column in inspector.get_columns("projects")}
    if "content_layout" not in project_columns:
        with op.batch_alter_table("projects") as batch:
            batch.add_column(
                sa.Column("content_layout", sa.JSON(), nullable=False, server_default="[]")
            )

    section_columns = {
        column["name"]: column for column in inspector.get_columns("project_sections")
    }
    with op.batch_alter_table("project_sections") as batch:
        if "client_key" not in section_columns:
            batch.add_column(sa.Column("client_key", sa.String(length=36), nullable=True))
        if "heading_level" not in section_columns:
            batch.add_column(
                sa.Column("heading_level", sa.Integer(), nullable=False, server_default="2")
            )
        if "is_visible" not in section_columns:
            batch.add_column(
                sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true())
            )

    section_indexes = {
        index["name"] for index in sa.inspect(connection).get_indexes("project_sections")
    }
    if "ix_project_sections_client_key" not in section_indexes:
        with op.batch_alter_table("project_sections") as batch:
            batch.create_index("ix_project_sections_client_key", ["client_key"], unique=False)

    if "client_key" not in section_columns:
        op.execute("UPDATE project_sections SET client_key = uuid WHERE client_key IS NULL")
        with op.batch_alter_table("project_sections") as batch:
            batch.alter_column(
                "client_key", existing_type=sa.String(length=36), nullable=False
            )


def downgrade() -> None:
    with op.batch_alter_table("project_sections") as batch:
        batch.drop_index("ix_project_sections_client_key")
        batch.drop_column("is_visible")
        batch.drop_column("heading_level")
        batch.drop_column("client_key")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("content_layout")
