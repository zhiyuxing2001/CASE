# 阶段一：数据库设计

> CASE — Clinical Archives for Student Encounters

| 项 | 内容 |
|---|---|
| 阶段 | **阶段一 · 数据库设计** |
| 目标 | 产出一套经过验证、可直接支撑软件开发的数据库 |
| 交付物 | SQLAlchemy 模型 · Alembic 迁移 · 字典表种子数据 · 数据字典文档 · 数据库层测试 |
| 估算 | 11.2 人日 / 14 项任务（`DB-01` ~ `DB-14`） |
| 状态 | 设计草案 v2.0，待评审 |

> 配套文档：[`project-plan.md`](./project-plan.md)（总纲）· [`phase-2-software-development.md`](./phase-2-software-development.md)（阶段二）· [`task-breakdown.md`](./task-breakdown.md)（任务清单）

**本文件结构**：§一 设计原则 → §二 实体关系 → §三 完整 DDL → §四 中文全文检索 → §五 关键取舍 → §六 字典种子来源 → §七 待确认事项。
对应任务：`DB-01`~`DB-05`（需求与模型设计）、`DB-06`~`DB-10`（落地与检索）、`DB-11`~`DB-14`（数据治理与验收）。

---

## 一、设计原则

在动手建表前，先明确五条贯穿全库的取舍，它们解释了后面所有看起来"多余"的表和字段：

| # | 原则 | 具体体现 |
|---|---|---|
| 1 | **结构化服务于统计，原始文本服务于保真** | 处方既存结构化药味明细，也存 `raw_ocr_text` 与 `raw_prescription_text`。宁可冗余，不可失真。 |
| 2 | **字典只做建议，绝不做闸门** | 所有指向字典表的外键**均可为 NULL**，同时保留 `*_raw` 文本字段。录入"生地"而字典里只有"生地黄"时，**必须能保存成功**并提示归一建议。 |
| 3 | **一切可溯源** | 每个结构化字段都能追回来源：`attachments` → `ocr_jobs` → `ocr_field_confidence`。 |
| 4 | **隐私在建模层就解决** | `patient_code` 是关联主键，姓名单独存放且可被替换为空/代称；上云前脱敏只需处理一列。 |
| 5 | **不可抵赖的修改历史** | `audit_log` 记录每一次字段级变更，学习记录的可信性依赖于此。 |

---

## 二、实体关系总览

```
                        ┌──────────┐      ┌──────────┐
                        │ patients │      │ mentors  │
                        └────┬─────┘      └────┬─────┘
                             │                 │
                             │            ┌────▼──────────┐
                             │            │  encounters   │ 跟诊事件
                             │            └────┬──────────┘
                             │                 │
                        ┌────▼─────────────────▼────┐
                        │          cases            │ 病案主表
                        │  (+search_text 检索聚合列) │
                        └──┬───┬───┬───┬───┬───┬────┘
                           │   │   │   │   │   │
      ┌────────────────────┘   │   │   │   │   └──────────────┐
      │        ┌───────────────┘   │   │   └───────┐          │
      ▼        ▼                   ▼   ▼           ▼          ▼
┌───────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────┐ ┌───────────┐
│case_exam- │ │diagnoses │ │treatments │ │prescriptions │ │attachments│
│inations   │ │(1:N)     │ │(1:N)      │ │(1:N)         │ │(1:N 图片) │
│四诊(1:1)  │ │          │ │           │ │              │ └─────┬─────┘
└───────────┘ └────┬─────┘ └───────────┘ └──────┬───────┘       │
                   │                            │               ▼
                   ▼                            ▼        ┌─────────────┐
            ┌────────────┐            ┌──────────────────┐│  ocr_jobs   │
            │ syndromes  │            │prescription_items│└──────┬──────┘
            │ 证型字典   │            │  处方药味明细    │       │
            └────────────┘            └────────┬─────────┘       ▼
            ┌────────────┐                     ▼        ┌──────────────────┐
            │ formulas   │              ┌────────────┐  │ocr_field_confid- │
            │ 方剂字典   │              │   herbs    │  │ence 字段级置信度 │
            └─────┬──────┘              │  中药字典  │  └──────────────────┘
                  │                     └──────┬─────┘
                  ▼                            ▼
            ┌──────────────┐            ┌──────────────┐
            │formula_items │            │herb_aliases  │ 中药别名（关键）
            └──────────────┘            └──────────────┘

  跟师学习线：
  ┌───────────┐     ┌────────────────┐     ┌──────────────────┐
  │encounters │────►│ learning_notes │◄────│ mentor_comments  │
  └───────────┘     │ 日志/心得/笔记 │     │ 导师点评         │
                    └───────┬────────┘     └──────────────────┘
                            ▼
                    ┌────────────────┐
                    │note_case_links │ 心得 ↔ 病案 双向引用
                    └────────────────┘

  辅助线：
  terms_dictionary（统一字典：舌象/脉象/炮制/用法）
  audit_log（字段级修改留痕）  ai_conversations / ai_messages（AI 留痕）
  ocr_eval_items（OCR 评测集，M2 基线用）
```

---

## 三、DDL 草案

