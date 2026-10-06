"""更新前核对镜像内的 Python 依赖。"""
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import re
import sys


def main() -> None:
    failures = []
    if sys.version_info[:2] != (3, 12):
        failures.append(f"需要 Python 3.12，当前为 {sys.version.split()[0]}")
    for line in (Path(__file__).resolve().parents[1] / "requirements.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)(?:\[[^]]+\])?==([^\s]+)", line)
        if not match:
            failures.append(f"无法核对依赖声明：{line}")
            continue
        package, expected = match.groups()
        try:
            installed = version(package)
        except PackageNotFoundError:
            failures.append(f"缺少依赖：{package}")
            continue
        if installed != expected:
            failures.append(f"{package}：需要 {expected}，镜像内为 {installed}")
    if failures:
        raise SystemExit("运行环境与代码不匹配，尚未停止服务：\n" + "\n".join(failures))
    print("运行环境核对通过，可复用现有镜像。")


if __name__ == "__main__":
    main()
