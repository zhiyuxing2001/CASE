# CASE 数据库设计说明

> 阶段一 · 任务 `DB-02` 概念模型 + `DB-04` 逻辑模型
> CASE — Clinical Archives for Student Encounters

| 项 | 内容 |
|---|---|
| 版本 | v1.0 |
| 字段级规范 | [`case-database-spec.xlsx`](./case-database-spec.xlsx)（**28 张表 / 342 字段 / 19 组枚举**） |
| 生成方式 | [`tools/build_db_spec.py`](../tools/build_db_spec.py) —— 表定义即单一数据源，可重复生成 |
| 设计依据 | 睡眠专病数据库结构说明书（XBB23059）· 2 份真实病案 · [`requirements-analysis.md`](./requirements-analysis.md) |
| 状态 | 待评审 |

---

## 一、设计依据

本设计综合三份材料：

| 来源 | 提供什么 |
|---|---|
| **睡眠专病数据库结构说明书**（11 张表） | **结构与约定范式**：命名法、字段说明格式、`father_id` 病程链、JSON 子结构、TINYINT 枚举附表 |
| **2 份真实病案**（手写教学表单 + HIS 导出） | **真实字段需求**：HIS 医嘱表的频次/总量/付数/开立医生、手写表单的辨证分析栏、跨专科就诊、多诊断并存 |
| [`requirements-analysis.md`](./requirements-analysis.md) | **设计约束与决策**：本地优先、离线降级、人工终审、字段溯源、隐私保护，以及 D1~D4 四项评审决策 |

---

## 二、总体结构

**28 张表，分七组**：

| 分组 | 表数 | 表 |
|---|---|---|
| 一、主数据 | 3 | `info_patient` · `info_record` · `mentor` |
| 二、病史 | 7 | `complaint_and_present_illness` · `chronic_diseases` · `communicable_diseases_related` · `personal_history` · `menorrhea_and_obstetric_history` · `other_history` · `hospital_exam` |
| 三、诊断与治疗 | 4 | `diagnosis` · `diagnosis_item` · `treatment` · `prescription_item` |
| 四、字典 | 5 | `dict_herb` · `dict_herb_alias` · `dict_syndrome` · `dict_formula` · `dict_term` |
| 五、跟师学习 | 3 | `learning_note` · `mentor_comment` · `note_record_link` |
| 六、来源与溯源 | 4 | `source_document` · `attachment` · `ocr_job` · `ocr_field_confidence` |
| 七、系统 | 2 | `audit_log` · `app_setting` |

### 2.1 实体关系

```
        mentor ──────────┐
            │            │
            │            │ (带教)
            ▼            ▼
   info_patient ──< info_record >── source_document ──< attachment ──< ocr_job ──< ocr_field_confidence
                        │  ▲
                        │  └── father_id 自指（初诊自指，复诊指向初诊）
                        │
   ┌────────────────────┼────────────────────┬──────────────┬───────────────┐
   ▼                    ▼                    ▼              ▼               ▼
complaint_and_      chronic_           personal_      other_          hospital_
present_illness     diseases           history        history         exam
   （主诉/现病史/四诊）  （慢病 JSON）       （个人史）      （过敏/家族）    （检查/体格）

                        │
            ┌───────────┴───────────┐
            ▼                       ▼
        diagnosis               treatment
            │                       │
            ▼                       ▼
      diagnosis_item          prescription_item ──> dict_herb ──< dict_herb_alias
            │                       │                   ▲
            ▼                       ▼                   │ parent_herb_id 自指
      dict_syndrome            dict_formula        （基原 ← 炮制品）
                                     │
                              dict_term（舌质/舌苔/脉象/炮制/用法…）

   跟师学习线：info_record ──< note_record_link >── learning_note ──< mentor_comment
   系统线：    audit_log（全表字段级留痕）· app_setting
```

### 2.2 数据分层

数据库同时容纳**两个极端**（这是真实病案决定的，见需求分析 §三）：

| 层 | 载体 | 用途 |
|---|---|---|
| **保真层** | JSON 列（`present_illness`、`formula_json`、`disorders`…）+ `raw_ocr_text` | 原样保存，永不覆盖，用于回看与溯源 |
| **统计层** | 关系表（`prescription_item`、`diagnosis_item`）+ 字典外键 | 归一化、可索引、可外键，用于频次与分布分析 |
| **溯源层** | `source_document` → `attachment` → `ocr_job` → `ocr_field_confidence` | 每个字段可追回来源图片与置信度 |

---

## 三、与睡眠专病数据库的对照

### 3.1 直接采纳（9 项）

