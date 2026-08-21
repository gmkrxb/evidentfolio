"""Asset folders for stable UUID-based resource organization."""

from alembic import op
import sqlalchemy as sa


revision = "20260731_0004"
down_revision = "20260731_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "asset_folders" not in inspector.get_table_names():
        op.create_table(
            "asset_folders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("name"),
            sa.UniqueConstraint("uuid"),
            sa.ForeignKeyConstraint(
                ["parent_id"], ["asset_folders.id"], ondelete="CASCADE"
            ),
        )
        op.create_index("ix_asset_folders_name", "asset_folders", ["name"], unique=True)
        op.create_index("ix_asset_folders_sort_order", "asset_folders", ["sort_order"])
        op.create_index("ix_asset_folders_created_at", "asset_folders", ["created_at"])
        op.create_index("ix_asset_folders_parent_id", "asset_folders", ["parent_id"])

    asset_columns = {column["name"] for column in sa.inspect(connection).get_columns("assets")}
    if "folder_id" not in asset_columns:
        with op.batch_alter_table("assets") as batch:
            batch.add_column(sa.Column("folder_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_assets_folder_id_asset_folders",
                "asset_folders",
                ["folder_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_index("ix_assets_folder_id", ["folder_id"])


def downgrade() -> None:
    with op.batch_alter_table("assets") as batch:
        batch.drop_index("ix_assets_folder_id")
        batch.drop_constraint("fk_assets_folder_id_asset_folders", type_="foreignkey")
        batch.drop_column("folder_id")
    op.drop_index("ix_asset_folders_created_at", table_name="asset_folders")
    op.drop_index("ix_asset_folders_parent_id", table_name="asset_folders")
    op.drop_index("ix_asset_folders_sort_order", table_name="asset_folders")
    op.drop_index("ix_asset_folders_name", table_name="asset_folders")
    op.drop_table("asset_folders")
