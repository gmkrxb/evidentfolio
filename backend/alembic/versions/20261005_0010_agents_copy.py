"""补齐多智能体协作章节的默认文案，只填补空缺，不覆盖已有内容。"""
import json

from alembic import op
import sqlalchemy as sa

from app.services.poetry import with_default_poetry

revision = "20261005_0010"
down_revision = "20261005_0009"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if "site_settings" not in sa.inspect(connection).get_table_names():
        return
    row = connection.execute(sa.text("SELECT id, data FROM site_settings WHERE id = 1")).first()
    if row is None:
        return
    data = row.data
    if isinstance(data, (str, bytes)):
        try:
            data = json.loads(data or "{}")
        except ValueError:
            return
    if not isinstance(data, dict) or not data.get("person_name") and not data.get("site_name"):
        return
    updated, changed = with_default_poetry(data)
    if changed:
        connection.execute(sa.text("UPDATE site_settings SET data = :data WHERE id = 1"), {"data": json.dumps(updated, ensure_ascii=False)})


def downgrade():
    pass
