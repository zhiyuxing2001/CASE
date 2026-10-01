# CASE — Clinical Archives for Student Encounters

> 中医跟诊病案数据库与跟师学习管理系统
> A TCM clinical case database and mentorship-learning management system for students.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## 这个项目解决什么

中医学生跟诊时会产生大量**手写处方、纸质病历和零散笔记**。这些材料一学期后就找不到了，更无法回答"老师治胃脘痛常用哪几味药"这类问题。

CASE 把跟诊材料变成**可检索、可溯源、可复用**的结构化病案数据库，并在其上提供跟师学习与 AI 辅助写作：

| 痛点 | CASE 的解法 |
|---|---|
| 记录散失 | 拍照即入库，结构化 + 全文检索 |
| 结构缺失 | 四诊 / 辨证 / 治法 / 方药结构化建模 |
| 学习不闭环 | 跟诊记录 → 学习心得 → 导师点评 → 病种覆盖统计 |

**核心流程**：拍一张手写处方 → macOS 本地 OCR 粗识别 → DeepSeek 视觉精修并结构化 → 人工校对 → 入库 → 检索 / 分析 / 写成心得。

---

## 项目分两个阶段

```
PREP 前置准备（3.0 pd）
  规划评审 · API Key · 采集 OCR 评测集 · 脱敏策略
        │
        ▼
阶段一 · 数据库设计（11.2 pd / 14 项任务）
  需求分析 → 概念模型 → 逻辑模型 → 检索设计 → 字典与种子数据 → 验证
  交付：SQLAlchemy 模型 + Alembic 迁移 + 种子数据 + 数据字典文档 + 测试
        │
        │  ★ 阶段门禁：DDL 可执行、迁移可回滚、检索路由经回归测试
        ▼
阶段二 · 软件开发（41.0 pd / 58 项任务）
  B1 脚手架 → B2 病案界面 → B3 OCR → B4 学习模块 → B5 AI 辅助 → B6 导出交付
  交付：可在本机日常使用的完整应用
```

**总计 76 项任务 / 55.2 人日**（专注人日；业余投入请 ×2–3 换算自然时间）

> **为什么数据库设计单独成为阶段**：中医病案的数据结构复杂度远高于普通业务系统 —— 四诊、辨证、方药、跟师关系各有内在结构，中药还存在同名异物/同物异名问题。**数据结构一旦定型，后期修改成本极高**（涉及迁移、数据清洗、界面与统计联动），因此先把数据基础做扎实。

---

## 技术选型

| 层 | 选型 |
|---|---|
| 运行形态 | **纯单机 Mac 本地工具**，仅绑定 `127.0.0.1`，不对局域网暴露 |
| 后端 | Python 3.13 + FastAPI + SQLAlchemy 2.0 + Alembic |
| 数据库 | SQLite（FTS5 `trigram` 中文全文检索 + LIKE 回退） |
| 前端 | React + TypeScript + Vite + Ant Design |
| OCR | **ocrmac**（macOS Vision，本地免费离线）+ **DeepSeek 视觉精修** |
| AI | DeepSeek `deepseek-flash`（支持图像）/ `deepseek-v4-pro`（纯文本深度推理） |

**设计原则**：本地优先 · 离线可降级 · 人工终审 · 字段可溯源 · 数据先行。

> ⚠️ 合规声明：CASE 是**学习记录工具**，不是医疗器械，**不提供诊疗建议、不做辅助诊断**。所有 AI 输出仅供学习参考。

---

## 项目文档

全部文档位于 [`docs/`](./docs/)，**文件名统一使用英文 kebab-case**。阅读顺序见 [`docs/README.md`](./docs/README.md)。