> 约定：主键统一 `INTEGER PRIMARY KEY`（SQLite rowid 别名）；时间统一 `TEXT` 存 ISO8601 本地时间；布尔用 `INTEGER 0/1`；删除采用**软删除**（`is_deleted`），学习数据不做物理删除。

### 3.1 主数据

```sql
-- ============================================================
-- 患者（隐私敏感：patient_code 是关联主键，name 可被脱敏替换）
-- ============================================================
CREATE TABLE patients (
    id                INTEGER PRIMARY KEY,
    patient_code      TEXT    NOT NULL UNIQUE,          -- 系统编号 P2026001
    name              TEXT,                             -- 可空；上云前替换为代称
    name_is_masked    INTEGER NOT NULL DEFAULT 0,       -- 是否已脱敏
    gender            TEXT    CHECK (gender IN ('男','女','未知')),
    birth_year        INTEGER,                          -- 只存年份，降低敏感度
    age_at_first_visit INTEGER,
    phone             TEXT,                             -- 上云前必须脱敏
    occupation        TEXT,
    address_region    TEXT,                             -- 仅存到区县，不存详址
    notes             TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at        TEXT,
    is_deleted        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_patients_code ON patients(patient_code);

-- ============================================================
-- 带教老师
-- ============================================================
CREATE TABLE mentors (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    title       TEXT,                                   -- 主任医师 / 教授
    affiliation TEXT,                                   -- 医院 / 科室
    expertise   TEXT,                                   -- 擅长领域，用于"专长病种"统计
    is_primary  INTEGER NOT NULL DEFAULT 0,             -- 主带教老师
    notes       TEXT,
    is_deleted  INTEGER NOT NULL DEFAULT 0
);

-- ============================================================
-- 跟诊事件：一次跟诊 = 一个 encounters 记录，关联当次的多份病案
-- ============================================================
CREATE TABLE encounters (
    id             INTEGER PRIMARY KEY,
    encounter_date TEXT NOT NULL,                       -- YYYY-MM-DD
    mentor_id      INTEGER REFERENCES mentors(id),
    location       TEXT,                                -- 医院/门诊/诊室
    department     TEXT,
    session_no     INTEGER,                             -- 第几次跟诊（累计序号）
    chief_topic    TEXT,                                -- 本次主题，如"脾胃病专诊"
    summary        TEXT,                                -- 本次跟诊小结
    case_count     INTEGER NOT NULL DEFAULT 0,          -- 冗余计数，列表页免 JOIN
    created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at     TEXT,
    is_deleted     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_encounters_date   ON encounters(encounter_date);
CREATE INDEX idx_encounters_mentor ON encounters(mentor_id);
```

### 3.2 病案主表

```sql
-- ============================================================
-- 病案主表
-- ============================================================
CREATE TABLE cases (
    id                INTEGER PRIMARY KEY,
    case_code         TEXT NOT NULL UNIQUE,             -- 病案编号
    patient_id        INTEGER NOT NULL REFERENCES patients(id),
    encounter_id      INTEGER REFERENCES encounters(id),-- 可空：非跟诊病案
    mentor_id         INTEGER REFERENCES mentors(id),   -- 冗余自 encounter，便于按老师统计

    -- ---- 就诊信息 ----
    visit_date        TEXT NOT NULL,                    -- YYYY-MM-DD
    visit_type        TEXT CHECK (visit_type IN ('初诊','复诊','复诊随访')),
    visit_no          INTEGER DEFAULT 1,                -- 第几诊
    parent_case_id    INTEGER REFERENCES cases(id),     -- 复诊指向初诊，构成病程链
    department        TEXT,

    -- ---- 病史（自由文本为主，此处不做过度结构化）----
    chief_complaint   TEXT,                             -- 主诉（含时间，如"胃脘胀痛3月余"）
    present_illness   TEXT,                             -- 现病史
    past_history      TEXT,                             -- 既往史
    personal_history  TEXT,                             -- 个人史（饮食/烟酒/作息）
    marital_history   TEXT,                             -- 婚育史
    family_history    TEXT,                             -- 家族史
    allergy_history   TEXT,                             -- 过敏史

    -- ---- 诊断主项（冗余便捷字段；完整诊断见 diagnoses 表）----
    tcm_disease       TEXT,                             -- 中医病名（主）
    syndrome          TEXT,                             -- 证型（主）
    western_diagnosis TEXT,                             -- 西医诊断（主）

    -- ---- 治法主项（完整见 treatments 表）----
    treatment_principle TEXT,                           -- 治则治法

    -- ---- 处方冗余文本（服务于检索与快速展示）----
    prescription_text TEXT,                             -- "柴胡10g 白芍15g ..." 聚合文本

    -- ---- 医嘱与随访 ----
    advice            TEXT,                             -- 医嘱（饮食起居调摄）
    outcome           TEXT,                             -- 疗效转归
    follow_up_plan    TEXT,                             -- 复诊计划

    -- ---- 溯源 ----
    raw_ocr_text      TEXT,                             -- OCR 原始文本（保真，永不覆盖）
    source_type       TEXT CHECK (source_type IN ('手写录入','OCR','导入','模板')),
    primary_attachment_id INTEGER,                      -- 主要来源图片

    -- ---- 检索聚合列（由服务层写入时生成，供 FTS5 使用）----
    search_text       TEXT,                             -- 见 §四

    -- ---- 元数据 ----
    status            TEXT NOT NULL DEFAULT 'draft'
                          CHECK (status IN ('draft','confirmed','archived')),
    tags              TEXT,                             -- 逗号分隔轻量标签
    student_notes     TEXT,                             -- 学生本人批注（非导师点评）
    created_at        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at        TEXT,
    is_deleted        INTEGER NOT NULL DEFAULT 0,
    CHECK (visit_type <> '复诊' OR parent_case_id IS NOT NULL OR visit_no = 1)
);
CREATE INDEX idx_cases_patient  ON cases(patient_id);
CREATE INDEX idx_cases_encount  ON cases(encounter_id);
CREATE INDEX idx_cases_mentor   ON cases(mentor_id);
CREATE INDEX idx_cases_date     ON cases(visit_date);
CREATE INDEX idx_cases_disease  ON cases(tcm_disease);
CREATE INDEX idx_cases_syndrome ON cases(syndrome);
CREATE INDEX idx_cases_parent   ON cases(parent_case_id);
```

