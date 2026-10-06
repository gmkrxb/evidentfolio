#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
TARGET_ROOT=$(CDPATH= cd -- "${1:?请指定部署目录}" && pwd -P)
CONTAINER=${2:-my-dashboard}
CONTACT_PROFILE=${3:-}
CONTACT_ARGS=(-e EVIDENTFOLIO_CONTACT_PROFILE=)
ENV_FILE=""
STOPPED=0

cleanup() {
    local result=$?
    trap - EXIT
    if [[ -n "$ENV_FILE" ]]; then rm -f -- "$ENV_FILE"; fi
    if [[ "$result" -ne 0 && "$STOPPED" -eq 1 ]]; then
        printf '\n更新失败，服务未确认恢复；修复上方错误后可重新执行同一条更新命令。\n' >&2
        docker logs --tail 60 "$CONTAINER" >&2 || true
    fi
    exit "$result"
}
trap cleanup EXIT

for tool in docker tar sha256sum mktemp; do command -v "$tool" >/dev/null; done
[[ "$SOURCE_ROOT" != "$TARGET_ROOT" ]] || { echo '请先把更新包解压到独立目录。' >&2; exit 1; }
[[ -f "$TARGET_ROOT/config.py" && -f "$TARGET_ROOT/data/portfolio.db" ]] || {
    echo '部署目录缺少 config.py 或 data/portfolio.db，未开始更新。' >&2; exit 1;
}
if [[ -n "$CONTACT_PROFILE" ]]; then
    [[ -f "$CONTACT_PROFILE" ]] || { echo '联系信息配置文件不存在，未开始更新。' >&2; exit 1; }
    CONTACT_PROFILE=$(CDPATH= cd -- "$(dirname -- "$CONTACT_PROFILE")" && printf '%s/%s' "$PWD" "$(basename -- "$CONTACT_PROFILE")")
    CONTACT_ARGS=(-v "$CONTACT_PROFILE:/update-contacts.json:ro" -e EVIDENTFOLIO_CONTACT_PROFILE=/update-contacts.json)
fi

echo '1/5 核对更新文件和现有挂载'
(cd "$SOURCE_ROOT" && sha256sum -c backend/deploy/update.sha256 >/dev/null)
check_mount() {
    local destination=$1 expected=$2 actual
    actual=$(docker inspect --format "{{range .Mounts}}{{if eq .Destination \"$destination\"}}{{if eq .Type \"bind\"}}{{.Source}}{{end}}{{end}}{{end}}" "$CONTAINER")
    [[ "$actual" == "$expected" ]] || {
        printf '挂载不匹配：%s 需要对应 %s，实际为 %s。未停止服务。\n' "$destination" "$expected" "$actual" >&2
        exit 1
    }
}
check_mount /app/backend "$TARGET_ROOT/backend"
check_mount /usr/share/nginx/html "$TARGET_ROOT/frontend"
check_mount /app/data "$TARGET_ROOT/data"
check_mount /app/uploads "$TARGET_ROOT/uploads"
check_mount /app/config/config.py "$TARGET_ROOT/config.py"
IMAGE=$(docker inspect --format '{{.Image}}' "$CONTAINER")
docker run --rm --network none --entrypoint /bin/sh \
    -v "$SOURCE_ROOT/backend:/update:ro" "${CONTACT_ARGS[@]}" "$IMAGE" -ec '
        python /update/deploy/check_runtime.py
        if [ -n "$EVIDENTFOLIO_CONTACT_PROFILE" ]; then
            python /update/deploy/configure_contacts.py --check "$EVIDENTFOLIO_CONTACT_PROFILE"
        fi
    '

# 继承原容器环境，临时文件只允许当前用户读取。
ENV_FILE=$(mktemp)
chmod 600 "$ENV_FILE"
docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$CONTAINER" > "$ENV_FILE"

echo '2/5 停止服务并覆盖前后端代码'
docker stop --time 30 "$CONTAINER"
STOPPED=1
# 仅复制清单中的文件，保留旧静态资源供已打开的页面使用。
(cd "$SOURCE_ROOT" && cut -c 67- backend/deploy/update.sha256 | tar -cf - -T -) | tar -xf - -C "$TARGET_ROOT"

echo '3/5 使用原镜像迁移数据库（不备份）'
docker run --rm --network none --volumes-from "$CONTAINER" \
    --env-file "$ENV_FILE" "${CONTACT_ARGS[@]}" --user portfolio --workdir /app/backend \
    --entrypoint /bin/sh "$IMAGE" -ec '
        python -m app.startup preflight --skip-backup
        python -m alembic -c alembic.ini upgrade head
        python -m app.startup postflight
        if [ -n "$EVIDENTFOLIO_CONTACT_PROFILE" ]; then
            python -m deploy.configure_contacts "$EVIDENTFOLIO_CONTACT_PROFILE"
        fi
    '

echo '4/5 启动原容器'
docker start "$CONTAINER"

echo '5/5 等待健康检查并核对数据库版本'
for ((attempt=0; attempt<60; attempt++)); do
    if docker exec "$CONTAINER" curl -fsS http://127.0.0.1/api/health >/dev/null 2>&1; then
        docker exec --user portfolio --workdir /app/backend "$CONTAINER" python -m app.startup postflight
        STOPPED=0
        echo '更新完成：前后端已更新，数据库迁移成功，服务健康检查通过。'
        exit 0
    fi
    sleep 2
done
echo '服务未在 120 秒内通过健康检查。' >&2
exit 1
