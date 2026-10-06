"""资源访问方式：可下载（默认）或仅可查看（加密传输、禁止下载）。"""

from alembic import op
import sqlalchemy as sa


revision = "20261005_0012"
down_revision = "20261005_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "assets" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("assets")}
    if "access_mode" not in columns:
        with op.batch_alter_table("assets") as batch:
            batch.add_column(
                sa.Column("access_mode", sa.String(length=16), nullable=False, server_default="download")
            )


def downgrade() -> None:
    with op.batch_alter_table("assets") as batch:
        batch.drop_column("access_mode")
