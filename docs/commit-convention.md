# Git 提交规范

> 适用范围：CASE 仓库的全部提交（本地与 GitHub 推送）。
> **两条硬性要求：文件名一律英文；Commit message 一律英文 Conventional Commits。**

---

## 一、文件与目录命名

### 1.1 总规则

| 规则 | 说明 |
|---|---|
| **一律使用英文** | 禁止中文文件名、禁止拼音 |
| **不使用空格** | 用连字符 `-` 或下划线 `_` 分隔 |
| **全小写** | 仅前端组件例外（见下表） |
| **语义明确** | 名称说明内容，避免 `file1.md`、`temp.py`、`新建文档.md` |

### 1.2 按类型约定

| 类型 | 风格 | 示例 |
|---|---|---|
| Markdown 文档 | kebab-case | `phase-1-database-design.md`、`commit-convention.md` |
| Python 模块/脚本 | snake_case | `verify_ddl.py`、`ocr_pipeline.py` |
| 目录 | kebab-case 或单数名词 | `docs/`、`backend/`、`frontend/`、`adapters/` |
| 前端 React 组件 | PascalCase | `CaseForm.tsx`、`OcrReviewPanel.tsx` |
| 前端其它 TS 文件 | camelCase | `caseApi.ts`、`useDebounce.ts` |
| 数据库表 / 字段 | snake_case | `prescription_items`、`herb_name_norm` |
| 配置文件 | kebab-case | `commit-convention.md`、`.env.example`、`run.sh` |

### 1.3 禁止命名

- ❌ `00-项目规划.md` —— 中文名
- ❌ `phase 1.md` —— 含空格
- ❌ `Phase1.md` —— 文档不应使用 PascalCase
- ❌ `文档.md`、`说明.txt` —— 中文且语义模糊
- ✅ `phase-1-database-design.md`

> 已按此规范整理：`docs/` 下全部文档均为英文 kebab-case 命名。

---

## 二、Commit Message 规范