### 3.3 四诊（1:1，拆表以保持 cases 可读）

```sql
-- ============================================================
-- 四诊：把高频统计项（舌/脉）单独成列，其余为文本
-- ============================================================
CREATE TABLE case_examinations (
    id             INTEGER PRIMARY KEY,
    case_id        INTEGER NOT NULL UNIQUE REFERENCES cases(id) ON DELETE CASCADE,

    -- 望诊
    inspection     TEXT,        -- 神色形态总体
    complexion     TEXT,        -- 面色
    tongue_body    TEXT,        -- 舌质：淡红/红/淡白/紫暗…
    tongue_coating TEXT,        -- 舌苔：薄白/黄腻/少苔…
    tongue_other   TEXT,        -- 舌形、舌下络脉

    -- 闻诊
    auscultation   TEXT,        -- 语声、气息
    olfaction      TEXT,        -- 气味

    -- 问诊（现病史未覆盖的常规项）
    inquiry        TEXT,        -- 问诊总体补充
    chills_fever   TEXT,        -- 寒热
    sweating       TEXT,        -- 汗
    appetite       TEXT,        -- 饮食口味
    sleep          TEXT,        -- 睡眠
    stool          TEXT,        -- 大便
    urine          TEXT,        -- 小便
    emotion        TEXT,        -- 情志
    menses         TEXT,        -- 经带（女性）
    pain           TEXT,        -- 疼痛部位性质

    -- 切诊
    pulse          TEXT,        -- 脉象：弦细/滑数/沉迟…
    pulse_detail   TEXT,        -- 寸关尺分部
    palpation      TEXT,        -- 按诊（腹诊等）

    -- 体格检查与辅助检查
    physical_exam  TEXT,        -- 西医体格检查
    lab_findings   TEXT,        -- 化验/影像（可含图片引用）
    vitals         TEXT,        -- 体温/血压/心率等

    created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at     TEXT
);
CREATE INDEX idx_exam_tongue ON case_examinations(tongue_body, tongue_coating);
CREATE INDEX idx_exam_pulse  ON case_examinations(pulse);
```

> **为何拆出 `tongue_body` / `tongue_coating` / `pulse` 单列**：v1.1 要做"舌象分布""脉象频次"统计，把它们埋在自由文本里会导致统计时不得不做字符串解析。这是**为后置功能预留的最小代价**。

### 3.4 诊断与治法（1:N）

```sql
-- ============================================================
-- 诊断：一个病案可有多个诊断（主证/兼证、中医病名 + 西医诊断）
-- ============================================================
CREATE TABLE diagnoses (
    id             INTEGER PRIMARY KEY,
    case_id        INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    diagnosis_type TEXT NOT NULL
                     CHECK (diagnosis_type IN ('中医病名','证型','西医诊断','兼证')),
    name           TEXT NOT NULL,             -- 实际录入的名称（原文）
    syndrome_id    INTEGER REFERENCES syndromes(id),  -- 归一化引用，可空
    standard_code  TEXT,                      -- 国标/ICD-11 编码，可空
    standard_system TEXT,                     -- 'GB/T 15657' | 'ICD-11 TM' | ...
    is_primary     INTEGER NOT NULL DEFAULT 0,-- 主诊断
    confidence     REAL,                      -- AI 识别置信度（人工录入为 NULL）
    sequence       INTEGER DEFAULT 0,
    notes          TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX idx_diag_case ON diagnoses(case_id);
CREATE INDEX idx_diag_name ON diagnoses(name);
CREATE INDEX idx_diag_syn  ON diagnoses(syndrome_id);

-- ============================================================
-- 治则治法：可多条
-- ============================================================
CREATE TABLE treatments (
    id         INTEGER PRIMARY KEY,
    case_id    INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    method     TEXT NOT NULL,        -- 疏肝理气和胃 / 益气健脾
    method_type TEXT CHECK (method_type IN ('治则','治法')),
    sequence   INTEGER DEFAULT 0,
    notes      TEXT
);
CREATE INDEX idx_treat_case ON treatments(case_id);
```

