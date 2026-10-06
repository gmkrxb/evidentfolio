"""修复多个默认简历，并由数据库保证默认标记唯一。"""
from alembic import op
import sqlalchemy as sa

revision = "20261005_0011"
down_revision = "20261005_0010"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    # 保留最近修改的默认选择，不删除任何简历或 PDF。
    connection.execute(sa.text("""
        UPDATE resumes SET is_default = 0
        WHERE is_default = 1 AND id NOT IN (
            SELECT id FROM resumes WHERE is_default = 1
            ORDER BY updated_at DESC, id DESC LIMIT 1
        )
    """))
    indexes = {item["name"] for item in sa.inspect(connection).get_indexes("resumes")}
    if "uq_resumes_single_default" not in indexes:
        op.create_index("uq_resumes_single_default", "resumes", ["is_default"],
                        unique=True, sqlite_where=sa.text("is_default = 1"))


def downgrade():
    op.drop_index("uq_resumes_single_default", table_name="resumes")
