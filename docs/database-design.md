# CASE 数据库设计说明

> 阶段一 · 任务 `DB-02` 概念模型 + `DB-04` 逻辑模型
> CASE — Clinical Archives for Student Encounters

| 项 | 内容 |
|---|---|
| 版本 | v2.0（按评审意见简化） |
| 字段级规范 | [`case-database-spec.xlsx`](./case-database-spec.xlsx)（**21 张表 / 247 字段 / 17 组枚举**） |
| 生成方式 | [`tools/build_db_spec.py`](../tools/build_db_spec.py) —— 表定义即单一数据源，可重复生成 |
| 设计依据 | 睡眠专病数据库结构说明书（XBB23059）· 2 份真实病案 · [`requirements-analysis.md`](./requirements-analysis.md) · 评审意见 |
| 状态 | 待评审 |

---

## 一、设计依据与核心原则

本设计综合四份输入：

| 来源 | 提供什么 |
|---|---|
| **睡眠专病数据库结构说明书**（11 张表） | **结构与约定范式**：命名法、字段说明格式、`father_id` 病程链、JSON 子结构、TINYINT 枚举附表 |
| **2 份真实病案**（手写教学表单 + HIS 导出） | **真实字段需求**：辨证分析栏、治法栏、跨专科就诊、多诊断并存 |
| [`requirements-analysis.md`](./requirements-analysis.md) | **设计约束与决策**：本地优先、离线降级、人工终审、字段溯源、隐私保护 |
| **评审意见（v2.0 核心修订）** | **简化原则**：跟师学习不需要十分细致的信息 |

### 1.1 核心原则：结构化只服务于检索与分析

> 过于细致的字段虽有助于结构化记录与规范，但**形成病案时会导致大量冗余**。
> **病案记录的自由度和灵活性比病历更高。**

这条原则限定了"什么该结构化"：

| 结构化（保留） | 理由 |
|---|---|
| 舌质 · 舌苔 · 脉象 | 舌象与脉象的频次统计，是中医分析的经典需求 |
| 中医病名 · 证型（+ 证型字典外键） | 证型频次统计与检索 |
| 治法 · 方剂名 | 按治法与方剂检索 |
| 处方药味明细 | 药物频次与剂量分析，是本库的核心分析价值 |
| 病程链 `father_id` | 取回整个病程 |
| 就诊元数据（日期/老师/科室/节气） | 按时间、按老师聚合 |

| 自由文本（不结构化） | 理由 |
|---|---|
| 现病史 | 叙述性内容，拆成时间点/诱发因素/伴随症状等子字段是重复劳动 |
| 既往史 · 个人史及婚育史 · 过敏史 | 分表分字段记录的价值低于其录入成本 |
| 体格检查 · 辅助检查 | 格式高度多变，结构化收益低 |
| 西医诊断 | 多条诊断并存，用分隔符文本即可 |

**评判标准**：一个字段若不能支撑某条具体的检索或统计，就不该单独成列——否则学生要写一遍叙述、再填一遍字段。

---

## 二、总体结构

**21 张表，分七组**：

| 分组 | 表数 | 表 |
|---|---|---|
| 一、主数据 | 3 | `info_patient` · `info_record` · `mentor` |
| 二、病案主体 | 1 | `case_narrative` |
| 三、诊断与治疗 | 3 | `diagnosis` · `treatment` · `prescription_item` |
| 四、字典 | 5 | `dict_herb` · `dict_herb_alias` · `dict_syndrome` · `dict_formula` · `dict_term` |
| 五、跟师学习 | 3 | `learning_note` · `mentor_comment` · `note_record_link` |
| 六、来源与溯源 | 4 | `source_document` · `attachment` · `ocr_job` · `ocr_field_confidence` |
| 七、系统 | 2 | `audit_log` · `app_setting` |

### 2.1 实体关系

```
        mentor ──────────┐
            │            │ (带教)
            ▼            ▼
   info_patient ──< info_record >── source_document ──< attachment ──< ocr_job ──< ocr_field_confidence
                        │  ▲
                        │  └── father_id 自指（初诊自指，复诊指向初诊）
                        │
        ┌───────────────┼───────────────┬──────────────────┐
        ▼               ▼               ▼                  ▼
  case_narrative    diagnosis       treatment        note_record_link
  （主诉/现病史/        （中医病名/       （治法/方剂名/          │
    既往史/个人史/       证型/西医诊断/     付数/煎煮法/          ▼
    过敏史/舌脉/         辨证分析）        用法/医嘱）      learning_note
    四诊/体格检查/            │                │              │
    辅助检查）               ▼                ▼              ▼
                        dict_syndrome   prescription_item   mentor_comment
                                              │
                                              ▼
                            dict_herb ──< dict_herb_alias
                                 ▲
                                 │ parent_herb_id 自指（基原 ← 炮制品）
                            dict_formula · dict_term

   系统线：audit_log（全表字段级留痕）· app_setting
```

