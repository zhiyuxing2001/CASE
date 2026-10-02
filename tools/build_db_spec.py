#!/usr/bin/env python3
"""Generate the CASE database structure specification workbook.

The table definitions below are the single source of truth for the
field-level spec. Running this script regenerates the workbook, so the
spec stays reproducible and reviewable as code.

DESIGN PRINCIPLE (drives every table below)
-------------------------------------------
Structure only where it serves retrieval or analysis; free text
everywhere else. A student writing up a case should not have to write
prose and then also fill in twenty structured fields describing the same
thing. Case archives (病案) allow far more freedom and flexibility than
clinical medical records (病历), so this spec deliberately does not
decompose the history of present illness, nor keep separate tables for
chronic, communicable, personal, menstrual and other history.

What stays structured, and why:
  - tongue body / tongue coating / pulse  -> tongue and pulse statistics
  - TCM disease / syndrome                -> pattern frequency, retrieval
  - treatment principle / formula name    -> retrieval
  - prescription herbs                    -> herb frequency, dose analysis
  - course chaining (father_id)           -> retrieving a whole course

Column layout follows the sibling sleep-disease database spec:
    A 字段名称  B 中文释义  C 数据类型(SQLite)
    D 键描述    E 数据说明与数据约束
For columns holding JSON, the nested sub-schema is documented to the
right starting at column G.

Usage:
    python tools/build_db_spec.py [OUTPUT.xlsx]
"""

from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# --------------------------------------------------------------------------
# Shared column definitions reused across every per-visit child table.
# --------------------------------------------------------------------------
RECORD_KEY = ("record_id", "病历编号", "INTEGER", "PRIMARY KEY AUTOINCREMENT",
              "计算机生成：从1开始，以1为步长增序编号，与就诊信息记录表同步")
PATIENT_KEY = ("patient_id", "患者编号", "TEXT", "FOREIGN KEY",
               "计算机生成，与患者基本信息同步记录")
CREATED_AT = ("created_at", "创建时间", "TIMESTAMP", "",
              "计算机以“%Y-%m-%d %H:%M:%S”形式自动存储记录创建时间")
UPDATED_AT = ("updated_at", "修改时间", "TIMESTAMP", "",
              "计算机以“%Y-%m-%d %H:%M:%S”形式自动存储记录修改时间")

