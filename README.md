# ass-Computational_proj-structure

> **目录结构即规范** —— 基于 `structure.json` 描述的项目脚手架生成工具。

ass-Computational_proj-structure 用一份 `structure.json` 定义目标项目的目录骨架与每个节点的职责（`purpose` / `rules`），
然后在任意输出目录中自动**重建目录骨架、填充模板文件内容、回填项目名/版本/日期等占位符**，
从而保证每一个新项目都遵循统一的项目结构与整洁架构规范。

---

## 核心特性

- **结构即规范**：目录骨架完全由 `structure.json` 声明，每个节点可携带 `purpose` / `rules` 说明，兼具"结构"与"规范"双重作用。
- **双向转换**：
  - 目录 → `structure.json`（`directory_structure_to_jsonfile.py`）
  - `structure.json` → 目录骨架（`jsonfile_to_directory_structure.py`）
- **模板复制**：从模板目录把真实文件内容复制进新项目骨架，保留相对结构。
- **占位符回填**：自动替换 `{project_name}`、`{version}`、`{date}`、`{parentDir}` 等 `{token}` 占位符。
- **主包重命名**：生成时把模板里的 `src/<old_pkg>/` 自动改名为 `src/<project_name>_<version>/`。
- **双分支工作流**：输出目录下存在 `pro/` 时进入"仅重扫结构"分支，适合迭代维护已有项目。

---

## 工作流

```
读取 config/main_config.json

        ┌─ 输出目录(output_path)下已存在 "pro" 项目目录？
        │
        ├─ 是 ──► 仅扫描 pro 目录，生成 pro/docs/structure.json，结束。
        │
        └─ 否 ──► 正常流程：
                  1. 拿到模板目录(templet_path)
                  2. 检查模板 docs 下是否已有 structure.json
                       · 没有 → 扫描模板目录生成 structure.json
                       · 有   → 直接使用
                  3. 依据模板 structure.json，在 output_path 下创建项目骨架
                  4. 从模板目录把所有文件内容复制到新项目结构
                  5. 回填文件内容中的 {占位符}
```

---

## 环境要求

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip

> 说明：`main.py` 本身只依赖 Python 标准库即可独立运行；`loguru` 为 `pyproject.toml` 中声明的依赖，供后续扩展使用。

---

## 安装

```bash
git clone <repo-url> ass-Computational_proj-structure
cd ass-Computational_proj-structure

# 推荐：uv
uv sync

# 或使用 pip
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## 快速开始

### 1. 修改主配置

编辑 `src/ass_computational_proj_structure/config/main_config.json`：

```json
{
  "project_config": {
    "project_name": "TeamCollaborationPlatform",
    "version": "0.1.0",
    "output_path": "/path/to/output",
    "templet_path": "../resources/templates/my_project",
    "templet_structurejson_path": "../resources/templates/my_project/docs/structure.json"
  }
}
```

### 2. 运行

```bash
uv run python src/ass_computational_proj_structure/main.py
# 或直接使用系统 Python
python3 src/ass_computational_proj_structure/main.py
```

运行成功后，目标项目将生成在 `output_path/<project_name>_<version>/` 下，
其 `src/` 主包被改名为 `<project_name>_<version>`，所有 `{占位符}` 被替换为真实值。

---

## 配置说明（main_config.json）

| 字段 | 含义 | 示例 |
| --- | --- | --- |
| `project_name` | 项目名，将作为项目根目录名与 src 主包名 | `TeamCollaborationPlatform` |
| `version` | 版本号，参与目录名（`<name>_<version>`）与占位符回填 | `0.1.0` |
| `output_path` | 项目生成位置。相对路径以 `config/` 目录为基准 | `.` 或 `/abs/path` |
| `templet_path` | 模板目录，相对 `config/` 目录 | `../resources/templates/my_project` |
| `templet_structurejson_path` | 模板对应的 structure.json 路径 | `../resources/templates/my_project/docs/structure.json` |

---

## 目录结构

```
ass-Computational_proj-structure/
├── pyproject.toml                      # 项目元数据与构建配置（src 布局）
├── README.md / CHANGELOG.md / SUPPORT.md / LICENSE.txt
├── docs/
│   ├── structure.json                  # 工具自身的目录结构规范
│   └── ass-Computational项目构建规范_1.0-20260701.txt
├── scripts/
│   ├── ci/                             # CI/CD 辅助脚本（预留）
│   ├── deployment/                     # 部署脚本（预留）
│   └── development/                    # 开发辅助脚本（预留）
└── src/
    └── ass_computational_proj_structure/   # 工具主包
        ├── main.py                     # 总控入口，编排完整工作流
        ├── config/
        │   └── main_config.json        # 主配置
        ├── core/
        │   ├── directory_structure_to_jsonfile.py   # 目录 → structure.json
        │   ├── jsonfile_to_directory_structure.py   # structure.json → 目录骨架
        │   └── backfill_placeholders.py             # {占位符} 信息回填
        └── resources/
            └── templates/
                └── my_project/         # 项目模板（含模板 structure.json）