| # | 采纳内容 | 说明 |
|---|---|---|
| 1 | **说明书五列格式** | 字段名称 / 中文释义 / 数据类型 / 键描述 / 数据说明与数据约束；JSON 子结构在右侧展开 |
| 2 | **表命名法** | 小写 snake_case 英文 + 中文释义，如 `complaint_and_present_illness` |
| 3 | **主键策略** | 主数据用 `TEXT` ULID 业务编号，业务子表用 `INTEGER AUTOINCREMENT` |
| 4 | **`father_id` 单字段病程链** | **初诊指向自身，复诊指向初诊**。取整个病程只需 `WHERE father_id = ?`，无需递归。这一方案优于本项目原计划的双字段（`parent_case_id` + `root_case_id`），已采纳取代 |
| 5 | **就诊子表挂载方式** | 每张临床子表以 `(record_id, patient_id)` 双键关联就诊记录 |
| 6 | **JSON 承载复杂结构** | 病史、个人史、检查、婚育史等可变结构用 JSON 列 + 右侧子结构说明 |
| 7 | **枚举用 `UNSIGNED TINYINT` + 附表** | 19 组枚举集中登记在「附表 枚举字典」工作表 |
| 8 | **约束写在说明列** | 必填/选填、默认值、取值范围、单位、自动计算规则全部显式写明 |
| 9 | **审计时间字段** | 每表 `created_at` / `updated_at` |

### 3.2 保留的中医特色字段（7 项）

`就诊节气 solar_terms`（二十四节气编码）· `舌质 body_of_tongue` · `舌苔 fur_of_tongue` · `切诊 pulse` · `中医病证 disorders` · `中医辨证 patterns` · `辨证分析 patterns_analysis` · `方剂/药味/煎煮法/付数`

另采纳两项业务约定：**主诉 ≤ 20 Unicode 字符**（中医主诉书写规范）、**血压值缺一时用 `-1` 代替**。

### 3.3 对睡眠库的调整（6 项）

| # | 调整 | 理由 |
|---|---|---|
| 1 | **处方药味拆为 `prescription_item` 关系表** | 睡眠库将药味存于 `formula` JSON。CASE 的核心价值是回答"老师治某脘痛常用哪几味药"，需要**药物频次统计**与**药材字典归一**；JSON 无法建索引、无法外键约束、无法高效聚合。治疗记录表的 JSON 仍保留为保真副本 |
| 2 | **诊断拆出 `diagnosis_item` 关系表** | 同理，支持证型分布统计与标准编码关联；`diagnosis` 表保留 JSON 原文 |
| 3 | **患者表隐私改造** | `patient_id`（ULID）为关联主键；身份证号 `id_no` 独立可缺省；**不存储内嵌身份证的 HIS 就诊卡号明文**（决策 D4） |
| 4 | **就诊表扩充** | 增加 `mentor_id`（带教老师）、`department`（就诊科室）、`visit_type`、`chief_complaint_inherited`。真实样本显示**就诊科室 ≠ 疾病所属专科**，二者不可混用 |
| 5 | **增加软删除** | 各主表增设 `is_deleted`，学习资料误删代价高 |
| 6 | **检查表增加外院机构** | 真实样本的辅助检查含外院机构名（子结构新增 `institution`） |

### 3.4 CASE 新增（15 张表）

> 表数勾稽：睡眠库沿用 11 张 + 本节新增 15 张 + §3.3 拆出的 2 张关系表（`diagnosis_item`、`prescription_item`）= **28 张**。

| 分组 | 表 | 为什么睡眠库没有 |
|---|---|---|
| 字典（5） | `dict_herb` · `dict_herb_alias` · `dict_syndrome` · `dict_formula` · `dict_term` | 睡眠库是纯录入研究库，无 OCR 与归一需求；CASE 需字典做**药名归一**与**形近字纠错** |
| 师承（4） | `mentor` · `learning_note` · `mentor_comment` · `note_record_link` | CASE 是**跟师学习系统**，教学元数据是核心，睡眠库无此需求 |
| 溯源（4） | `source_document` · `attachment` · `ocr_job` · `ocr_field_confidence` | CASE 需从扫描件入库，必须回答"这个字段来自哪张图的哪一行" |
| 系统（2） | `audit_log` · `app_setting` | 学习记录可信性依赖不可抵赖的修改历史 |

---

## 四、关键设计决策

| # | 决策 | 选择 | 理由 |
|---|---|---|---|
| **K1** | 病程链字段 | **`father_id` 单字段，初诊自指** | 取代原 D1 的"`parent_case_id` + 冗余 `root_case_id`"双字段方案。单字段即可同时表达链式关系与 O(1) 病程聚合，更简洁。约束：初诊 `father_id = record_id`；复诊 `father_id = 初诊 record_id` |
| **K2** | 保真 vs 统计 | **双写**：JSON 保真 + 关系表统计 | 病案原文不可失真（手写识别本就有误），同时统计必须可索引可归一。二者由服务层同步写入，`diagnosis` / `treatment` 的 JSON 为**准**，`*_item` 表为**派生** |
| **K3** | 字典表 vs TINYINT 枚举 | **两分**：可扩展的中医药术语（中药/证型/方剂/舌脉/炮制）用**字典表**；封闭的小枚举（性别、婚姻、状态、类型）用 **TINYINT + 附表** | 沿用睡眠库做法。药材有别名、有基原关系、条目会持续增长，必须是表；婚姻状况等取值封闭，TINYINT 更紧凑 |
| **K4** | 炮制品建模 | **独立药材 + `parent_herb_id` 指向基原** | 决策 D2。与 HIS 及处方实际书写一致（项目名就是"盐黄柏""醋莪术"），统计直接 |
| **K5** | 隐私 | **`patient_id` 为唯一关联键；`id_no` 独立可缺省；不存 HIS 卡号明文** | 决策 D4。真实样本的 HIS 卡号内嵌完整身份证号，必须解耦 |