# --------------------------------------------------------------------------
# Table definitions
# --------------------------------------------------------------------------
TABLES: list[dict] = [

    # ================= 一、主数据 =================
    {
        "sheet": "01 患者基本信息表",
        "cn": "患者基本信息表",
        "en": "info_patient",
        "note": "患者主数据。patient_id（ULID）是系统内部唯一关联键；"
                "姓名与身份证号仅为记录性字段，上云前必须脱敏。",
        "fields": [
            ("id", "自动编号", "INTEGER", "PRIMARY KEY AUTOINCREMENT",
             "计算机生成：从1开始，以1为步长增序编号"),
            ("patient_id", "患者编号", "TEXT", "UNIQUE NOT NULL",
             "计算机生成：以ULID方式生成唯一编号，全库关联主键"),
            ("patient_name", "患者姓名", "TEXT", "NOT NULL",
             "必填，小于（包含）20个Unicode字符；上云前替换为代称"),
            ("name_masked", "姓名是否已脱敏", "BOOLEAN", "DEFAULT 0",
             "0为未脱敏，1为已脱敏；脱敏后 patient_name 不参与任何默认输出"),
            ("id_no", "身份证号", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串。独立于任何卡号存储；不参与检索与默认展示，"
             "上云前必须替换"),
            ("gender", "性别", "BOOLEAN", "NOT NULL DEFAULT 0",
             "必选，0为女性，1为男性，默认为0"),
            ("birthday", "出生日期", "DATE", "NOT NULL",
             "必填，以“%Y-%m-%d”形式记录"),
            ("nationality", "国籍", "TEXT", "NOT NULL",
             "必填，参考《GB/T 2659-2022》代表国家的代码"),
            ("ethnicity", "民族", "UNSIGNED TINYINT", "DEFAULT 0",
             "可选，默认为0，编号详见附表A1"),
            ("birthplace", "出生地", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("job", "职业", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("tel", "联系电话", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串；上云前必须脱敏"),
            ("addr_region", "居住地区", "TEXT", "DEFAULT ''",
             "选填，仅记录到区县一级，不记录详细门牌"),
            ("is_deleted", "是否删除", "BOOLEAN", "DEFAULT 0",
             "软删除标记，0为正常，1为已删除；学习类数据不做物理删除"),
            CREATED_AT,
            UPDATED_AT,
        ],
    },
    {
        "sheet": "02 就诊信息记录表",
        "cn": "就诊信息记录表",
        "en": "info_record",
        "note": "一次就诊一条记录，是全部临床子表的挂载点。"
                "father_id 单字段实现病程链：初诊指向自身，复诊指向初诊，"
                "因此取回整个病程只需一次索引查询。",
        "fields": [
            ("record_id", "病历编号", "INTEGER", "PRIMARY KEY AUTOINCREMENT",
             "计算机生成：从1开始，以1为步长增序编号"),
            PATIENT_KEY,
            ("father_id", "父节点病历编号", "INTEGER", "FOREIGN KEY NOT NULL",
             "初诊病历的父节点编号等于其自身病历编号；复诊病历的父节点编号"
             "等于其初诊病历编号。取整个病程：WHERE father_id = ?"),
            ("visit_no", "第几诊", "INTEGER", "NOT NULL DEFAULT 1",
             "初诊为1，其后依次递增"),
            ("visit_type", "就诊类型", "UNSIGNED TINYINT", "DEFAULT 0",
             "0为初诊，1为复诊，2为随访；详见附表A2"),
            ("clinic_date", "就诊日期", "DATE", "NOT NULL",
             "必填，以“%Y-%m-%d”形式记录"),
            ("age", "就诊年龄", "REAL", "NOT NULL",
             "必填，年龄范围：[0, 200]"),
            ("doctor_name", "就诊医师", "TEXT", "DEFAULT ''",
             "选填，记录原始姓名写法"),
            ("mentor_id", "带教老师编号", "TEXT", "FOREIGN KEY",
             "选填，关联 mentor；用于按老师统计用药与辨证规律"),
            ("department", "就诊科室", "TEXT", "DEFAULT ''",
             "选填。注意：就诊科室不等于疾病所属专科"),
            ("addr", "就诊地点", "TEXT", "DEFAULT ''",
             "选填，如医院与门诊名称"),
            ("solar_terms", "就诊节气", "UNSIGNED TINYINT", "DEFAULT 0",
             "计算机由就诊日期推算，编号从0开始，详见附表A3"),
            ("source_document_id", "来源单据编号", "TEXT", "FOREIGN KEY",
             "选填，关联 source_document；手工录入时为空"),
            ("is_deleted", "是否删除", "BOOLEAN", "DEFAULT 0",
             "软删除标记，0为正常，1为已删除"),
            CREATED_AT,
            UPDATED_AT,
        ],
    },
    {
        "sheet": "03 带教老师表",
        "cn": "带教老师表",
        "en": "mentor",
        "note": "师承关系的核心主数据。用于按老师聚合病案、"
                "统计用药与辨证规律。",
        "fields": [
            ("mentor_id", "老师编号", "TEXT", "PRIMARY KEY",
             "计算机生成：以ULID方式生成唯一编号"),
            ("mentor_name", "老师姓名", "TEXT", "NOT NULL",
             "必填，小于（包含）20个Unicode字符"),
            ("title", "职称", "TEXT", "DEFAULT ''",
             "选填，如主任医师、教授"),
            ("affiliation", "所属机构", "TEXT", "DEFAULT ''",
             "选填，如医院名称"),
            ("department", "所属科室", "TEXT", "DEFAULT ''",
             "选填，如消化科"),
            ("expertise", "擅长领域", "TEXT", "DEFAULT ''",
             "选填，用于按专长病种聚合统计"),
            ("is_primary", "是否主带教", "BOOLEAN", "DEFAULT 0",
             "0为否，1为是"),
            ("notes", "备注", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("is_deleted", "是否删除", "BOOLEAN", "DEFAULT 0",
             "软删除标记，0为正常，1为已删除"),
            CREATED_AT,
            UPDATED_AT,
        ],
    },

    # ================= 二、病案主体 =================
    {
        "sheet": "04 病案文本记录表",
        "cn": "病案文本记录表",
        "en": "case_narrative",
        "note": "病案主体，一次就诊一条。除舌质、舌苔、脉象外全部为自由文本，"
                "不做拆解。原设计中的现病史子结构、慢性非传染病史、传染病相关史、"
                "个人史、月经婚育史、其他病史、检查记录共 6 张表已合并至本表，"
                "以换取病案记录的自由度与灵活性。",
        "fields": [
            RECORD_KEY, PATIENT_KEY,
            ("complaint", "主诉", "TEXT", "NOT NULL",
             "必填，长度需小于（包含）20个Unicode字符。复诊可填“服药后复诊”"
             "或直接留空，不加额外标记"),
            ("present_illness", "现病史", "TEXT", "DEFAULT ''",
             "选填，自由文本，不拆解为时间点、诱发因素等子字段"),
            ("past_history", "既往史", "TEXT", "DEFAULT ''",
             "选填，自由文本。慢性病史、传染病史、手术外伤输血史一并记于此栏，"
             "不单独建表"),
            ("personal_history", "个人史及婚育史", "TEXT", "DEFAULT ''",
             "选填，自由文本。吸烟饮酒、职业接触、月经婚育等记于此栏"),
            ("allergy_history", "过敏史", "TEXT", "DEFAULT ''",
             "选填，自由文本"),
            ("body_of_tongue", "舌质", "TEXT", "DEFAULT ''",
             "选填。单独成列以支持舌象统计；建议取值见 dict_term（类型=舌质）"),
            ("fur_of_tongue", "舌苔", "TEXT", "DEFAULT ''",
             "选填。单独成列以支持舌象统计；建议取值见 dict_term（类型=舌苔）"),
            ("pulse", "切诊", "TEXT", "DEFAULT ''",
             "选填。单独成列以支持脉象统计；建议取值见 dict_term（类型=脉象）"),
            ("other_cond", "其他望闻切诊", "TEXT", "DEFAULT ''",
             "选填，自由文本，记录望诊、闻诊及按诊内容"),
            ("physical_exam", "体格检查", "TEXT", "DEFAULT ''",
             "选填，自由文本。真实样本中舌象脉象有时记于此栏，解析时需兼容"),
            ("auxiliary_exam", "辅助检查", "TEXT", "DEFAULT ''",
             "选填，自由文本。含检查日期、外院机构、项目与结果，不单独建表"),
            ("notes", "其他", "TEXT", "DEFAULT ''",
             "选填，自由文本，承载本表未覆盖的补充信息"),
            ("raw_ocr_text", "OCR 原文", "TEXT", "DEFAULT ''",
             "本表相关栏位的识别原文，只写不改，用于溯源"),
            CREATED_AT, UPDATED_AT,
        ],
    },

    # ================= 三、诊断与治疗 =================
    {
        "sheet": "05 诊断记录表",
        "cn": "诊断记录表",
        "en": "diagnosis",
        "note": "诊断以自由文本为主。仅证型保留一个可选的字典外键，"
                "用于证型频次统计；不拆分为一行一诊断的子表。",
        "fields": [
            RECORD_KEY, PATIENT_KEY,
            ("tcm_disease", "中医病名", "TEXT", "DEFAULT ''",
             "选填，自由文本，如“胃脘痛”“上腹痛”"),
            ("syndrome", "中医证型", "TEXT", "DEFAULT ''",
             "选填，证型原文，如“肝胃不和证”“湿热瘀阻、脾虚证”"),
            ("syndrome_id", "证型字典编号", "TEXT", "FOREIGN KEY",
             "选填，关联 dict_syndrome。录入时由字典联想写入，"
             "用于证型频次统计；未匹配时为空且不影响保存"),
            ("wm_diagnosis", "西医诊断", "TEXT", "DEFAULT ''",
             "选填，自由文本，多条诊断以中文分号分隔，"
             "如“带状疱疹后神经痛；睡眠障碍；2型糖尿病”"),
            ("patterns_analysis", "辨证分析", "TEXT", "DEFAULT ''",
             "选填，自由文本。真实样本的手写教学表单设有独立栏位，"
             "用于记录辨证推理过程"),
            ("differential_diagnosis", "鉴别诊断", "TEXT", "DEFAULT ''",
             "选填，自由文本"),
            ("notes", "其他", "TEXT", "DEFAULT ''",
             "选填，自由文本"),
            ("raw_ocr_text", "OCR 原文", "TEXT", "DEFAULT ''",
             "本表相关栏位的识别原文，只写不改，用于溯源"),
            CREATED_AT, UPDATED_AT,
        ],
    },
    {
        "sheet": "06 治疗记录表",
        "cn": "治疗记录表",
        "en": "treatment",
        "note": "处方级信息，一次就诊一条。药味明细见 07 处方药味明细表。"
                "治法为学生书写病案时的独立栏目，故单列。",
        "fields": [
            RECORD_KEY, PATIENT_KEY,
            ("treatment_principle", "治法", "TEXT", "DEFAULT ''",
             "选填，自由文本，如“清热祛湿、理气活血止痛”。"
             "真实样本的手写教学表单设有独立“治法”栏"),
            ("formula_name", "方剂名", "TEXT", "DEFAULT ''",
             "选填，如“柴胡疏肝散”。对应手写表单“方拟____加减治之”的空位"),
            ("formula_id", "方剂字典编号", "TEXT", "FOREIGN KEY",
             "选填，关联 dict_formula；用于方剂使用频次统计"),
            ("dose_count", "付数", "INTEGER", "DEFAULT 0",
             "选填，默认为0，单位为付（剂）"),
            ("decoction", "煎煮法", "TEXT", "DEFAULT ''",
             "选填，自由文本，如“水煎服”“机械煎药（含2袋）”。"
             "是否代煎直接记录于此栏，不另设布尔字段"),
            ("usage", "用法", "TEXT", "DEFAULT ''",
             "选填，如“日一剂，分早晚温服”“每天一次（10点）”"),
            ("advice", "医嘱与调护", "TEXT", "DEFAULT ''",
             "选填，自由文本，含饮食起居调摄与复诊安排"),
            ("other_treatment", "其他治疗", "TEXT", "DEFAULT ''",
             "选填，自由文本。中成药、西医治疗、针灸外治等一并记于此栏"),
            ("raw_ocr_text", "OCR 原文", "TEXT", "DEFAULT ''",
             "处方原文，只写不改，用于溯源"),
            CREATED_AT, UPDATED_AT,
        ],
    },
    {
        "sheet": "07 处方药味明细表",
        "cn": "处方药味明细表",
        "en": "prescription_item",
        "note": "本库药物频次与剂量分析的核心表。处方天然就是一串药味，"
                "按行记录不是冗余而是数据的本来形态，故保留结构化；"
                "治疗记录表不再另存一份 JSON 副本，仅保留 raw_ocr_text 保真。",
        "fields": [
            ("item_id", "明细编号", "INTEGER", "PRIMARY KEY AUTOINCREMENT",
             "计算机生成：从1开始，以1为步长增序编号"),
            RECORD_KEY, PATIENT_KEY,
            ("prescription_no", "第几张方", "INTEGER", "DEFAULT 1",
             "同一病历内有多张方时的序号"),
            ("sequence", "方中顺序", "INTEGER", "DEFAULT 0",
             "药味在方中的排列顺序，君臣佐使顺序有意义"),
            ("herb_id", "药材编号", "TEXT", "FOREIGN KEY",
             "选填，关联 dict_herb；未匹配到字典时为空，不影响保存"),
            ("herb_name", "药味", "TEXT", "NOT NULL",
             "必填，录入原文，如“生地”“盐黄柏”，用于保真与回看"),
            ("herb_name_norm", "归一药名", "TEXT", "DEFAULT ''",
             "选填，经字典别名归一后的标准名，如“生地黄”；统计以此列为准"),
            ("dose", "剂量", "REAL", "DEFAULT 0",
             "选填，默认为0，指标记录不含单位"),
            ("unit", "单位", "TEXT", "DEFAULT 'g'",
             "选填，默认为g。后处理须做单位白名单校验：g 常被 OCR 误识为 9"),
            ("total_quantity", "总量", "REAL", "DEFAULT 0",
             "选填，默认为0。HIS 单据中总量 = 剂量 × 付数，"
             "该等式用作 OCR 结果的确定性校验，不成立则标记待校对"),
            ("frequency", "频次", "TEXT", "DEFAULT ''",
             "选填，如 BID、QD；仅 HIS 单据具备此信息"),
            ("processing", "炮制", "TEXT", "DEFAULT ''",
             "选填，如炒、炙、醋制、盐制、砂烫"),
            ("decoction_note", "煎煮要求", "TEXT", "DEFAULT ''",
             "选填，如先煎、后下、包煎、烊化、冲服"),
            ("role", "君臣佐使", "TEXT", "DEFAULT ''",
             "选填，取值为君、臣、佐、使之一"),
            ("needs_review", "是否待校对", "BOOLEAN", "DEFAULT 0",
             "0为正常，1为需人工复核；由置信度与算术校验共同决定"),
            ("confidence", "识别置信度", "REAL", "DEFAULT 1",
             "选填，人工录入为1；OCR 结果取融合后置信度"),
            CREATED_AT,
        ],
    },

    # ================= 四、字典 =================
    {
        "sheet": "08 中药字典表",
        "cn": "中药字典表",
        "en": "dict_herb",
        "note": "炮制品作为独立条目并指向基原：盐黄柏、醋莪术、炒酸枣仁"
                "各自成条，parent_herb_id 指向基原药材。",
        "fields": [
            ("herb_id", "药材编号", "TEXT", "PRIMARY KEY",
             "计算机生成：以ULID方式生成唯一编号"),
            ("herb_name", "标准药名", "TEXT", "UNIQUE NOT NULL",
             "必填，标准名，如“生地黄”“盐黄柏”"),
            ("pinyin", "拼音", "TEXT", "DEFAULT ''",
             "选填，便于拼音检索，如 sheng di huang"),
            ("parent_herb_id", "基原药材编号", "TEXT", "FOREIGN KEY",
             "选填，自引用。炮制品指向其基原，如盐黄柏→黄柏；基原药材为空"),
            ("is_processed", "是否炮制品", "BOOLEAN", "DEFAULT 0",
             "0为基原药材，1为炮制品"),
            ("processing", "炮制方法", "TEXT", "DEFAULT ''",
             "选填，炮制品的炮制方法，如盐炙、醋炙、炒、砂烫"),
            ("category", "类别", "TEXT", "DEFAULT ''",
             "选填，如解表药、清热药、补虚药"),
            ("nature", "四气", "TEXT", "DEFAULT ''",
             "选填，寒、热、温、凉、平"),
            ("flavor", "五味", "TEXT", "DEFAULT ''",
             "选填，辛、甘、酸、苦、咸、淡、涩"),
            ("meridians", "归经", "TEXT", "DEFAULT ''",
             "选填，多条以逗号分隔"),
            ("functions", "功效", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("standard_code", "标准编码", "TEXT", "DEFAULT ''",
             "选填，药典或国标编码，仅作建议不强制"),
            ("is_common", "是否常用药", "BOOLEAN", "DEFAULT 1",
             "0为否，1为是；影响录入联想排序"),
            ("is_active", "是否启用", "BOOLEAN", "DEFAULT 1",
             "0为停用，1为启用"),
            CREATED_AT,
        ],
    },
    {
        "sheet": "09 中药别名表",
        "cn": "中药别名表",
        "en": "dict_herb_alias",
        "note": "同名异物与同物异名的显式建模。除统计归一外，"
                "还承担 OCR 药名纠错：错误几乎全为形近字（黄芩→黄苓、黄柏→黄相），"
                "而正确写法多在字典内，可用编辑距离与拼音相似度自动建议。",
        "fields": [
            ("alias_id", "别名编号", "INTEGER", "PRIMARY KEY AUTOINCREMENT",
             "计算机生成：从1开始，以1为步长增序编号"),
            ("herb_id", "药材编号", "TEXT", "FOREIGN KEY NOT NULL",
             "必填，关联 dict_herb"),
            ("alias", "别名", "TEXT", "NOT NULL",
             "必填，如“生地”“杭白芍”“川贝”"),
            ("alias_type", "别名类型", "UNSIGNED TINYINT", "DEFAULT 0",
             "0为异名，1为简称，2为处方名，3为炮制品，4为错写；详见附表A4"),
            ("ambiguity_note", "同名异物提示", "TEXT", "DEFAULT ''",
             "选填。如“川贝”可能指多种贝母，在此说明以提示人工确认"),
            ("source", "依据来源", "TEXT", "DEFAULT ''",
             "选填，别名收录依据"),
            CREATED_AT,
        ],
    },
    {
        "sheet": "10 证型字典表",
        "cn": "证型字典表",
        "en": "dict_syndrome",
        "note": "证候标准化与频次统计的基础。",
        "fields": [
            ("syndrome_id", "证型编号", "TEXT", "PRIMARY KEY",
             "计算机生成：以ULID方式生成唯一编号"),
            ("syndrome_name", "证型名称", "TEXT", "UNIQUE NOT NULL",
             "必填，如“肝胃不和证”“湿热瘀阻证”"),
            ("category", "辨证体系", "TEXT", "DEFAULT ''",
             "选填，如脏腑辨证、六经辨证、卫气营血辨证、三焦辨证"),
            ("standard_code", "标准编码", "TEXT", "DEFAULT ''",
             "选填，国标编码，仅作建议不强制"),
            ("key_symptoms", "主症要点", "TEXT", "DEFAULT ''",
             "选填，用于录入联想与学习提示"),
            ("treatment", "常用治法", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("common_formula", "代表方", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("description", "说明", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("is_active", "是否启用", "BOOLEAN", "DEFAULT 1",
             "0为停用，1为启用"),
            CREATED_AT,
        ],
    },
    {
        "sheet": "11 方剂字典表",
        "cn": "方剂字典表",
        "en": "dict_formula",
        "note": "用于识别处方所本的基础方，支持“方剂 vs 实际处方”的加减分析。",
        "fields": [
            ("formula_id", "方剂编号", "TEXT", "PRIMARY KEY",
             "计算机生成：以ULID方式生成唯一编号"),
            ("formula_name", "方剂名称", "TEXT", "UNIQUE NOT NULL",
             "必填，如“柴胡疏肝散”"),
            ("alias", "别名", "TEXT", "DEFAULT ''",
             "选填，别名或简称"),
            ("source", "出处", "TEXT", "DEFAULT ''",
             "选填，如《景岳全书》"),
            ("category", "类别", "TEXT", "DEFAULT ''",
             "选填，如和解剂、理气剂"),
            ("functions", "功用", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("indications", "主治", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("syndrome_id", "主治病证编号", "TEXT", "FOREIGN KEY",
             "选填，关联 dict_syndrome"),
            ("composition_text", "组成原文", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("usage_text", "用法原文", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("is_active", "是否启用", "BOOLEAN", "DEFAULT 1",
             "0为停用，1为启用"),
            CREATED_AT,
        ],
    },
    {
        "sheet": "12 通用术语字典表",
        "cn": "通用术语字典表",
        "en": "dict_term",
        "note": "承载舌质、舌苔、脉象、炮制、煎服法、用法等轻量字典，"
                "并记录使用频次用于录入联想排序。",
        "fields": [
            ("term_id", "术语编号", "INTEGER", "PRIMARY KEY AUTOINCREMENT",
             "计算机生成：从1开始，以1为步长增序编号"),
            ("term_type", "术语类型", "UNSIGNED TINYINT", "NOT NULL",
             "1舌质，2舌苔，3脉象，4面色，5炮制，6煎服法，7用法，"
             "8中医病名，9治法，10剂型；详见附表A5"),
            ("term", "术语", "TEXT", "NOT NULL",
             "必填，术语原文，如“淡红”“薄白”“弦滑”"),
            ("standard_code", "标准编码", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("parent_id", "上级术语编号", "INTEGER", "FOREIGN KEY",
             "选填，自引用，用于术语的层级归类"),
            ("description", "说明", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("usage_count", "使用频次", "INTEGER", "DEFAULT 0",
             "计算机维护，用于录入联想排序"),
            ("is_active", "是否启用", "BOOLEAN", "DEFAULT 1",
             "0为停用，1为启用"),
        ],
    },

    # ================= 五、跟师学习 =================
    {
        "sheet": "13 学习笔记表",
        "cn": "学习笔记表",
        "en": "learning_note",
        "note": "以 note_type 区分跟诊日志与学习心得，"
                "避免为相似结构建多张表。",
        "fields": [
            ("note_id", "笔记编号", "TEXT", "PRIMARY KEY",
             "计算机生成：以ULID方式生成唯一编号"),
            ("note_type", "笔记类型", "UNSIGNED TINYINT", "NOT NULL DEFAULT 0",
             "0为跟诊日志，1为学习心得，2为读书笔记，3为病例讨论，4为阶段总结；"
             "详见附表A6"),
            ("title", "标题", "TEXT", "NOT NULL",
             "必填，小于（包含）100个Unicode字符"),
            ("content_md", "正文", "TEXT", "DEFAULT ''",
             "选填，Markdown 富文本正文"),
            ("status", "状态", "UNSIGNED TINYINT", "DEFAULT 0",
             "0为草稿，1为已发布，2为已归档；详见附表A7"),
            ("record_id", "关联病历编号", "INTEGER", "FOREIGN KEY",
             "选填，关联 info_record"),
            ("mentor_id", "带教老师编号", "TEXT", "FOREIGN KEY",
             "选填，关联 mentor"),
            ("word_count", "字数", "INTEGER", "DEFAULT 0",
             "计算机维护，用于学习进度统计"),
            ("is_ai_assisted", "是否使用AI辅助", "BOOLEAN", "DEFAULT 0",
             "0为否，1为是；学术诚信留痕，界面须显式标注"),
            ("is_deleted", "是否删除", "BOOLEAN", "DEFAULT 0",
             "软删除标记，0为正常，1为已删除"),
            CREATED_AT, UPDATED_AT,
        ],
    },
    {
        "sheet": "14 导师点评表",
        "cn": "导师点评表",
        "en": "mentor_comment",
        "note": "师承关系中的权威内容。is_ai_generated 字段确保 AI 生成内容"
                "绝不被误认为真实导师点评，界面须视觉区分。",
        "fields": [
            ("comment_id", "点评编号", "INTEGER", "PRIMARY KEY AUTOINCREMENT",
             "计算机生成：从1开始，以1为步长增序编号"),
            ("target_type", "点评对象类型", "UNSIGNED TINYINT", "NOT NULL",
             "0为学习笔记，1为病案，2为就诊记录；详见附表A8"),
            ("target_id", "点评对象编号", "TEXT", "NOT NULL",
             "必填，按 target_type 指向对应表的主键"),
            ("mentor_id", "老师编号", "TEXT", "FOREIGN KEY",
             "选填，关联 mentor"),
            ("content", "点评内容", "TEXT", "NOT NULL",
             "必填，点评原文"),
            ("comment_type", "点评类型", "UNSIGNED TINYINT", "DEFAULT 0",
             "0为批注，1为评语，2为指正，3为补充；详见附表A9"),
            ("is_ai_generated", "是否AI生成", "BOOLEAN", "DEFAULT 0",
             "0为真实导师点评，1为AI生成的参考意见；界面须视觉区分"),
            ("commented_at", "点评时间", "TIMESTAMP", "NOT NULL",
             "必填，以“%Y-%m-%d %H:%M:%S”形式记录"),
            CREATED_AT,
        ],
    },
    {
        "sheet": "15 笔记与病案关联表",
        "cn": "笔记与病案关联表",
        "en": "note_record_link",
        "note": "学习心得与病案的双向引用，支持“从心得跳病案”与反向追溯。",
        "fields": [
            ("link_id", "关联编号", "INTEGER", "PRIMARY KEY AUTOINCREMENT",
             "计算机生成：从1开始，以1为步长增序编号"),
            ("note_id", "笔记编号", "TEXT", "FOREIGN KEY NOT NULL",
             "必填，关联 learning_note"),
            ("record_id", "病历编号", "INTEGER", "FOREIGN KEY NOT NULL",
             "必填，关联 info_record"),
            ("relation", "关联类型", "UNSIGNED TINYINT", "DEFAULT 0",
             "0为引证，1为讨论，2为对比；详见附表A10"),
            ("notes", "说明", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            CREATED_AT,
        ],
    },

    # ================= 六、来源与溯源 =================
    {
        "sheet": "16 来源单据表",
        "cn": "来源单据表",
        "en": "source_document",
        "note": "真实样本显示同一病程的数据可能来自手写教学表单、"
                "HIS 打印件或 HIS 界面截图，来源不同则解析策略与可信度不同。",
        "fields": [
            ("doc_id", "单据编号", "TEXT", "PRIMARY KEY",
             "计算机生成：以ULID方式生成唯一编号"),
            ("doc_type", "单据类型", "UNSIGNED TINYINT", "NOT NULL",
             "0为手写教学表单，1为HIS门诊病历，2为HIS医嘱截图，"
             "3为检验报告，4为其他；详见附表A11"),
            ("template_name", "表单模板名", "TEXT", "DEFAULT ''",
             "选填，如“跟师学习临床医案”“门诊病历”"),
            ("hospital", "机构名称", "TEXT", "DEFAULT ''",
             "选填，如医院名称"),
            ("page_count", "页数", "INTEGER", "DEFAULT 1",
             "选填，默认为1"),
            ("ocr_strategy", "解析策略", "UNSIGNED TINYINT", "DEFAULT 0",
             "0为手写模式，1为印刷表格模式，2为混合模式；详见附表A12"),
            ("file_name_origin", "原始文件名", "TEXT", "DEFAULT ''",
             "选填。真实样本的文件名形如“日期-患者-主病”，可辅助推断元数据"),
            ("notes", "备注", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            CREATED_AT,
        ],
    },
    {
        "sheet": "17 附件表",
        "cn": "附件表",
        "en": "attachment",
        "note": "文件本体存于 data/attachments/，库中仅存路径与哈希。"
                "sha256 用于去重与完整性校验。",
        "fields": [
            ("attach_id", "附件编号", "TEXT", "PRIMARY KEY",
             "计算机生成：以ULID方式生成唯一编号"),
            ("record_id", "病历编号", "INTEGER", "FOREIGN KEY",
             "选填，可先上传后关联"),
            ("doc_id", "单据编号", "TEXT", "FOREIGN KEY",
             "选填，关联 source_document"),
            ("file_path", "文件路径", "TEXT", "NOT NULL",
             "必填，相对 data/ 的路径"),
            ("thumb_path", "缩略图路径", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("file_type", "文件类型", "UNSIGNED TINYINT", "NOT NULL",
             "0为图片，1为PDF；详见附表A13"),
            ("mime_type", "MIME类型", "TEXT", "DEFAULT ''",
             "选填，按文件实际内容判断"),
            ("file_size", "文件大小", "INTEGER", "DEFAULT 0",
             "选填，单位：字节"),
            ("width", "宽度", "INTEGER", "DEFAULT 0",
             "选填，单位：像素"),
            ("height", "高度", "INTEGER", "DEFAULT 0",
             "选填，单位：像素"),
            ("sha256", "文件哈希", "TEXT", "DEFAULT ''",
             "选填，用于去重与完整性校验"),
            ("page_no", "页码", "INTEGER", "DEFAULT 1",
             "选填，多页单据中的页码"),
            ("sort_order", "排序", "INTEGER", "DEFAULT 0",
             "选填，同一病历内附件的排列顺序"),
            ("is_deleted", "是否删除", "BOOLEAN", "DEFAULT 0",
             "软删除标记，0为正常，1为已删除"),
            CREATED_AT,
        ],
    },
    {
        "sheet": "18 OCR作业表",
        "cn": "OCR作业表",
        "en": "ocr_job",
        "note": "一次识别的完整留痕：双通道结果、提示词版本、成本与耗时。"
                "提示词固定前缀须字节级稳定以命中 DeepSeek 上下文缓存。",
        "fields": [
            ("job_id", "作业编号", "TEXT", "PRIMARY KEY",
             "计算机生成：以ULID方式生成唯一编号"),
            ("attach_id", "附件编号", "TEXT", "FOREIGN KEY NOT NULL",
             "必填，关联 attachment"),
            ("record_id", "病历编号", "INTEGER", "FOREIGN KEY",
             "选填，关联 info_record"),
            ("status", "状态", "UNSIGNED TINYINT", "NOT NULL DEFAULT 0",
             "0为待处理，1为进行中，2为成功，3为失败，4为已校对，5为已废弃；"
             "详见附表A14"),
            ("vision_engine", "通道A引擎", "TEXT", "DEFAULT 'ocrmac/Vision'",
             "选填，本地 macOS Vision 引擎标识"),
            ("vision_text", "通道A文本", "TEXT", "DEFAULT ''",
             "选填，本地 OCR 纯文本结果"),
            ("vision_json", "通道A结构化结果", "JSON", "DEFAULT []",
             "选填，Array[Object]，含 text、confidence、bbox 三键"),
            ("vision_ms", "通道A耗时", "INTEGER", "DEFAULT 0",
             "选填，单位：毫秒"),
            ("model", "通道B模型", "TEXT", "DEFAULT ''",
             "选填，如 deepseek-flash"),
            ("prompt_version", "提示词版本", "TEXT", "DEFAULT ''",
             "选填，用于回归对比"),
            ("structured_json", "通道B结构化结果", "JSON", "DEFAULT {}",
             "选填，经 JSON Output 约束的输出"),
            ("degraded_mode", "降级模式", "UNSIGNED TINYINT", "DEFAULT 0",
             "0为双通道，1为仅通道A（离线降级）；详见附表A15"),
            ("tokens_in", "输入tokens", "INTEGER", "DEFAULT 0",
             "选填，默认为0"),
            ("tokens_cached", "缓存命中tokens", "INTEGER", "DEFAULT 0",
             "选填，缓存命中单价约为未命中的1/50"),
            ("tokens_out", "输出tokens", "INTEGER", "DEFAULT 0",
             "选填，默认为0"),
            ("cost_yuan", "费用(元)", "REAL", "DEFAULT 0",
             "选填，默认为0"),
            ("duration_ms", "总耗时", "INTEGER", "DEFAULT 0",
             "选填，单位：毫秒"),
            ("error_message", "错误信息", "TEXT", "DEFAULT ''",
             "选填，失败时记录错误原因"),
            CREATED_AT,
        ],
        "json_subs": [
            ("vision_json", "通道A结构化结果", "Array[Object]", [
                ("text", "识别文本", "string"),
                ("confidence", "置信度", "float"),
                ("bbox", "坐标框", "[float]"),
            ]),
        ],
    },
    {
        "sheet": "19 OCR字段置信度表",
        "cn": "OCR字段置信度表",
        "en": "ocr_field_confidence",
        "note": "驱动校对界面高亮，同时是 OCR 评测的数据来源。"
                "真实样本显示印刷体置信度0.5~1.0、手写体约0.3，可据此路由。",
        "fields": [
            ("conf_id", "记录编号", "INTEGER", "PRIMARY KEY AUTOINCREMENT",
             "计算机生成：从1开始，以1为步长增序编号"),
            ("job_id", "作业编号", "TEXT", "FOREIGN KEY NOT NULL",
             "必填，关联 ocr_job"),
            ("field_path", "字段路径", "TEXT", "NOT NULL",
             "必填，如 prescription_item[3].dose"),
            ("value", "字段值", "TEXT", "DEFAULT ''",
             "选填，识别得到的值"),
            ("confidence", "置信度", "REAL", "DEFAULT 0",
             "选填，范围：[0, 1]。印刷体约0.5~1.0，手写体约0.3"),
            ("source", "来源", "UNSIGNED TINYINT", "DEFAULT 0",
             "0为通道A，1为通道B，2为融合，3为字典校验；详见附表A16"),
            ("needs_review", "是否待校对", "BOOLEAN", "DEFAULT 0",
             "0为正常，1为需人工复核；低置信或算术校验失败时置1"),
            ("evidence", "依据", "TEXT", "DEFAULT ''",
             "选填，如依据通道A的哪一行与坐标"),
            ("suggestion", "归一建议", "TEXT", "DEFAULT ''",
             "选填，如“生地”→“生地黄”"),
            CREATED_AT,
        ],
    },

    # ================= 七、系统 =================
    {
        "sheet": "20 审计日志表",
        "cn": "审计日志表",
        "en": "audit_log",
        "note": "字段级修改留痕。学习记录的可信性依赖不可抵赖的修改历史。",
        "fields": [
            ("log_id", "日志编号", "INTEGER", "PRIMARY KEY AUTOINCREMENT",
             "计算机生成：从1开始，以1为步长增序编号"),
            ("table_name", "表名", "TEXT", "NOT NULL",
             "必填，被修改的表名"),
            ("record_pk", "记录主键", "TEXT", "NOT NULL",
             "必填，被修改记录的主键值"),
            ("action", "操作类型", "UNSIGNED TINYINT", "NOT NULL",
             "0为新增，1为修改，2为删除，3为恢复，4为脱敏；详见附表A17"),
            ("field_name", "字段名", "TEXT", "DEFAULT ''",
             "选填，修改操作记录到字段级"),
            ("old_value", "旧值", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("new_value", "新值", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            ("changed_at", "修改时间", "TIMESTAMP", "NOT NULL",
             "必填，以“%Y-%m-%d %H:%M:%S”形式记录"),
            ("note", "备注", "TEXT", "DEFAULT ''",
             "选填，如“AI归一化”“患者信息脱敏”"),
        ],
    },
    {
        "sheet": "21 应用设置表",
        "cn": "应用设置表",
        "en": "app_setting",
        "note": "仅存非敏感偏好。API Key 等敏感项存于 .env，不入库、不入 Git。",
        "fields": [
            ("key", "设置项", "TEXT", "PRIMARY KEY",
             "必填，设置项名称"),
            ("value", "设置值", "TEXT", "DEFAULT ''",
             "选填，默认为空字符串"),
            UPDATED_AT,
        ],
    },
]

# --------------------------------------------------------------------------
# Enumeration appendix (TINYINT code tables)
# --------------------------------------------------------------------------
ENUMS: list[tuple[str, str, list[tuple[int, str]]]] = [
    ("A1", "民族（ethnicity，参考 GB/T 3304-1991，节选）", [
        (0, "未填"), (1, "汉族"), (2, "蒙古族"), (3, "回族"), (4, "藏族"),
        (5, "维吾尔族"), (6, "苗族"), (7, "彝族"), (8, "壮族"), (9, "布依族"),
        (10, "朝鲜族"), (11, "满族"), (12, "侗族"), (13, "瑶族"), (14, "白族"),
        (99, "其他（详见国标）"),
    ]),
    ("A2", "就诊类型（visit_type）", [
        (0, "初诊"), (1, "复诊"), (2, "随访"),
    ]),
    ("A3", "二十四节气（solar_terms，编号从0起）", [
        (0, "立春"), (1, "雨水"), (2, "惊蛰"), (3, "春分"), (4, "清明"), (5, "谷雨"),
        (6, "立夏"), (7, "小满"), (8, "芒种"), (9, "夏至"), (10, "小暑"), (11, "大暑"),
        (12, "立秋"), (13, "处暑"), (14, "白露"), (15, "秋分"), (16, "寒露"), (17, "霜降"),
        (18, "立冬"), (19, "小雪"), (20, "大雪"), (21, "冬至"), (22, "小寒"), (23, "大寒"),
    ]),
    ("A4", "别名类型（dict_herb_alias.alias_type）", [
        (0, "异名"), (1, "简称"), (2, "处方名"), (3, "炮制品"), (4, "错写"),
    ]),
    ("A5", "术语类型（dict_term.term_type）", [
        (1, "舌质"), (2, "舌苔"), (3, "脉象"), (4, "面色"), (5, "炮制"),
        (6, "煎服法"), (7, "用法"), (8, "中医病名"), (9, "治法"), (10, "剂型"),
    ]),
    ("A6", "笔记类型（learning_note.note_type）", [
        (0, "跟诊日志"), (1, "学习心得"), (2, "读书笔记"), (3, "病例讨论"), (4, "阶段总结"),
    ]),
    ("A7", "笔记状态（learning_note.status）", [
        (0, "草稿"), (1, "已发布"), (2, "已归档"),
    ]),
    ("A8", "点评对象类型（mentor_comment.target_type）", [
        (0, "学习笔记"), (1, "病案"), (2, "就诊记录"),
    ]),
    ("A9", "点评类型（mentor_comment.comment_type）", [
        (0, "批注"), (1, "评语"), (2, "指正"), (3, "补充"),
    ]),
    ("A10", "关联类型（note_record_link.relation）", [
        (0, "引证"), (1, "讨论"), (2, "对比"),
    ]),
    ("A11", "单据类型（source_document.doc_type）", [
        (0, "手写教学表单"), (1, "HIS门诊病历"), (2, "HIS医嘱截图"),
        (3, "检验报告"), (4, "其他"),
    ]),
    ("A12", "解析策略（source_document.ocr_strategy）", [
        (0, "手写模式"), (1, "印刷表格模式"), (2, "混合模式"),
    ]),
    ("A13", "文件类型（attachment.file_type）", [
        (0, "图片"), (1, "PDF"),
    ]),
    ("A14", "OCR状态（ocr_job.status）", [
        (0, "待处理"), (1, "进行中"), (2, "成功"), (3, "失败"),
        (4, "已校对"), (5, "已废弃"),
    ]),
    ("A15", "降级模式（ocr_job.degraded_mode）", [
        (0, "双通道"), (1, "仅通道A（离线降级）"),
    ]),
    ("A16", "置信度来源（ocr_field_confidence.source）", [
        (0, "通道A"), (1, "通道B"), (2, "融合"), (3, "字典校验"),
    ]),
    ("A17", "操作类型（audit_log.action）", [
        (0, "新增"), (1, "修改"), (2, "删除"), (3, "恢复"), (4, "脱敏"),
    ]),
]

# --------------------------------------------------------------------------
# Styling
# --------------------------------------------------------------------------
TITLE_FONT = Font(bold=True, size=12)
HEADER_FONT = Font(bold=True, size=10, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="4472C4")
SUB_FONT = Font(bold=True, size=10, color="FFFFFF")
SUB_FILL = PatternFill("solid", fgColor="ED7D31")
MONO = Font(name="Menlo", size=9)
BODY = Font(size=10)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
HEADERS = ["字段名称", "中文释义", "数据类型（SQLite）", "键描述", "数据说明与数据约束"]
WIDTHS = [26, 22, 20, 26, 62]

GROUPS: dict[str, list[str]] = {
    "一、主数据": ["info_patient", "info_record", "mentor"],
    "二、病案主体": ["case_narrative"],
    "三、诊断与治疗": ["diagnosis", "treatment", "prescription_item"],
    "四、字典": ["dict_herb", "dict_herb_alias", "dict_syndrome",
                 "dict_formula", "dict_term"],
    "五、跟师学习": ["learning_note", "mentor_comment", "note_record_link"],
    "六、来源与溯源": ["source_document", "attachment", "ocr_job",
                       "ocr_field_confidence"],
    "七、系统": ["audit_log", "app_setting"],
}


def style_header(cells, font, fill):
    for c in cells:
        c.font = font
        c.fill = fill
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER


def build_table_sheet(wb: Workbook, spec: dict) -> None:
    ws = wb.create_sheet(spec["sheet"])
    last_col = get_column_letter(len(HEADERS))

    ws.merge_cells(f"A1:{last_col}1")
    ws["A1"] = f"{spec['cn']}（{spec['en']}）"
    ws["A1"].font = TITLE_FONT
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells(f"A2:{last_col}2")
    ws["A2"] = spec["note"]
    ws["A2"].font = Font(size=9, italic=True, color="595959")
    ws["A2"].alignment = WRAP

    for i, h in enumerate(HEADERS, start=1):
        ws.cell(row=3, column=i, value=h)
    style_header(ws[3][:len(HEADERS)], HEADER_FONT, HEADER_FILL)

    row = 4
    for field in spec["fields"]:
        for i, val in enumerate(field, start=1):
            cell = ws.cell(row=row, column=i, value=val)
            cell.font = MONO if i in (1, 3) else BODY
            cell.alignment = WRAP
            cell.border = BORDER
        row += 1

    for i, w in enumerate(WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A4"

    subs = spec.get("json_subs")
    if subs:
        base = len(HEADERS) + 2
        for j, (col, cn, kind, subfields) in enumerate(subs):
            start = base + j * 3
            c1, c2, c3 = (get_column_letter(start + k) for k in range(3))
            ws.merge_cells(f"{c1}3:{c2}3")
            ws[f"{c1}3"] = f"{cn}（{col}）"
            ws[f"{c3}3"] = kind
            style_header([ws[f"{c1}3"], ws[f"{c2}3"], ws[f"{c3}3"]], SUB_FONT, SUB_FILL)
            for k, (name, label, typ) in enumerate(subfields, start=4):
                ws[f"{c1}{k}"] = f"{name}<{typ}>"
                ws[f"{c1}{k}"].font = MONO
                ws[f"{c2}{k}"] = label
                ws[f"{c2}{k}"].font = BODY
                for cc in (c1, c2, c3):
                    ws[f"{cc}{k}"].border = BORDER
            ws.column_dimensions[c1].width = 30
            ws.column_dimensions[c2].width = 34
            ws.column_dimensions[c3].width = 16


def build_overview(wb: Workbook) -> None:
    ws = wb.create_sheet("00 总览", 0)
    ws["A1"] = "CASE 数据库结构说明书（Clinical Archives for Student Encounters）"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells("A1:E1")

    ws["A2"] = ("设计原则：结构化只保留支撑检索与分析的部分，其余一律自由文本。"
                "病案记录的自由度与灵活性高于病历，故不拆解现病史，"
                "也不为慢性病史、传染病史、个人史、月经婚育史、其他病史单独建表。"
                "共 21 张表，分七组。")
    ws["A2"].font = Font(size=10, italic=True, color="595959")
    ws.merge_cells("A2:E2")
    ws["A2"].alignment = WRAP

    headers = ["序号", "分组", "表名（英文）", "表名（中文）", "说明"]
    for i, h in enumerate(headers, start=1):
        ws.cell(row=4, column=i, value=h)
    style_header(ws[4][:len(headers)], HEADER_FONT, HEADER_FILL)

    by_en = {t["en"]: t for t in TABLES}
    row, n = 5, 0
    for group, tables in GROUPS.items():
        for en in tables:
            spec = by_en[en]
            n += 1
            for i, val in enumerate([n, group, en, spec["cn"], spec["note"]], start=1):
                cell = ws.cell(row=row, column=i, value=val)
                cell.font = MONO if i == 3 else BODY
                cell.alignment = WRAP
                cell.border = BORDER
            row += 1

    for i, w in enumerate([6, 16, 34, 24, 74], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A5"


def build_enum_appendix(wb: Workbook) -> None:
    ws = wb.create_sheet("附表 枚举字典")
    ws["A1"] = "附表：TINYINT 枚举与编码字典"
    ws["A1"].font = TITLE_FONT
    ws.merge_cells("A1:C1")
    for i, h in enumerate(["附表编号", "所属字段／说明", "编号与取值"], start=1):
        ws.cell(row=2, column=i, value=h)
    style_header(ws[2][:3], HEADER_FONT, HEADER_FILL)

    row = 3
    for code, desc, items in ENUMS:
        values = "；".join(f"{v}={label}" for v, label in items)
        for i, val in enumerate([code, desc, values], start=1):
            cell = ws.cell(row=row, column=i, value=val)
            cell.font = MONO if i == 1 else BODY
            cell.alignment = WRAP
            cell.border = BORDER
        row += 1

    for i, w in enumerate([12, 46, 96], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/case-database-spec.xlsx")
    wb = Workbook()
    wb.remove(wb.active)
    build_overview(wb)
    for spec in TABLES:
        build_table_sheet(wb, spec)
    build_enum_appendix(wb)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"written: {out}")
    print(f"  sheets : {len(wb.sheetnames)}  (1 总览 + {len(TABLES)} 表 + 1 附表)")
    print(f"  fields : {sum(len(t['fields']) for t in TABLES)}")
    print(f"  enums  : {len(ENUMS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