### 2.2 数据分层

| 层 | 载体 | 用途 |
|---|---|---|
| **文本层** | `case_narrative` 的自由文本栏、`diagnosis` / `treatment` 的文本栏 | 学生按习惯书写，不强制拆分 |
| **统计层** | 舌脉三列、证型、药味明细、字典外键 | 归一化、可索引，供检索与频次分析 |
| **保真层** | 各表 `raw_ocr_text` | OCR 原文只写不改，用于溯源与回看 |
| **溯源层** | `source_document` → `attachment` → `ocr_job` → `ocr_field_confidence` | 每个字段可追回来源图片与置信度 |

---

## 三、v2.0 简化清单（本次核心修订）

### 3.1 合并与删除

**7 张表被移除，1 张表重构**（28 → 21 张）：

| 原表 | 处置 |
|---|---|
| `complaint_and_present_illness` | **重构为 `case_narrative`**，现病史取消 `Array[Object]` 拆解 |
| `chronic_diseases`（慢性非传染病史） | 并入 `case_narrative.past_history` 自由文本 |
| `communicable_diseases_related`（传染病相关史） | 并入 `case_narrative.past_history` |
| `personal_history`（个人史） | 并入 `case_narrative.personal_history` |
| `menorrhea_and_obstetric_history`（月经及婚育史） | 并入 `case_narrative.personal_history` |
| `other_history`（手术/外伤/输血/过敏/家族史） | 手术外伤输血并入 `past_history`，过敏史单列 `allergy_history` |
| `hospital_exam`（检查记录） | 体格检查并入 `physical_exam`，辅助检查并入 `auxiliary_exam` |
| `diagnosis_item`（诊断明细） | **删除**。证型改用 `syndrome`（文本）+ `syndrome_id`（可选字典外键） |

### 3.2 同步取消的其他冗余

| 项 | 原设计 | 现在 |
|---|---|---|
| 治疗记录表的 JSON 副本 | `formula_json` 存完整处方 JSON，`prescription_item` 再存一份 | **删除 JSON 副本**，只保留 `prescription_item` + `raw_ocr_text` |
| 诊断的 JSON 数组 | `disorders` / `patterns` 两个 JSON 列 | 改为 `tcm_disease` / `syndrome` 文本列 |
| 是否代煎 | 独立布尔字段 `is_decocted` | 直接写进 `decoction` 文本（"机械煎药（含2袋）"） |
| 中医/西医治疗、中成药、调护 | 4 个独立字段 | 合并为 `other_treatment` + `advice` |
| HIS 医嘱细节 | `group_no`、`spec`、`started_at`、`prescribed_by` | **删除**（病案不需要到这一级） |
| 病史陈述者 | `complainer` 布尔字段 | **删除**（手写表单无此栏） |
| 主诉是否继承 | `chief_complaint_inherited` 布尔字段 | **删除**，复诊主诉直接留空或写"服药后复诊" |
| 婚姻状况枚举 | 附表 A4 | **删除**（婚育史已并入自由文本） |

### 3.3 同时补上的一个缺失

| 项 | 说明 |
|---|---|
| **`treatment.treatment_principle`（治法）** | 真实样本的手写教学表单设有独立「治法」栏，而 v1.0 漏掉了这个字段。本次补上——它是"病—证—法—方—药"链条中"法"的一环 |

### 3.4 简化效果

| 指标 | v1.0 | v2.0 | 变化 |
|---|---|---|---|
| 表数 | 28 | **21** | −7 |
| 字段数 | 342 | **247** | −95 |
| 枚举组数 | 19 | **17** | −2 |
| JSON 列 | 15 | **1** | −14（仅 `ocr_job.vision_json` 保留，承载 OCR 坐标） |

---

## 四、与睡眠专病数据库的对照

### 4.1 直接采纳（9 项）

