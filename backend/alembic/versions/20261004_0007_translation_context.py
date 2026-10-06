"""翻译上下文窗口。"""
from alembic import op
import sqlalchemy as sa

revision = "20261004_0007"
down_revision = "20261004_0006"
branch_labels = None
depends_on = None


def upgrade():
    if "max_context_chars" not in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("ai_settings")}:
        op.add_column("ai_settings", sa.Column("max_context_chars", sa.Integer(), nullable=False, server_default="32000"))


def downgrade():
    with op.batch_alter_table("ai_settings") as batch:
        batch.drop_column("max_context_chars")
