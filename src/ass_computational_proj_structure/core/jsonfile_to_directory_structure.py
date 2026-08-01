#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jsonfile_to_directory_structure.py
----------------------------------
读取 structure.json，在输出目录中重建项目骨架（目录 + 空文件）。
真实文件内容由 main.py 在随后的复制阶段填充。

解析规则（兼容规范格式与手写模板）：
  - key 以 '/' 结尾  -> 目录
  - 其它 key（非元信息）-> 文件
  - 子节点容器键：children / child / subdirectories
  - example_files 列表 -> 批量创建示例文件
  - 其余元信息键（purpose / rules / ...）一律跳过

命名规则：
  - 生成的项目根目录名 = project_name（配置文件 main_config.json）
  - src/ 下的主包目录名同样被改写为 project_name
    （即把模板里的 src/<old_package>/ 重建为 src/<project_name>/）
"""

import json
import argparse
from pathlib import Path

CONTAINER_KEYS = ("children", "child", "subdirectories")
META_KEYS = {"purpose", "rules", "description", "version", "project",
             "naming_convention", "rule", "dependency_rule"}


def detect_src_package(root: dict):
    """
    从 structure.json 的 root 节点里找出 src/ 下的主包目录名。
    返回该目录名（不含 '/'），找不到则返回 None。
    """
    src_node = root.get("src/")
    if not isinstance(src_node, dict):
        return None
    # 展开 src/ 的子节点容器（child / children / subdirectories）
    children = {}
    for ck in CONTAINER_KEYS:
        if isinstance(src_node.get(ck), dict):
            children.update(src_node[ck])
    for key in children:
        if key.endswith("/"):
            return key.rstrip("/")
    return None


def build_node(base: Path, node: dict, parent_name: str, rename: tuple):
    """
    递归在 base 下创建目录与空文件。
    rename = (old_package, new_package)：当某目录的父级为 'src' 且名字等于
    old_package 时，实际创建为 new_package。
    """
    old_pkg, new_pkg = rename
    for key, value in node.items():
        if key in CONTAINER_KEYS:                 # 子节点容器：原地展开，parent_name 不变
            build_node(base, value, parent_name, rename)
        elif key == "example_files":              # 示例文件列表
            base.mkdir(parents=True, exist_ok=True)
            for name in value:
                (base / name).touch()
        elif key in META_KEYS:                    # 纯说明字段：跳过
            continue
        elif key.endswith("/"):                   # 目录
            dirname = key.rstrip("/")
            # 把 src/ 下的主包目录改名为 project_name
            if parent_name == "src" and old_pkg and dirname == old_pkg:
                dirname = new_pkg
            sub = base / dirname
            sub.mkdir(parents=True, exist_ok=True)
            if isinstance(value, dict):
                build_node(sub, value, dirname, rename)
        else:                                     # 文件
            base.mkdir(parents=True, exist_ok=True)
            (base / key).touch()


def build_from_json(structure_json_path, output_parent, version, default_project_name=None) -> Path:
    """依据 structure.json 在 output_parent 下创建项目骨架，返回项目根目录。"""
    structure_json_path = Path(structure_json_path)
    output_parent = Path(output_parent)

    if not structure_json_path.exists():
        raise FileNotFoundError(f"structure.json 不存在: {structure_json_path}")

    data = json.loads(structure_json_path.read_text(encoding="utf-8"))
    project_name = default_project_name + "_" + version or data.get("project") or "my_project"
    root = data.get("structure", {}).get("root", data)

    # src/ 下的主包目录改名映射
    old_pkg = detect_src_package(root)
    rename = (old_pkg, project_name)

    target = output_parent / project_name
    target.mkdir(parents=True, exist_ok=True)
    build_node(target, root, parent_name="", rename=rename)

    if old_pkg and old_pkg != project_name:
        print(f"✅ 项目骨架已创建: {target} （src/{old_pkg}/ -> src/{project_name}/）")
    else:
        print(f"✅ 项目骨架已创建: {target}")
    return target


# ── 独立运行入口（调试用） ──────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="依据 structure.json 创建项目骨架")
    parser.add_argument("--config", default="../config/main_config.json")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    pc = json.loads(config_path.read_text(encoding="utf-8"))["project_config"]
    base = config_path.parent

    output_parent = (base / pc["output_path"]).resolve()
    structure_json = (base / pc["templet_structurejson_path"]).resolve()
    build_from_json(structure_json, output_parent, pc.get("project_name"))


if __name__ == "__main__":
    main()