| # | 采纳内容 | 说明 |
|---|---|---|
| 1 | **说明书五列格式** | 字段名称 / 中文释义 / 数据类型 / 键描述 / 数据说明与数据约束 |
| 2 | **表命名法** | 小写 snake_case 英文 + 中文释义 |
| 3 | **主键策略** | 主数据 `TEXT` ULID，业务子表 `INTEGER AUTOINCREMENT` |
| 4 | **`father_id` 单字段病程链** | 初诊指向自身，复诊指向初诊。取整个病程只需 `WHERE father_id = ?`。**优于本项目原计划的双字段方案** |
| 5 | **就诊子表挂载方式** | 临床子表以 `(record_id, patient_id)` 双键关联就诊记录 |
| 6 | **枚举用 `UNSIGNED TINYINT` + 附表** | 17 组枚举集中登记在「附表 枚举字典」工作表 |
| 7 | **约束写在说明列** | 必填/选填、默认值、取值范围、单位、自动计算规则显式写明 |
| 8 | **审计时间字段** | 每表 `created_at` / `updated_at` |
| 9 | **软删除** | 各主表 `is_deleted` |

### 4.2 保留的中医特色字段

`就诊节气 solar_terms`（二十四节气编码）· `舌质` · `舌苔` · `切诊` · `中医病名` · `中医证型` · `辨证分析` · `治法` · `方剂名` · `付数` · `煎煮法`

另采纳：**主诉 ≤ 20 Unicode 字符**（中医主诉书写规范）、**国标编码**（GB/T 2659-2022 国籍、GB/T 3304-1991 民族）。

### 4.3 对睡眠库的调整（4 项）

| # | 调整 | 理由 |
|---|---|---|
| 1 | **处方药味拆为 `prescription_item` 关系表** | 睡眠库将药味存于 `formula` JSON。CASE 的核心价值是回答"老师治某病常用哪几味药"，需要药物频次统计与药材字典归一。**注意：这与 v2.0 的简化原则不冲突——处方本来就是一串药味，按行记录是数据的本来形态，而非冗余** |
| 2 | **患者表隐私改造** | `patient_id`（ULID）为关联主键；`id_no` 独立可缺省；**不存储内嵌身份证的 HIS 就诊卡号明文** |
| 3 | **就诊表扩充** | 增加 `mentor_id`（带教老师）、`department`（就诊科室）、`visit_type`。真实样本显示**就诊科室 ≠ 疾病所属专科** |
| 4 | **病史类大幅简化** | 睡眠库是**专病研究库**，需要把慢病指标拆到变量级以供统计分析；CASE 是**教学病案库**，病史只需可读可查。故 6 张病史表合并为 1 张自由文本表（见 §三） |

> **这是本次设计最重要的一处判断**：睡眠库的病史细分不是错，而是**服务于不同的目的**。研究库要的是可统计的变量，教学库要的是书写自由度。照搬会在 CASE 中产生大量无人填写的字段。

### 4.4 CASE 新增（15 张表）

> 勾稽：沿用/重构自睡眠库 **5 张**（`info_patient` · `info_record` · `case_narrative` · `diagnosis` · `treatment`）+ 由睡眠库 JSON 拆出 **1 张**（`prescription_item`）+ 本节新增 **15 张** = **21 张**

| 分组 | 表 | 为什么睡眠库没有 |
|---|---|---|
| 字典（5） | `dict_herb` · `dict_herb_alias` · `dict_syndrome` · `dict_formula` · `dict_term` | 睡眠库是纯录入研究库，无 OCR 与归一需求；CASE 需字典做**药名归一**与**形近字纠错** |
| 师承（4） | `mentor` · `learning_note` · `mentor_comment` · `note_record_link` | CASE 是**跟师学习系统**，教学元数据是核心 |
| 溯源（4） | `source_document` · `attachment` · `ocr_job` · `ocr_field_confidence` | CASE 需从扫描件入库，必须回答"这个字段来自哪张图的哪一行" |
| 系统（2） | `audit_log` · `app_setting` | 学习记录可信性依赖不可抵赖的修改历史 |

---

## 五、关键设计决策

| # | 决策 | 选择 | 理由 |
|---|---|---|---|
| **K1** | 病程链字段 | **`father_id` 单字段，初诊自指** | 取代原"`parent_case_id` + 冗余 `root_case_id`"双字段方案。单字段即可同时表达链式关系与 O(1) 病程聚合。约束：初诊 `father_id = record_id`；复诊 `father_id = 初诊 record_id` |
| **K2** | 结构化边界 | **仅保留支撑检索与统计的字段，其余自由文本** | v2.0 核心决策，见 §一。评判标准：不能支撑具体检索或统计的字段不单独成列 |
| **K3** | 保真方式 | **`raw_ocr_text` 保真**，不再另存结构化 JSON 副本 | v1.0 的双写（JSON + 关系表）本身就是冗余，与 K2 冲突。改为：原文进 `raw_ocr_text`，统计进关系表 |
| **K4** | 字典表 vs TINYINT 枚举 | **两分**：可扩展的中医药术语用**字典表**；封闭小枚举用 **TINYINT + 附表** | 药材有别名、有基原关系、条目持续增长，必须是表；就诊类型等取值封闭，TINYINT 更紧凑 |
| **K5** | 炮制品建模 | **独立药材 + `parent_herb_id` 指向基原** | 与 HIS 及处方实际书写一致（项目名就是"盐黄柏""醋莪术"），统计直接 |
| **K6** | 隐私 | **`patient_id` 为唯一关联键；`id_no` 独立可缺省；不存 HIS 卡号明文** | 真实样本的 HIS 卡号内嵌完整身份证号，必须解耦 |

