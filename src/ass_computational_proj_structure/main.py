#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py —— 总控入口
====================
工作流逻辑：

  读取 config/main_config.json

  ┌─ 输出目录(output_path)下已存在 "pro" 项目目录？
  │
  ├─ 是 ──► 仅扫描 pro 目录，生成 structure.json 到 pro/docs/structure.json，结束。
  │
  └─ 否 ──► 正常流程：
            1. 拿到模板目录(templet_path)
            2. 检查模板 docs 下是否已有 structure.json
                 · 没有 -> 扫描模板目录生成 structure.json
                 · 有   -> 直接使用
            3. 依据模板 structure.json，在 output_path 下创建项目骨架
            4. 从模板目录把所有文件内容复制到刚创建的项目结构中

路径解析：配置中的相对路径(如 "../output/my_project/")均相对于本 main.py 所在目录。
"""

import sys
import json
import shutil
from pathlib import Path

# ── 让 core 包可被导入 ───────────────────────────────────────
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.directory_structure_to_jsonfile import export_structure, should_ignore
from core.jsonfile_to_directory_structure import build_from_json, detect_src_package
from core.backfill_placeholders import backfill_directory

CONFIG_PATH = ROOT / "config" / "main_config.json"


# ============================================================
# 工具函数
# ============================================================
def resolve_path(p: str) -> Path:
    """把配置里的路径解析为绝对路径。

    相对路径一律以【配置文件所在目录(config/)】为基准，
    与 core/*.py 独立运行时的解析口径保持一致。
    这样配置里的 "../output/my_project/" 会从 config/ 回到工作区根目录，
    最终定位到与 main.py 同级的 output/ 目录。
    """
    path = Path(p)
    return path if path.is_absolute() else (CONFIG_PATH.parent / path).resolve()


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"找不到主配置文件: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    pc = config.get("project_config")
    if not pc:
        raise ValueError("配置缺少 'project_config' 节")
    return pc


def remap_rel(rel: Path, old_pkg: str, new_pkg: str) -> Path:
    """把相对路径中的 src/<old_pkg>/... 改写为 src/<new_pkg>/...。"""
    parts = list(rel.parts)
    if old_pkg and new_pkg and old_pkg != new_pkg \
            and len(parts) >= 2 and parts[0] == "src" and parts[1] == old_pkg:
        parts[1] = new_pkg
        return Path(*parts)
    return rel


def copy_tree_contents(src_dir: Path, dst_dir: Path, old_pkg=None, new_pkg=None):
    """把 src_dir 内的所有文件复制到 dst_dir，保持相对结构并遵循忽略规则。
    若提供 old_pkg/new_pkg，则把 src/<old_pkg>/ 复制到 src/<new_pkg>/。"""
    copied = 0
    for src_file in src_dir.rglob("*"):
        rel = src_file.relative_to(src_dir)
        if any(should_ignore(part) for part in rel.parts):
            continue
        dst_file = dst_dir / remap_rel(rel, old_pkg, new_pkg)
        if src_file.is_dir():
            dst_file.mkdir(parents=True, exist_ok=True)
        else:
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            copied += 1
    print(f"✅ 已复制 {copied} 个文件: {src_dir} -> {dst_dir}")
    return copied


# ============================================================
# 两个分支
# ============================================================
def run_pro_branch(pro_dir: Path):
    """分支A：输出目录下已有 pro 项目，仅生成 structure.json。"""
    print(f"🔍 检测到 pro 项目目录: {pro_dir}")
    json_out = pro_dir / "docs" / "structure.json"
    export_structure(pro_dir, json_out, project_name="pro")
    print("🎯 pro 分支完成：仅生成了 structure.json。")


def run_normal_branch(pc: dict, output_path: Path):
    """分支B：正常模板复制流程。"""
    templet_path = resolve_path(pc["templet_path"])
    templet_json = resolve_path(pc["templet_structurejson_path"])
    project_name = pc.get("project_name") or templet_path.name

    if not templet_path.exists() or not templet_path.is_dir():
        raise FileNotFoundError(f"模板目录不存在: {templet_path}")

    # ── 步骤2：确保模板 structure.json 存在 ──────────────────
    if templet_json.exists():
        print(f"📄 模板 structure.json 已存在，直接使用: {templet_json}")
    else:
        print(f"📄 模板缺少 structure.json，开始扫描生成: {templet_json}")
        export_structure(templet_path, templet_json, project_name)

    # ── 步骤3：在输出目录创建项目骨架 ────────────────────────
    version = str(pc.get("version", "0.1.0"))
    target_dir = build_from_json(templet_json, output_path, version=version,
                                 default_project_name=project_name,)

    # 找出模板 src/ 下的主包目录名，复制时同样改名为 project_name
    structure_root = json.loads(templet_json.read_text(encoding="utf-8")) \
        .get("structure", {}).get("root", {})
    old_pkg = detect_src_package(structure_root)

    # ── 步骤4：复制模板内的所有文件内容到项目结构 ────────────
    copy_tree_contents(templet_path, target_dir,
                       old_pkg=old_pkg, new_pkg=project_name + "_" + version)

    # ── 步骤5：回填文件内容中的 {占位符} ─────────────────────
    backfill_directory(target_dir, project_name, version)

    print(f"🎯 正常分支完成：项目已生成在 {target_dir}")


# ============================================================
# 入口
# ============================================================
def main():
    try:
        pc = load_config()
        output_path = resolve_path(pc["output_path"])
        output_path.mkdir(parents=True, exist_ok=True)

        pro_dir = output_path / "pro"
        if pro_dir.exists() and pro_dir.is_dir():
            run_pro_branch(pro_dir)
        else:
            run_normal_branch(pc, output_path)

    except Exception as e:
        print(f"❌ 工作流异常终止: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