### 3.5 处方与药味（核心）

```sql
-- ============================================================
-- 处方：一个病案可有多张方（主方 + 外洗方 + 中成药）
-- ============================================================
CREATE TABLE prescriptions (
    id              INTEGER PRIMARY KEY,
    case_id         INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    prescription_no INTEGER NOT NULL DEFAULT 1,         -- 第几张方
    formula_id      INTEGER REFERENCES formulas(id),    -- 基础方（柴胡疏肝散），可空
    formula_name    TEXT,                               -- 方名原文
    is_modified     INTEGER NOT NULL DEFAULT 0,         -- 是否加减
    modification    TEXT,                               -- 加减说明（"加陈皮、去甘草"）
    dose_count      REAL,                               -- 剂数
    dose_unit       TEXT DEFAULT '剂',
    usage_method    TEXT,                               -- 用法：水煎服 / 冲服 / 外洗
    decoction       TEXT,                               -- 煎服法：日一剂分早晚温服
    course_days     INTEGER,                            -- 疗程天数
    raw_text        TEXT,                               -- 处方原文（保真，永不覆盖）
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX idx_rx_case    ON prescriptions(case_id);
CREATE INDEX idx_rx_formula ON prescriptions(formula_id);

-- ============================================================
-- 处方药味明细：全库分析的核心表
-- ============================================================
CREATE TABLE prescription_items (
    id             INTEGER PRIMARY KEY,
    prescription_id INTEGER NOT NULL REFERENCES prescriptions(id) ON DELETE CASCADE,
    herb_id        INTEGER REFERENCES herbs(id),        -- 归一化引用，可空
    herb_name      TEXT NOT NULL,                       -- 录入原文（"生地"）
    herb_name_norm TEXT,                                -- 归一后标准名（"生地黄"）
    dose           REAL,                                -- 剂量数值
    dose_unit      TEXT DEFAULT 'g',
    dose_text      TEXT,                                -- 非常规剂量原文（"适量""3片"）
    role           TEXT CHECK (role IN ('君','臣','佐','使')),
    processing     TEXT,                                -- 炮制：炒 / 炙 / 生 / 醋制
    decoction_note TEXT,                                -- 先煎 / 后下 / 包煎 / 烊化 / 冲服
    is_added       INTEGER DEFAULT 0,                   -- 本次加减：新增
    is_removed     INTEGER DEFAULT 0,                   -- 本次加减：减去
    sequence       INTEGER NOT NULL DEFAULT 0,          -- 方中顺序（君臣佐使顺序有意义）
    confidence     REAL,                                -- OCR/AI 识别置信度
    needs_review   INTEGER NOT NULL DEFAULT 0,          -- 是否需人工复核
    notes          TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX idx_rxitem_rx   ON prescription_items(prescription_id);
CREATE INDEX idx_rxitem_herb ON prescription_items(herb_id);
CREATE INDEX idx_rxitem_name ON prescription_items(herb_name);
CREATE INDEX idx_rxitem_norm ON prescription_items(herb_name_norm);
```

> **为什么 `herb_name` 与 `herb_name_norm` 都存**：
> `herb_name` 保留学生原始写法（保真、可回看），`herb_name_norm` 由字典/别名表归一后写入，用于统计。
> 统计"柴胡用了多少次"时查 `herb_id`/`herb_name_norm`，绝不会因"南柴胡/北柴胡/柴胡"写法不一而漏计。**这是药物频次分析准确性的前提。**

### 3.6 字典表