---

## 六、命名与编码约定

| 项 | 约定 | 示例 |
|---|---|---|
| 表名 | 小写 snake_case 英文 | `case_narrative` |
| 字段名 | 小写 snake_case 英文 | `body_of_tongue` |
| 主键 | 主数据 `TEXT`(ULID)；业务子表 `INTEGER AUTOINCREMENT` | `patient_id` / `record_id` |
| 布尔 | `BOOLEAN`，0 否 / 1 是 | `is_deleted` |
| 枚举 | `UNSIGNED TINYINT` + 附表编号 | `doc_type` → 附表 A11 |
| 时间 | `TIMESTAMP`，`%Y-%m-%d %H:%M:%S` | `created_at` |
| 日期 | `DATE`，`%Y-%m-%d` | `clinic_date` |
| 剂量/指标 | `REAL`，**指标不存单位**，单位见中文释义 | `dose`(g) |

---

## 七、落地实现（已完成）

本说明书是评审用的字段级规范；**可执行 schema 的权威来源是 ORM 模型**，两者由脚本逐字段比对，不允许漂移。

| 落地项 | 位置 |
|---|---|
| 21 张表的 ORM 模型 | `backend/app/models/` |
| Alembic 迁移（可正向/回滚） | `backend/alembic/versions/` |
| 中文全文检索（聚合表 + FTS5 + 18 个触发器 + 按长度路由） | `backend/app/search/case_search.py` |
| 字段级审计留痕 | `backend/app/audit.py` |
| 字典种子数据与药名归一 | `backend/app/seed/` · `backend/app/dictionary.py` |
| 建库脚本 | `backend/scripts/init_db.py` |
| 说明书 ⇄ 模型漂移检查 | `backend/scripts/check_spec_drift.py` |

**建库**：

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r backend/requirements.txt
./.venv/bin/python backend/scripts/init_db.py
```

**验收状态**：全部 DDL 可执行、迁移可正反向、FTS5 触发器同步正确、2 字词检索路由经回归测试、字典种子数据入库可用 —— 阶段门禁五项全部满足。数据库层 **50 项测试通过**，其中包含一次「五诊次病程」的端到端验证。

> 原计划"由说明书生成 DDL"的做法已调整：说明书与模型若各自生成 SQL，会形成两个真相源。现改为**模型为权威、说明书为评审文档**，用漂移检查保证二者一致。

---

## 八、待确认事项

| # | 事项 | 影响 | 建议 |
|---|---|---|---|
| Q1 | `case_narrative` 保留舌质/舌苔/脉象三列是否值得 | 若认为舌脉统计价值不高，可进一步并入「其他望闻切诊」单栏，表数不变、字段再减 3 | 建议保留：这是中医分析中最常用的三个结构化维度 |
| Q2 | 中医病名是否需要与证型一样的字典外键 | 病名检索与统计 | 建议暂不加：`dict_term`（类型=中医病名）已可做联想 |
| Q3 | 是否需要 `lab_result_item` 支持检验指标趋势 | 随访类病种的指标趋势 | 建议列入 v1.1；当前 `auxiliary_exam` 自由文本已够用 |
| Q4 | 师承关系是否需要"学生"表（当前为单机单人） | 若日后多人共用需扩展 | 建议暂不建 |

---

## 附：相关文档

| 文档 | 内容 |
|---|---|
| [`case-database-spec.xlsx`](./case-database-spec.xlsx) | **字段级结构说明书**（21 表 / 247 字段 / 17 组枚举） |
| [`requirements-analysis.md`](./requirements-analysis.md) | 需求分析报告与 D1~D4 决策 |
| [`phase-1-database-design.md`](./phase-1-database-design.md) | 阶段一设计说明；§四 中文全文检索方案仍有效，§三 DDL 已被取代 |
| [`../tools/build_db_spec.py`](../tools/build_db_spec.py) | 说明书生成器（表定义单一数据源） |