| 文档 | 内容 |
|---|---|
| [`docs/project-plan.md`](./docs/project-plan.md) | **总纲**：项目定位、两阶段划分、范围界定、技术选型、里程碑、风险、验收标准 |
| [`docs/requirements-analysis.md`](./docs/requirements-analysis.md) | **需求分析报告**（DB-01）：基于 2 份真实病案的解析，归纳数据库基本特点与基本要求 |
| [`docs/database-design.md`](./docs/database-design.md) | **数据库设计说明**（DB-02/DB-04）：28 表总体结构、与睡眠专病库的对照、关键决策 K1~K5 |
| [`docs/case-database-spec.xlsx`](./docs/case-database-spec.xlsx) | **字段级结构说明书**：28 张表 / 342 字段 / 19 组枚举附表 |
| [`docs/phase-1-database-design.md`](./docs/phase-1-database-design.md) | 阶段一设计说明；§四 中文全文检索方案仍有效，§三 DDL 已被取代 |
| [`docs/phase-2-software-development.md`](./docs/phase-2-software-development.md) | **阶段二 · 软件开发**：系统架构、模块设计、OCR 双通道流水线、离线降级 |
| [`docs/task-breakdown.md`](./docs/task-breakdown.md) | 两阶段可勾选任务清单（76 项 / 55.2 人日），含依赖与门禁 |
| [`docs/technical-validation.md`](./docs/technical-validation.md) | 立项阶段技术假设的验证过程与实测结论 |
| [`docs/commit-convention.md`](./docs/commit-convention.md) | Git 命名与提交规范（英文文件名 + 英文 Conventional Commits） |

---

## 立项阶段已验证的关键结论

1. **DeepSeek 支持图像输入**（`deepseek-flash`）→ 手写处方 OCR 无需本地训练模型，单张图成本约 0.002–0.01 元。
2. **macOS Vision 可从 Python 调用**（`ocrmac`）→ 中文识别置信度可达 1.0，且**逐行返回置信度与坐标框**，这是"只把低置信行送云端精修"的前提。
3. **SQLite FTS5 的 `trigram` 分词器对 2 字查询静默失效** → 「风热」「气虚」「血瘀」等高频中医术语会查不到且不报错，检索层**必须按查询长度路由**到 LIKE 回退。

详见 [`docs/technical-validation.md`](./docs/technical-validation.md)。

---

## 项目状态

**当前阶段：立项规划已完成（v2.0 两阶段规划），尚未开始编码。**

| 阶段 | 任务数 | 人日 | 状态 |
|---|---|---|---|
| PREP 前置准备 | 4 | 3.0 | 未开始 |
| **阶段一 · 数据库设计** | 14 | 11.2 | 未开始 |
| **阶段二 · 软件开发** | 58 | 41.0 | 未开始 |
| **合计** | **76** | **55.2** | |

---

## 开始前的准备

1. **申请 DeepSeek API Key**：到 [platform.deepseek.com](https://platform.deepseek.com/) 申请，写入 `.env`（**切勿提交到 Git**）。
2. **采集 OCR 评测集**：30–50 张真实病案/处方照片（**务必包含手写体**）。这是**唯一需要与阶段一并行**的任务，也是 OCR 成败的前提。
3. 阅读 [`docs/project-plan.md`](./docs/project-plan.md) 并确认范围与阶段划分。

---

## 开发约定

| 约定 | 说明 |
|---|---|
| **文件名** | 一律英文、小写、连字符分隔；禁用中文文件名 |
| **Commit message** | 英文 [Conventional Commits](https://www.conventionalcommits.org/)：`<type>(<scope>): <subject>` |
| **提交粒度** | 一次提交只做一件事；文档与代码分开提交 |
| **禁止提交** | `data/`（含患者隐私）、`.env`、`*.db`、真实病案照片 |

详见 [`docs/commit-convention.md`](./docs/commit-convention.md)。

---

## 开发者工具

| 工具 | 用途 |
|---|---|
| [`tools/verify_ddl.py`](./tools/verify_ddl.py) | 从阶段一文档抽取全部 SQL 并在内存库执行，作为 DDL 回归测试 |
| [`tools/ocr_smoke_test.sh`](./tools/ocr_smoke_test.sh) | macOS Vision OCR 自举验证脚本（自动建 venv、生成中文测试图并识别） |

```bash
python3 tools/verify_ddl.py        # 验证 DDL 可执行性
bash tools/ocr_smoke_test.sh       # 验证 macOS OCR 可用性
```

---

## 许可证

[MIT](./LICENSE) © 2026 StarZhi