```sql
-- ============================================================
-- 中药字典
-- ============================================================
CREATE TABLE herbs (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,     -- 标准名：生地黄
    pinyin        TEXT,                     -- sheng di huang（便于拼音检索）
    category      TEXT,                     -- 解表药/清热药/补虚药…
    nature        TEXT,                     -- 四气：寒/热/温/凉/平
    flavor        TEXT,                     -- 五味：辛/甘/酸/苦/咸/淡/涩
    meridians      TEXT,                    -- 归经（逗号分隔）
    functions     TEXT,                     -- 功效
    standard_code TEXT,                     -- 药典/国标编码
    usage_note    TEXT,
    is_common     INTEGER NOT NULL DEFAULT 1,-- 是否常用药（影响联想排序）
    is_active     INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_herbs_name ON herbs(name);
CREATE INDEX idx_herbs_py   ON herbs(pinyin);

-- ============================================================
-- 中药别名（同物异名 / 同名异物）—— 中医数据的老大难
-- ============================================================
CREATE TABLE herb_aliases (
    id         INTEGER PRIMARY KEY,
    herb_id    INTEGER NOT NULL REFERENCES herbs(id) ON DELETE CASCADE,
    alias      TEXT NOT NULL,               -- 生地 / 干地黄 / 怀地黄
    alias_type TEXT DEFAULT '异名'
                 CHECK (alias_type IN ('异名','简称','处方名','炮制品','错写')),
    ambiguity_note TEXT,                    -- 同名异物警告："川贝"可能指多种
    source     TEXT,                        -- 来源依据
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE UNIQUE INDEX idx_herbalias_uniq ON herb_aliases(alias, herb_id);
CREATE INDEX idx_herbalias_alias ON herb_aliases(alias);

-- ============================================================
-- 证型字典
-- ============================================================
CREATE TABLE syndromes (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,     -- 肝胃不和证
    category      TEXT,                     -- 脏腑辨证 / 六经辨证 / 卫气营血 / 三焦
    standard_code TEXT,                     -- GB/T 15657 等编码
    standard_system TEXT,
    key_symptoms  TEXT,                     -- 主症要点（用于录入联想与学习提示）
    treatment     TEXT,                     -- 常用治法
    common_formula TEXT,                    -- 代表方
    description   TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_synd_name ON syndromes(name);
CREATE INDEX idx_synd_cat  ON syndromes(category);

CREATE TABLE syndrome_aliases (
    id          INTEGER PRIMARY KEY,
    syndrome_id INTEGER NOT NULL REFERENCES syndromes(id) ON DELETE CASCADE,
    alias       TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_syndalias_uniq ON syndrome_aliases(alias, syndrome_id);

-- ============================================================
-- 方剂字典
-- ============================================================
CREATE TABLE formulas (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,      -- 柴胡疏肝散
    alias        TEXT,                      -- 别名/简称
    source        TEXT,                     -- 出处：《景岳全书》
    category     TEXT,                      -- 和解剂 / 理气剂
    functions    TEXT,                      -- 功用
    indications  TEXT,                      -- 主治
    syndrome_id  INTEGER REFERENCES syndromes(id),
    composition_text TEXT,                  -- 组成原文
    usage_text   TEXT,                      -- 用法原文
    is_active    INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_formula_name ON formulas(name);

-- ============================================================
-- 方剂组成（标准方 → 药味），用于"方剂 vs 实际处方"对比
-- ============================================================
CREATE TABLE formula_items (
    id         INTEGER PRIMARY KEY,
    formula_id INTEGER NOT NULL REFERENCES formulas(id) ON DELETE CASCADE,
    herb_id    INTEGER REFERENCES herbs(id),
    herb_name  TEXT NOT NULL,
    dose       REAL,
    dose_unit  TEXT DEFAULT 'g',
    role       TEXT CHECK (role IN ('君','臣','佐','使')),
    sequence   INTEGER DEFAULT 0
);
CREATE INDEX idx_formulaitem_f ON formula_items(formula_id);
CREATE INDEX idx_formulaitem_h ON formula_items(herb_id);

-- ============================================================
-- 统一术语字典（舌象/脉象/炮制/用法/病名 等轻量字典）
-- ============================================================
CREATE TABLE terms_dictionary (
    id            INTEGER PRIMARY KEY,
    term_type     TEXT NOT NULL
                    CHECK (term_type IN ('舌质','舌苔','脉象','面色','炮制','煎服法',
                                         '用法','中医病名','治法','剂型','西医诊断')),
    term          TEXT NOT NULL,
    standard_code TEXT,
    parent_id     INTEGER REFERENCES terms_dictionary(id),
    description   TEXT,
    usage_count   INTEGER NOT NULL DEFAULT 0,   -- 使用频次，用于联想排序
    is_active     INTEGER NOT NULL DEFAULT 1
);
CREATE UNIQUE INDEX idx_terms_uniq ON terms_dictionary(term_type, term);
CREATE INDEX idx_terms_type ON terms_dictionary(term_type);
```

### 3.7 附件与 OCR 溯源

