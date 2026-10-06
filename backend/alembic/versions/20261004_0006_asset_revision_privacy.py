"""附件版本与会话 IP。"""
from alembic import op
import sqlalchemy as sa

revision = "20261004_0006"
down_revision = "20260821_0005"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    for table in ["project_links", "project_assets", "project_album_assets", "resumes"]:
        if "translations" not in {item["name"] for item in inspector.get_columns(table)}:
            op.add_column(table, sa.Column("translations", sa.JSON(), nullable=False, server_default="{}"))
    if "version" not in {item["name"] for item in inspector.get_columns("assets")}:
        op.add_column("assets", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    if "encrypted_ip" not in {item["name"] for item in inspector.get_columns("visitor_sessions")}:
        op.add_column("visitor_sessions", sa.Column("encrypted_ip", sa.Text(), nullable=True))


def downgrade():
    for table in ["project_links", "project_assets", "project_album_assets", "resumes"]:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("translations")
    with op.batch_alter_table("visitor_sessions") as batch:
        batch.drop_column("encrypted_ip")
    with op.batch_alter_table("assets") as batch:
        batch.drop_column("version")
