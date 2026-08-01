#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
directory_structure_to_jsonfile.py
----------------------------------
扫描真实目录，生成符合规范格式的 structure.json。

输出格式（与模板规范保持一致）：
  - 目录键以 '/' 结尾，值为 { "purpose": "", "rules": "", "children": {...} }（无子项则省略 children）
  - 文件键不带 '/'，值为 { "purpose": "", "rules": "" }
  - "purpose" 与 "rules" 均留空，供人工或 LLM 后续补充说明
"""

import json
import argparse
from pathlib import Path

# 仅忽略真正的“垃圾/无关”目录
DEFAULT_IGNORE = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    ".idea", ".vscode", "dist", "build", ".DS_Store",
}


def should_ignore(name: str) -> bool:
    """判断名称是否需忽略（含 .pyc 等编译产物）。"""
    return name in DEFAULT_IGNORE or name.endswith((".pyc", ".pyo"))


def scan_directory(root: Path) -> dict:
    """递归扫描目录，返回规范格式的嵌套字典。"""
    node = {}
    items = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name))
    for item in items:
        if should_ignore(item.name):
            continue
        if item.is_dir():
            entry = {"purpose": "", "rules": ""}
            children = scan_directory(item)
            if children:
                entry["children"] = children
            node[item.name + "/"] = entry
        else:
            node[item.name] = {"purpose": "", "rules": ""}
    return node


def export_structure(source_dir, json_output, project_name) -> Path:
    """扫描 source_dir，生成 structure.json 到 json_output。"""
    source_dir = Path(source_dir)
    json_output = Path(json_output)

    if not source_dir.is_dir():
        raise FileNotFoundError(f"待扫描目录不存在: {source_dir}")

    data = {
        "project": project_name,
        "version": "1.0.0",
        "description": "",
        "structure": {"root": scan_directory(source_dir)},
        "naming_convention": {
            "directories": "snake_case",
            "files": "snake_case",
            "classes": "PascalCase",
        },
    }

    json_output.parent.mkdir(parents=True, exist_ok=True)
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ 结构描述已导出: {json_output}")
    return json_output


# ── 独立运行入口（调试用） ──────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="导出目录结构为 structure.json")
    parser.add_argument("--config", default="../config/main_config.json")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    pc = json.loads(config_path.read_text(encoding="utf-8"))["project_config"]
    base = config_path.parent

    templet = (base / pc["templet_path"]).resolve()
    json_out = (base / pc["templet_structurejson_path"]).resolve()
    export_structure(templet, json_out, pc.get("project_name", templet.name))


if __name__ == "__main__":
    main()