```sql
-- ============================================================
-- 附件：原始图片/PDF。文件本体存 data/attachments/，库中只存路径与哈希
-- ============================================================
CREATE TABLE attachments (
    id          INTEGER PRIMARY KEY,
    case_id     INTEGER REFERENCES cases(id) ON DELETE SET NULL,  -- 可先上传后关联
    file_path   TEXT NOT NULL,                  -- 相对 data/ 的路径
    thumb_path  TEXT,
    file_type   TEXT CHECK (file_type IN ('image','pdf')),
    mime_type   TEXT,
    file_size   INTEGER,
    width       INTEGER,
    height      INTEGER,
    sha256      TEXT,                           -- 去重 + 完整性校验
    page_no     INTEGER DEFAULT 1,
    sort_order  INTEGER DEFAULT 0,
    caption     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    is_deleted  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_attach_case ON attachments(case_id);
CREATE INDEX idx_attach_sha  ON attachments(sha256);

-- ============================================================
-- OCR 作业：一次识别的完整留痕（引擎、提示词版本、成本）
-- ============================================================
CREATE TABLE ocr_jobs (
    id              INTEGER PRIMARY KEY,
    attachment_id   INTEGER NOT NULL REFERENCES attachments(id) ON DELETE CASCADE,
    case_id         INTEGER REFERENCES cases(id),
    status          TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending','running','succeeded','failed','reviewed','discarded')),
    -- 通道 A：本地 macOS Vision
    vision_engine   TEXT,                       -- 'ocrmac/Vision'
    vision_raw_json TEXT,                       -- [{text, confidence, bbox}]
    vision_text     TEXT,
    vision_ms       INTEGER,
    -- 通道 B：DeepSeek 视觉精修
    model           TEXT,                       -- 'deepseek-flash'
    prompt_version  TEXT,                       -- 提示词版本号，便于回归对比
    structured_json TEXT,                       -- 结构化输出（JSON）
    degraded_mode   TEXT,                       -- 'none' | 'vision_only'（离线降级）
    -- 成本与耗时
    tokens_in       INTEGER,
    tokens_cached   INTEGER,
    tokens_out      INTEGER,
    cost_yuan       REAL,
    duration_ms     INTEGER,
    error_message   TEXT,
    started_at      TEXT,
    finished_at     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX idx_ocrjob_attach ON ocr_jobs(attachment_id);
CREATE INDEX idx_ocrjob_status ON ocr_jobs(status);
CREATE INDEX idx_ocrjob_case   ON ocr_jobs(case_id);

-- ============================================================
-- 字段级置信度：驱动校对界面高亮，也是评测的数据来源
-- ============================================================
CREATE TABLE ocr_field_confidence (
    id          INTEGER PRIMARY KEY,
    ocr_job_id  INTEGER NOT NULL REFERENCES ocr_jobs(id) ON DELETE CASCADE,
    field_path  TEXT NOT NULL,          -- 'prescription_items[3].dose'
    value       TEXT,
    confidence  REAL,
    source      TEXT CHECK (source IN ('vision','llm','fused','dictionary')),
    needs_review INTEGER NOT NULL DEFAULT 0,
    evidence    TEXT,                   -- 依据：Vision 的哪一行 / 坐标
    suggestion  TEXT,                   -- 字典归一建议（"生地"→"生地黄"）
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX idx_ocrconf_job ON ocr_field_confidence(ocr_job_id);
CREATE INDEX idx_ocrconf_review ON ocr_field_confidence(needs_review);

-- ============================================================
-- OCR 评测集（M2 基线用，是"准确率是否达标"的唯一客观依据）
-- ============================================================
CREATE TABLE ocr_eval_items (
    id             INTEGER PRIMARY KEY,
    attachment_id  INTEGER NOT NULL REFERENCES attachments(id) ON DELETE CASCADE,
    ground_truth_json TEXT NOT NULL,    -- 人工标注的正确答案
    is_handwritten INTEGER NOT NULL DEFAULT 0,
    difficulty     TEXT,                -- easy / medium / hard
    notes          TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE ocr_eval_runs (
    id           INTEGER PRIMARY KEY,
    run_label    TEXT NOT NULL,         -- 'vision-baseline' / 'dual-channel-v2'
    engine_config TEXT,                 -- 引擎、模型、提示词版本的组合
    metrics_json TEXT NOT NULL,         -- {cer:.., field_accuracy:{herb:..,dose:..}}
    item_count   INTEGER,
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
```

### 3.8 跟师学习

```sql
-- ============================================================
-- 学习笔记：用 note_type 区分「跟诊日志 / 学习心得 / 读书笔记 / 病例讨论」
-- 这样避免为相似结构建多张表
-- ============================================================
CREATE TABLE learning_notes (
    id           INTEGER PRIMARY KEY,
    note_type    TEXT NOT NULL DEFAULT '学习心得'
                   CHECK (note_type IN ('跟诊日志','学习心得','读书笔记','病例讨论','总结')),
    title        TEXT NOT NULL,
    content_md   TEXT,                          -- Markdown 富文本
    content_html TEXT,                          -- 渲染缓存（可选）
    status       TEXT NOT NULL DEFAULT 'draft'
                   CHECK (status IN ('draft','published','archived')),
    encounter_id INTEGER REFERENCES encounters(id),
    mentor_id    INTEGER REFERENCES mentors(id),
    word_count   INTEGER DEFAULT 0,
    is_ai_assisted INTEGER NOT NULL DEFAULT 0,  -- 是否使用 AI 辅助（学术诚信留痕）
    ai_conversation_id INTEGER REFERENCES ai_conversations(id),
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at   TEXT,
    is_deleted   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_notes_type   ON learning_notes(note_type);
CREATE INDEX idx_notes_enc    ON learning_notes(encounter_id);
CREATE INDEX idx_notes_status ON learning_notes(status);

-- 心得 ↔ 病案 双向引用
CREATE TABLE note_case_links (
    id       INTEGER PRIMARY KEY,
    note_id  INTEGER NOT NULL REFERENCES learning_notes(id) ON DELETE CASCADE,
    case_id  INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    relation TEXT DEFAULT '引证' CHECK (relation IN ('引证','讨论','对比')),
    notes    TEXT
);
CREATE UNIQUE INDEX idx_notecase_uniq ON note_case_links(note_id, case_id);

-- 笔记修改历史（保留每一稿，用于"学习轨迹"回顾）
CREATE TABLE note_revisions (
    id         INTEGER PRIMARY KEY,
    note_id    INTEGER NOT NULL REFERENCES learning_notes(id) ON DELETE CASCADE,
    content_md TEXT,
    word_count INTEGER,
    saved_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    change_note TEXT
);
CREATE INDEX idx_noterev_note ON note_revisions(note_id);

-- ============================================================
-- 导师点评：可挂在笔记、病案或跟诊记录上
-- ============================================================
CREATE TABLE mentor_comments (
    id          INTEGER PRIMARY KEY,
    target_type TEXT NOT NULL CHECK (target_type IN ('note','case','encounter')),
    target_id   INTEGER NOT NULL,
    mentor_id   INTEGER REFERENCES mentors(id),
    content     TEXT NOT NULL,
    comment_type TEXT CHECK (comment_type IN ('批注','评语','指正','补充')),
    is_ai_generated INTEGER NOT NULL DEFAULT 0, -- 明确区分 AI 模拟评语
    commented_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX idx_mcomment_target ON mentor_comments(target_type, target_id);
```