采用 [Conventional Commits](https://www.conventionalcommits.org/) **英文书写**。

### 2.1 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

- **`type`**：必填，见 §2.2
- **`scope`**：可选，见 §2.3
- **`subject`**：必填，英文祈使句
- **`body`**：可选，说明 **what** 与 **why**
- **`footer`**：可选，关联 issue 或声明破坏性变更

### 2.2 允许的 type

| type | 用途 |
|---|---|
| `feat` | 新增功能 |
| `fix` | 修复缺陷 |
| `docs` | 仅文档变更 |
| `style` | 格式调整（不影响逻辑，如空白、分号） |
| `refactor` | 重构（既不新增功能也不修缺陷） |
| `perf` | 性能优化 |
| `test` | 新增或修改测试 |
| `build` | 构建系统或依赖变更 |
| `ci` | CI 配置变更 |
| `chore` | 杂项（不改动 src 或 test） |
| `revert` | 回滚提交 |

### 2.3 本项目建议的 scope

| scope | 对应范围 |
|---|---|
| `db` | 数据库设计、模型、迁移、种子数据 |
| `api` | 后端 FastAPI 路由与服务 |
| `ocr` | OCR 流水线 |
| `ai` | DeepSeek 集成与提示词 |
| `web` | 前端界面 |
| `learning` | 跟师学习模块 |
| `export` | 导出与备份 |
| `docs` | 文档 |
| `deps` | 依赖升级 |
| `repo` | 仓库级配置（.gitignore、run.sh 等） |

### 2.4 书写规则

| 规则 | 正例 | 反例 |
|---|---|---|
| **英文书写** | `feat(ocr): add vision adapter` | `feat(ocr): 增加视觉适配器` |
| **祈使句、现在时** | `add`, `fix`, `remove` | `added`, `adds`, `fixing` |
| **首字母小写**（subject） | `add case search` | `Add case search` |
| **结尾不加句号** | `fix fts5 trigram query` | `fix fts5 trigram query.` |
| **长度 ≤ 72 字符** | 简洁 | 一句话塞满 \
| **body 与 subject 空一行** | 见示例 | 紧贴 |

### 2.5 示例

**基础提交**

```
docs: add project plan with two-phase design

Split the plan into database design and software development
phases, with an explicit gate between them.
```

```
feat(db): add SQLAlchemy models for case archives
```

```
fix(db): route short queries to LIKE fallback

FTS5 trigram tokenizer silently returns an empty set for queries
shorter than three characters, so common two-character TCM terms
such as "风热" and "气虚" never matched. Route queries by length:
>= 3 chars to FTS5, otherwise to LIKE.

Refs: #R4
```

```
refactor(ocr): extract vision adapter behind an interface

Keeps macOS Vision and DeepSeek behind adapters/ so offline
degradation and unit-test mocking only touch one layer.
```

**破坏性变更**

```
feat(db)!: rename four_diagnoses to case_examinations

BREAKING CHANGE: the table was renamed and its columns
restructured; run `alembic upgrade head` to migrate.
```

**回滚**

```
revert: feat(ocr): add vision adapter

This reverts commit 1a2b3c4.
```

### 2.6 反例对照

| ❌ 错误 | 问题 | ✅ 正确 |
|---|---|---|
| `更新文档` | 中文 | `docs: update README` |
| `fix bug` | scope 与描述不具体 | `fix(web): prevent duplicate case submit` |
| `feat: Add OCR.` | 首字母大写 + 句号 | `feat(ocr): add ocr pipeline` |
| `WIP` | 无意义 | `feat(api): add case list endpoint` |
| `修改了一下数据库` | 中文 + 模糊 | `refactor(db): normalize herb alias table` |

---

## 三、提交粒度

- **一次提交只做一件事** —— 便于 `git bisect` 与回滚。
- 文档变更与代码变更**分开提交**。
- 依赖升级单独提交（`build(deps): ...`）。
- 每个 `DB-*` / `DEV-*` 任务完成时提交一次，subject 可引用任务编号：

```
feat(db): implement FTS5 virtual table and sync triggers

Task: DB-08
```

---

## 四、禁止提交的内容

`.gitignore` 已覆盖，但仍需自查：

| 禁止项 | 原因 |
|---|---|
| `data/` 下任何内容 | **含患者隐私病案与原始处方图片** |
| `.env` | 含 `DEEPSEEK_API_KEY` |
| `*.db` / `*.sqlite` | 数据库文件，体积大且含隐私 |
| `.venv/`、`node_modules/` | 体积大，可由锁文件还原 |
| 真实病案照片 / 评测集原图 | **隐私**；评测集只提交脱敏后的样例与标注脚本 |

> ⚠️ **一旦隐私数据被推送到 GitHub，仅靠 `git rm` 无法真正删除**（历史记录仍在）。若不慎提交，必须立即：撤销 API Key → 用 `git filter-repo` 重写历史 → 强制推送。**推送前务必先 `git status` 检查。**

---

## 五、可选的工具化约束

阶段二 B1 完成后可加入（非必须）：

| 工具 | 作用 |
|---|---|
| `commitlint` + `husky` | 提交时校验 message 是否符合本规范 |
| `pre-commit` | 提交前跑格式化与敏感文件检查 |
| `.gitmessage` 模板 | `git config commit.template .gitmessage` 提供填写提示 |

建议在 `frontend/package.json` 加入：

```json
{
  "commitlint": {
    "extends": ["@commitlint/config-conventional"]
  }
}
```

---

## 六、当前仓库的提交约定

本项目规划阶段的提交示例（已按本规范执行）：

```
chore(repo): add gitignore and validation tooling
docs: add CASE project plan and two-phase design documentation
```

- 分支策略：单机个人项目，**主干开发**（`main`），无需 PR 流程。
- 推送前自查：`git status` → 确认无 `data/`、`.env`、`*.db` → `git push`