```

---

## 核心模块

| 模块 | 职责 |
| --- | --- |
| `main.py` | 总控入口：读取配置 → 判断 pro/正常分支 → 生成骨架 → 复制文件 → 回填占位符。各路径解析以 `config/` 目录为基准。 |
| `core/directory_structure_to_jsonfile.py` | 递归扫描真实目录，导出符合规范的 `structure.json`。自动忽略 `.git`、`__pycache__`、`.venv`、`*.pyc` 等目录/产物。 |
| `core/jsonfile_to_directory_structure.py` | 解析 `structure.json`（兼容 `children` / `child` / `subdirectories` 等容器键），重建目录骨架与空文件，并完成 `src/<old_pkg>` → `src/<project_name>` 的改名。 |
| `core/backfill_placeholders.py` | 扫描生成后的项目，把文本文件中的 `{token}` 替换为真实信息；只处理文本文件，未知占位符保持原样并汇总提示。 |

三个 `core/` 模块均支持独立运行调试（`python core/<模块>.py --config ...`），入口默认读取 `../config/main_config.json`。

---

## 占位符说明

| 占位符 | 含义 | 示例 |
| --- | --- | --- |
| `{project_name}` | 项目名（来自配置） | `TeamCollaborationPlatform` |
| `{version}` | 版本号 | `0.1.0` |
| `{YYYYMMRR}` / `{YYYYMMDD}` | 生成日期 | `20260801` |
| `{date}` | 生成日期（`YYYY-MM-DD`） | `2026-08-01` |
| `{date-time}` / `{datetime}` | 生成时间戳 | `2026-08-01 10:30:00` |
| `{full_name}` | 完整标识 | `TeamCollaborationPlatform_0.1.0-20260801` |
| `{parentDir}` | 项目所在父目录名 | `workspace` |
| `{current_dir}` | 项目根目录名 | `TeamCollaborationPlatform_0.1.0` |

> 新增占位符只需在 `backfill_placeholders.py` 的 `build_context()` 中追加一条映射即可生效。

---

## 模板与整洁架构规范

内置模板 `resources/templates/my_project/` 提供了一套基于**整洁架构**的项目骨架：

- **分层依赖方向**：`api / workflows ➡ services ➡ core（domain）`，依赖只能由外向内。
- **core 保持纯净**：领域层不依赖任何外部框架，禁止反向导入 `api` / `services` / `infrastructure`。
- **resources 资源**：作为包内资源（`static` / `templates` / `AIprompts`），推荐通过 `importlib.resources` 或基于 `__file__` 的相对路径访问。
- **命名约定**：目录小写复数、文件 `snake_case`、类 `PascalCase`、根目录文档全大写（`README.md` 等）。

完整的目录职责与规则以模板 `docs/structure.json` 为准。

---

## 常见问题

**Q：执行 `uv sync` 报 `ModuleNotFoundError: No module named 'setuptools.backends'`**

A：`pyproject.toml` 的构建后端被误写为不存在的 `setuptools.backends.legacy:build`，应改为标准后端：

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta:__legacy__"
```

（注意：`resources/templates/my_project/pyproject.toml` 模板中同样存在此写法，新生成的项目若需要 `uv sync`，请一并修正。）

**Q：回填时某些 `{占位符}` 没有被替换？**

A：只有出现在 `backfill_placeholders.py` 的 `build_context()` 上下文中的占位符才会被替换；未知占位符会保持原样并在结束时打印提示，避免误伤业务代码中的花括号。

---

## 许可证与支持

- 许可证：[MIT](LICENSE.txt)（Copyright (c) 2026 apyyc）
- 问题反馈与支持：见 [SUPPORT.md](SUPPORT.md)
- 更新记录：见 [CHANGELOG.md](CHANGELOG.md)