> ⚠️ **`is_ai_generated` 字段的意义**：导师点评是**师承关系中的权威内容**，绝不允许与 AI 生成内容混淆。CASE 可以生成"AI 视角的参考意见"，但必须显式标记，并在界面上与真实导师点评视觉区分。

### 3.9 AI 与审计

```sql
-- ============================================================
-- AI 对话留痕：满足"AI 辅助学术诚信"要求
-- ============================================================
CREATE TABLE ai_conversations (
    id           INTEGER PRIMARY KEY,
    title        TEXT,
    scene        TEXT CHECK (scene IN ('ocr_struct','qa','writing','polish','lookup','normalize')),
    model        TEXT,
    prompt_version TEXT,
    total_tokens INTEGER DEFAULT 0,
    total_cost_yuan REAL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at   TEXT
);
CREATE INDEX idx_aiconv_scene ON ai_conversations(scene);

CREATE TABLE ai_messages (
    id              INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('system','user','assistant','tool')),
    content         TEXT,
    content_json    TEXT,               -- 结构化内容（图片引用、工具调用）
    referenced_cases TEXT,              -- 引用的病案 id 列表（用于"带出处的回答"）
    tokens          INTEGER,
    latency_ms      INTEGER,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX idx_aimsg_conv ON ai_messages(conversation_id);

-- ============================================================
-- 审计日志：字段级修改留痕
-- ============================================================
CREATE TABLE audit_log (
    id         INTEGER PRIMARY KEY,
    table_name TEXT NOT NULL,
    record_id  INTEGER NOT NULL,
    action     TEXT NOT NULL CHECK (action IN ('INSERT','UPDATE','DELETE','RESTORE','MASK')),
    field_name TEXT,
    old_value  TEXT,
    new_value  TEXT,
    changed_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    note       TEXT                     -- 例如 'AI 归一化' / '患者信息脱敏'
);
CREATE INDEX idx_audit_target ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_time   ON audit_log(changed_at);

-- ============================================================
-- 应用设置（API Key 等敏感项放 .env，此处仅存非敏感偏好）
-- ============================================================
CREATE TABLE app_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TEXT
);
```

---

## 四、中文全文检索方案（含已实测的坑）

### 4.1 索引结构

采用 **单列聚合 + 外部内容表** 的简单模式：服务层在保存病案时把各表可检索内容聚合写入 `cases.search_text`，FTS5 只索引这一列。

```sql
CREATE VIRTUAL TABLE cases_fts USING fts5(
    search_text,
    content = 'cases',          -- 外部内容表，不重复存储正文
    content_rowid = 'id',
    tokenize = 'trigram'        -- 支持中文，无需外部分词器
);

-- 同步触发器
CREATE TRIGGER cases_fts_ai AFTER INSERT ON cases BEGIN
    INSERT INTO cases_fts(rowid, search_text) VALUES (new.id, new.search_text);
END;
CREATE TRIGGER cases_fts_ad AFTER DELETE ON cases BEGIN
    INSERT INTO cases_fts(cases_fts, rowid, search_text) VALUES ('delete', old.id, old.search_text);
END;
CREATE TRIGGER cases_fts_au AFTER UPDATE ON cases BEGIN
    INSERT INTO cases_fts(cases_fts, rowid, search_text) VALUES ('delete', old.id, old.search_text);
    INSERT INTO cases_fts(rowid, search_text) VALUES (new.id, new.search_text);
END;
```

`search_text` 的聚合内容建议：

```
主诉 + 现病史 + 中医病名 + 证型 + 治法 + 处方文本(药名+剂量) + 医嘱 + 学生批注 + 舌象 + 脉象
```

### 4.2 ⚠️ 必须实现的查询路由（否则静默失效）

实测确认：`trigram` 分词器按 3 字符滑窗建索引，**长度 < 3 的查询词永远匹配不到，且不报错，静默返回空集**。

而中医高频术语里 2 字词极多：**风热、气虚、血瘀、肝郁、脾虚、痰湿、阳虚、阴虚、湿热**……

```python
def build_search_clause(keyword: str) -> tuple[str, list]:
    """按查询长度路由：>=3 字走 FTS5，<3 字走 LIKE 回退。"""
    kw = keyword.strip()
    if len(kw) >= 3:
        # FTS5：有索引、有 bm25 相关性排序，快
        return "cases_fts MATCH ?", [escape_fts_query(kw)]
    else:
        # 2 字及以下：LIKE 回退。单机万级数据量性能完全可接受
        return "c.search_text LIKE ?", [f"%{kw}%"]

# 查询示例
# SELECT c.* FROM cases c
#   JOIN cases_fts f ON f.rowid = c.id
#  WHERE cases_fts MATCH ? AND c.is_deleted = 0
#  ORDER BY bm25(cases_fts);
```

