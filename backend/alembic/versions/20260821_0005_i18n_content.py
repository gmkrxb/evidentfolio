"""Add non-destructive bilingual content fields."""

from alembic import op
import sqlalchemy as sa

revision = "20260821_0005"
down_revision = "20260731_0004"
branch_labels = None
depends_on = None


def _add(table: str, name: str, column: sa.Column) -> None:
    connection = op.get_bind()
    columns = {item["name"] for item in sa.inspect(connection).get_columns(table)}
    if name not in columns:
        with op.batch_alter_table(table) as batch:
            batch.add_column(column)


def upgrade() -> None:
    connection = op.get_bind()
    if "ai_settings" not in sa.inspect(connection).get_table_names():
        op.create_table(
            "ai_settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("base_url", sa.String(1000), nullable=False, server_default=""),
            sa.Column("encrypted_api_key", sa.Text(), nullable=False, server_default=""),
            sa.Column("model", sa.String(200), nullable=False, server_default=""),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
    for table in ["project_categories", "tags", "projects", "project_sections", "project_albums", "assets", "certificates"]:
        _add(table, "translations", sa.Column("translations", sa.JSON(), nullable=False, server_default="{}"))
    _add("projects", "content_language_mode", sa.Column("content_language_mode", sa.String(20), nullable=False, server_default="bilingual"))
    _add("certificates", "content_language_mode", sa.Column("content_language_mode", sa.String(20), nullable=False, server_default="bilingual"))


def downgrade() -> None:
    for table in ["certificates", "assets", "project_albums", "project_sections", "projects", "tags", "project_categories"]:
        with op.batch_alter_table(table) as batch:
            if table in {"projects", "certificates"}:
                batch.drop_column("content_language_mode")
            batch.drop_column("translations")
    op.drop_table("ai_settings")
