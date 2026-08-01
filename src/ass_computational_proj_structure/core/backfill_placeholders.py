#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backfill_placeholders.py
------------------------
信息回填模块。

在 main.py 创建完目标项目目录、并把模板文件内容复制过去之后，
本模块负责扫描生成后的项目，把文件内容里形如 ``{token}`` 的占位符
替换为真实信息（项目名、版本号、日期、所属目录等）。

典型占位符：
  {project_name}   -> 项目名（来自 main_config.json）
  {version}        -> 版本号（来自 main_config.json 的 version 字段）
  {YYYYMMRR}       -> 生成日期，格式 YYYYMMDD（如 20260701）
  {date-time}      -> 生成时间戳，格式 YYYY-MM-DD HH:MM:SS
  {parentDir}      -> 目标项目所在的父目录名
  {current_dir}    -> 目标项目根目录名

设计要点：
  - 通用替换：任意 {token} 只要在上下文映射里存在就会被替换，
    因此新增占位符只需往 build_context() 里加一条即可。
  - 只处理文本文件（按扩展名白名单 + 二进制探测），二进制文件跳过。
  - 未知占位符保持原样，并在结束时汇总提示，避免误伤业务代码里的花括号。
"""

import re
from datetime import datetime
from pathlib import Path

# 允许回填的文本文件扩展名（其余按内容探测，含 \x00 视为二进制并跳过）
TEXT_SUFFIXES = {
    ".md", ".txt", ".json", ".toml", ".cfg", ".ini", ".yaml", ".yml",
    ".py", ".rst", ".env", ".sh", ".bat", ".html", ".css", ".js", ".j2",
}

# 用户明确要求回填的重点文件（按文件名匹配，用于日志高亮，不限制其它文件）
KEY_FILES = {
    "README.md",
    "pyproject.toml",
    "CHANGELOG.md",
    "structure.json",
}

# 匹配 {token}：token 由字母/数字/下划线/连字符组成（如 date-time、project_name）
_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z0-9_\-]+)\}")

# 与源文件名前缀匹配即视为重点规范文件（如 ass-Computational项目构建规范_1.0-*.txt）
_SPEC_PREFIX = "ass-Computational项目构建规范"


def build_context(project_name: str, version: str, target_dir: Path) -> dict:
    """构造占位符 -> 真实值 的映射。

    参数
    ----
    project_name : 项目名（main_config.json 的 project_name）
    version      : 版本号（main_config.json 的 version）
    target_dir   : 已创建的目标项目根目录
    """
    now = datetime.now()
    ymd = now.strftime("%Y%m%d")               # 20260701
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")  # 2026-07-01 12:00:00
    full_name = f"{project_name}_{version}-{ymd}"

    return {
        "project_name": project_name,
        "version": version,
        "YYYYMMRR": ymd,        # 规范里的日期占位符，回填为 YYYYMMDD
        "YYYYMMDD": ymd,        # 兼容写法
        "date-time": stamp,
        "datetime": stamp,
        "date": now.strftime("%Y-%m-%d"),
        "full_name": full_name,
        "parentDir": target_dir.parent.name,   # 项目所在父目录名
        "current_dir": target_dir.name,        # 项目根目录名
    }


def _looks_binary(path: Path) -> bool:
    """粗略判断文件是否为二进制（读取前 1KB 探测 NUL 字节）。"""
    try:
        with open(path, "rb") as f:
            return b"\x00" in f.read(1024)
    except OSError:
        return True


def _is_text_file(path: Path) -> bool:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    # 无扩展名或未知扩展名时，用二进制探测兜底
    return not _looks_binary(path)


def _is_key_file(path: Path) -> bool:
    return path.name in KEY_FILES or path.name.startswith(_SPEC_PREFIX)


def fill_text(text: str, context: dict, unknown: set) -> tuple:
    """替换单段文本中的占位符，返回 (新文本, 替换次数)。
    未在 context 中的占位符保持原样并记入 unknown。"""
    count = 0

    def _repl(m: "re.Match") -> str:
        nonlocal count
        token = m.group(1)
        if token in context:
            count += 1
            return str(context[token])
        unknown.add(token)
        return m.group(0)  # 保持原样

    return _PLACEHOLDER_RE.sub(_repl, text), count


def backfill_directory(target_dir, project_name: str, version: str) -> dict:
    """扫描 target_dir 下所有文本文件并回填占位符。

    返回统计字典：{"files_changed", "replacements", "unknown_tokens"}。
    """
    target_dir = Path(target_dir)
    if not target_dir.is_dir():
        raise FileNotFoundError(f"回填目标目录不存在: {target_dir}")

    context = build_context(project_name, version, target_dir)
    print(f"🖊️  开始回填占位符: {target_dir}")
    print(f"    上下文: project_name={context['project_name']}, "
          f"version={context['version']}, date={context['YYYYMMRR']}, "
          f"full_name={context['full_name']}")

    unknown: set = set()
    files_changed = 0
    total_replacements = 0

    for path in sorted(target_dir.rglob("*")):
        if not path.is_file() or not _is_text_file(path):
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # 无法按 UTF-8 读取的文件跳过

        if "{" not in original:  # 没有占位符，快速跳过
            continue

        new_text, count = fill_text(original, context, unknown)
        if count > 0 and new_text != original:
            path.write_text(new_text, encoding="utf-8")
            files_changed += 1
            total_replacements += count
            flag = "⭐" if _is_key_file(path) else "  "
            rel = path.relative_to(target_dir)
            print(f"    {flag} 回填 {count:>2} 处: {rel}")

    print(f"✅ 回填完成：修改 {files_changed} 个文件，共替换 {total_replacements} 处占位符。")
    if unknown:
        print(f"⚠️  以下占位符未在上下文中定义，已保持原样: "
              f"{', '.join('{' + t + '}' for t in sorted(unknown))}")

    return {
        "files_changed": files_changed,
        "replacements": total_replacements,
        "unknown_tokens": sorted(unknown),
    }


# ── 独立运行入口（调试用） ──────────────────────────────────
def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="回填项目目录中的 {占位符}")
    parser.add_argument("target", help="已创建的项目根目录")
    parser.add_argument("--config", default="../config/main_config.json",
                        help="main_config.json 路径，用于读取 project_name/version")
    args = parser.parse_args()

    pc = json.loads(Path(args.config).resolve().read_text(encoding="utf-8"))["project_config"]
    backfill_directory(args.target, pc.get("project_name", "my_project"),
                       str(pc.get("version", "0.1.0")))


if __name__ == "__main__":
    main()