**强制要求**：M1-9 回归测试**必须包含 2 字词用例**（风热/气虚/血瘀），防止此坑在重构中复发。
**v1.1 改进（F-4）**：jieba 预分词写入 `search_tokens` + `unicode61` 索引，可统一支持任意长度词。

### 4.3 拼音检索（可选增强）

`herbs.pinyin` 已预留。中药录入时可支持输入 `chaihu` 联想出"柴胡"，这是高频录入场景下很实用的提速手段。

---

## 五、关键取舍说明

| 取舍点 | 选择 | 理由与代价 |
|---|---|---|
| 四诊是否拆表 | **拆** `case_examinations`（1:1） | 代价是多一次 JOIN；收益是 `cases` 表保持可读，舌象/脉象可单独建索引供统计 |
| 诊断是否拆表 | **拆** `diagnoses`（1:N） | 一个病案确实常有主证+兼证+西医诊断并存，塞进 `cases` 会退化成非结构化 |
| 药味是否直连 cases | **经 `prescriptions` 中转** | 一个病案可能有多张方（内服+外洗+中成药），直连无法表达 |
| 是否用 ICD-11 / 国标编码 | **预留字段，不强制** | 中医术语标准化仍在演进，强制编码会严重拖累录入；字典仅做建议 |
| 中药名存原文还是标准名 | **两者都存** | `herb_name` 保真、`herb_name_norm` 供统计。药物频次分析的准确性依赖此设计 |
| 是否物理删除 | **软删除** | 学习资料误删代价高；`is_deleted` 配合回收站 |
| AI 生成内容如何处置 | **独立字段/表 + 显式标记** | `mentor_comments.is_ai_generated`、`learning_notes.is_ai_assisted`，杜绝与真实师承内容混淆 |
| 时间字段类型 | **TEXT 存 ISO8601** | SQLite 无原生日期类型；TEXT 可直接字符串比较与排序，且便于导出 |

---

## 六、数据字典种子来源（M1-3 待办）

| 字典表 | 种子来源 | 目标条数 |
|---|---|---|
| `herbs` + `herb_aliases` | 《中国药典》一部 / 《中药学》教材常用药 | 400–600 味（覆盖临床常用） |
| `syndromes` | 《中医诊断学》教材证候 + GB/T 15657 | 200–400 个 |
| `formulas` + `formula_items` | 《方剂学》教材正方 + 常用经方 | 150–300 首 |
| `terms_dictionary`（舌质/舌苔/脉象） | 《中医诊断学》四诊部分 | 各 30–60 条 |
| `terms_dictionary`（炮制/煎服法） | 《中药炮制学》常用法 + 处方常规 | 各 20–40 条 |

> **种子数据不必一次做全**。MVP 先做"常用药 200 味 + 常用证型 100 个"，其余在使用中按需补充——系统必须允许字典里没有的词正常录入（见设计原则 2）。

---

## 七、待确认事项

| # | 事项 | 需谁确认 |
|---|---|---|
| 1 | 国标/ICD-11 编码字段是否真要启用，还是仅预留 | 用户（涉及录入工作量） |
| 2 | 四诊拆表 vs 并入 `cases` —— 若认为统计需求不强可简化 | 用户 |
| 3 | 是否需要"病案模板/自定义字段"（F-7） | 用户（影响 M1-1 模型设计） |
| 4 | 种子字典的数据来源与版权（教材内容需注意） | 用户 |
| 5 | 脱敏字段清单（P-4） | 用户 |

---

## 附：本文件的 SQL 为草案

部分 DDL 未包含 `CHECK` 约束、`ON DELETE` 策略与全部索引，正式实现时以 `backend/alembic/versions/` 中的迁移文件为准。

**✅ 已实测可执行**：本文件中的全部 SQL 块已被 [`tools/verify_ddl.py`](../tools/verify_ddl.py) 自动抽取并在内存库中执行通过
（**34 张表 / 51 个索引 / 3 个触发器**均创建成功，FTS 触发器同步正常，检索路由验证通过，并完成了一次"病案 + 四诊 + 诊断 + 处方 + 心得 + 导师点评"的端到端写入冒烟测试）。
该脚本可在每次修改本文档后重跑，作为 DDL 的语法与集成回归：

```bash
python3 tools/verify_ddl.py
```

建议实现顺序：

1. `patients` / `mentors` / `encounters` / `cases`（主链路）
2. `case_examinations` / `diagnoses` / `treatments`
3. `herbs` / `herb_aliases` / `syndromes` / `formulas` / `formula_items` / `terms_dictionary`（字典）
4. `prescriptions` / `prescription_items`
5. `attachments` / `ocr_jobs` / `ocr_field_confidence` / `ocr_eval_*`
6. `learning_notes` / `note_case_links` / `note_revisions` / `mentor_comments`
7. `ai_conversations` / `ai_messages` / `audit_log` / `app_settings`
8. `cases_fts` 虚拟表与同步触发器
