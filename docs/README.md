# CASE 文档索引

本目录包含 CASE 项目的全部规划与技术文档。**文件名一律使用英文 kebab-case**（见 [`commit-convention.md`](./commit-convention.md) §1）。

---

## 阅读顺序

| 顺序 | 文档 | 内容 | 读者 |
|---|---|---|---|
| 1 | [`project-plan.md`](./project-plan.md) | **总纲**：项目定位、两阶段划分、范围界定、技术选型、里程碑、风险、验收标准 | 所有人，先读这个 |
| 2 | [`requirements-analysis.md`](./requirements-analysis.md) | **需求分析报告**（DB-01）：基于 2 份真实病案的解析，归纳数据库基本特点与基本要求 | 阶段一执行者 |
| 3 | [`phase-1-database-design.md`](./phase-1-database-design.md) | **阶段一 · 数据库设计**：设计原则、ER 模型、34 张表 DDL、中文检索方案、字典计划 | 阶段一执行者 |
| 4 | [`phase-2-software-development.md`](./phase-2-software-development.md) | **阶段二 · 软件开发**：系统架构、模块设计、OCR 双通道流水线、离线降级、测试策略 | 阶段二执行者 |
| 5 | [`task-breakdown.md`](./task-breakdown.md) | 两阶段可勾选任务清单（76 项 / 55.2 人日），含依赖、门禁与验收点 | 执行与进度跟踪 |
| 6 | [`technical-validation.md`](./technical-validation.md) | 立项阶段技术假设的验证过程与实测结论（含两个已验证的坑） | 想了解技术风险依据 |
| 7 | [`commit-convention.md`](./commit-convention.md) | Git 命名与提交规范（英文文件名 + 英文 Conventional Commits） | 提交代码前必读 |

---

## 两阶段速查

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

---

## 关键结论速查

| 结论 | 出处 |
|---|---|
| 手写处方 OCR 无需本地训练模型 —— DeepSeek `deepseek-flash` 已支持视觉输入 | [`technical-validation.md`](./technical-validation.md) V1 |
| macOS Vision 可从 Python 调用，中文识别置信度 1.0，且返回逐行置信度与坐标框 | [`technical-validation.md`](./technical-validation.md) V2 |
| **SQLite FTS5 `trigram` 对 2 字查询静默失效**（「风热」「气虚」查不到且不报错） | [`technical-validation.md`](./technical-validation.md) V3 |
| Vision 置信度在**印刷体（0.5–1.0）与手写体（≈0.3）间清晰分层**，可直接用作路由阈值 | [`requirements-analysis.md`](./requirements-analysis.md) §6.1 |
| 药名 OCR 错误**几乎全为形近字**（黄芩→黄苓、黄柏→黄相），字典 + 相似度匹配即可自动纠正 | [`requirements-analysis.md`](./requirements-analysis.md) §6.2 |
| **HIS 医嘱表存在确定性算术不变量**（总量 = 单剂剂量 × 剂数，实测 14/14 成立），可做不依赖模型的自动校验 | [`requirements-analysis.md`](./requirements-analysis.md) §6.6 |
| 表格类单据的**行列对应关系会被 Vision 完全丢失**，必须做表格结构重建 | [`requirements-analysis.md`](./requirements-analysis.md) §6.4 |
| 就诊卡号内嵌身份证号，**必须脱敏或不存** | [`requirements-analysis.md`](./requirements-analysis.md) §4.3 |
| 双通道 OCR 优于单通道：Vision 给确定性字符与坐标，模型在其约束下纠错结构化 | [`phase-2-software-development.md`](./phase-2-software-development.md) §3.3.2 |
| 数据库设计独立成阶段的原因：数据结构定型后修改成本极高 | [`project-plan.md`](./project-plan.md) §2.2 |
| **最大风险是手写体识别率**，故阶段二 B3 第一件事是跑评测基线 | [`phase-2-software-development.md`](./phase-2-software-development.md) §5.1 |

---

## 相关目录

| 路径 | 说明 |
|---|---|
| [`../tools/verify_ddl.py`](../tools/verify_ddl.py) | 从 `phase-1-database-design.md` 抽取全部 SQL 并在内存库执行，作为 DDL 回归 |
| [`../tools/ocr_smoke_test.sh`](../tools/ocr_smoke_test.sh) | macOS Vision OCR 自举验证脚本（自动建 venv、生成中文测试图并识别） |
| `../backend/` | 阶段一与阶段二的后端代码（待创建） |
| `../frontend/` | 阶段二的前端代码（待创建） |
| `../data/` | 数据库与附件，**已被 .gitignore 忽略**（含患者隐私） |