### 4.1 与前期 34 表草案的差异

本项目在需求分析前曾起草过一份 34 张表的 DDL（见 [`phase-1-database-design.md`](./phase-1-database-design.md) §三）。本设计相对其变化：

| 变化 | 说明 |
|---|---|
| 表数 34 → 28 | 病史类 7 张表改按睡眠库的**"每次就诊一张宽表 + JSON"**方案，取代原先的 `case_examinations` 单表 + 大量小字典表，结构更贴近既有实践 |
| 病程链 2 字段 → 1 字段 | 见 K1 |
| 新增 | `mentor`、`diagnosis_item`、`source_document`、`dict_*` 体系 |
| 移除 | 原 `cases` 单表承载全部临床内容的设计；拆为 `info_record` + 7 张病史表 |

> ⚠️ [`phase-1-database-design.md`](./phase-1-database-design.md) §三 的 DDL 为**v1 草案，已被本设计取代**。其 §四「中文全文检索方案」仍然有效，将在 `DB-04` 重新落到新结构上。

---

## 五、命名与编码约定

| 项 | 约定 | 示例 |
|---|---|---|
| 表名 | 小写 snake_case 英文 | `prescription_item` |
| 字段名 | 小写 snake_case 英文 | `herb_name_norm` |
| 主键 | 主数据 `TEXT`(ULID)；业务子表 `INTEGER AUTOINCREMENT` | `patient_id` / `item_id` |
| 布尔 | `BOOLEAN`，0 否 / 1 是 | `is_deleted` |
| 枚举 | `UNSIGNED TINYINT` + 附表编号 | `doc_type` → 附表 A13 |
| 时间 | `TIMESTAMP`，`%Y-%m-%d %H:%M:%S` | `created_at` |
| 日期 | `DATE`，`%Y-%m-%d` | `clinic_date` |
| 金额/剂量 | `REAL`，**指标不存单位**，单位见中文释义 | `dose`(g)、`temperature`(℃) |
| 机构标准 | 引用国标编码 | `nationality` → GB/T 2659-2022；`ethnicity` → GB/T 3304-1991 |

---

## 六、DDL 落地计划（`DB-04`）

本说明书是字段级规范，尚未生成可执行 DDL。`DB-04` 将：

1. 由 [`tools/build_db_spec.py`](../tools/build_db_spec.py) 的表定义**同时生成** `CREATE TABLE` 语句与 Alembic 迁移，避免说明书与实现脱节
2. 在新结构上重新落地 [`phase-1-database-design.md`](./phase-1-database-design.md) §四 的中文全文检索方案（FTS5 `trigram` + 按查询长度路由到 LIKE）
3. 复核 §七 待确认事项后再定稿

---

## 七、待确认事项

| # | 事项 | 影响 | 建议 |
|---|---|---|---|
| Q1 | **JSON 与关系表双写**（K2）是否接受 | 若只保留 JSON，药物频次统计需改用 `json_each`，无法建索引与外键；若只保留关系表，则丢失原始结构保真 | 建议保留双写，由服务层保证一致性并提供校验脚本 |
| Q2 | 慢病表沿用睡眠库的**固定病种列**（高血压/糖尿病/冠心病/高脂血症/高尿酸/脑梗死 + 其他） | CASE 病种不限，固定列可能频繁改表 | 建议沿用（覆盖常见慢病）并依赖 `other_ncd` 兜底；若认为不妥可改为完全 JSON 化 |
| Q3 | 是否需要 `lab_result_item` 关系表以支持检验指标趋势 | 糖尿病等随访病种的指标趋势分析 | 建议 MVP 先用 JSON，趋势分析列入 v1.1 |
| Q4 | 是否保留睡眠库中**就诊节气** `solar_terms` | 中医时间医学特色字段，但 CASE 未必使用 | 建议保留，成本低且符合中医语境 |
| Q5 | 师承关系是否需要"学生"表（当前为单机单人使用） | 若日后多人共用需扩展 | 建议暂不建，`learning_note` 已可承载学生身份信息 |

---

## 附：相关文档

| 文档 | 内容 |
|---|---|
| [`case-database-spec.xlsx`](./case-database-spec.xlsx) | **字段级结构说明书**（28 表 / 342 字段 / 19 组枚举） |
| [`requirements-analysis.md`](./requirements-analysis.md) | 需求分析报告与 D1~D4 决策 |
| [`phase-1-database-design.md`](./phase-1-database-design.md) | 阶段一设计说明；§四 中文全文检索方案仍有效，§三 DDL 已被取代 |
| [`../tools/build_db_spec.py`](../tools/build_db_spec.py) | 说明书生成器（表定义单一数据源） |
