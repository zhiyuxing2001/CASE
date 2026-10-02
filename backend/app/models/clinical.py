"""病案主体与诊疗：case_narrative · diagnosis · treatment · prescription_item.

Structure is kept only where it serves a concrete retrieval or analysis
need. Everything else is a free-text column, because a case archive
allows far more freedom than a clinical medical record and over-fine
fields turn into duplicated data entry.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, REAL, Text

from .base import Base, CreatedAtMixin, TimestampsMixin
from .types import UnsignedTinyInt


class CaseNarrative(TimestampsMixin, Base):
    """病案文本记录表 — the body of the case, one row per visit.

    Free text throughout, except tongue body, tongue coating and pulse.
    Those three are the core diagnostic information in TCM and are kept
    as separate columns so tongue and pulse patterns can be counted.
    """

    __tablename__ = "case_narrative"

    record_id = Column(Integer, primary_key=True, autoincrement=True,
                       doc="病历编号")
    patient_id = Column(Text, ForeignKey("info_patient.patient_id"),
                        nullable=False, doc="患者编号")
    complaint = Column(Text, nullable=False,
                       doc="主诉，≤20个Unicode字符；复诊可写“服药后复诊”或留空")
    present_illness = Column(Text, nullable=False, default="",
                             doc="现病史，自由文本，不拆解为子字段")
    past_history = Column(Text, nullable=False, default="",
                          doc="既往史，自由文本；慢性病史、传染病史、手术外伤输血史一并记于此")
    personal_history = Column(Text, nullable=False, default="",
                              doc="个人史及婚育史，自由文本；吸烟饮酒、职业接触、月经婚育记于此")
    allergy_history = Column(Text, nullable=False, default="",
                             doc="过敏史，自由文本")
    body_of_tongue = Column(Text, nullable=False, default="",
                            doc="舌质，单独成列以支持舌象统计")
    fur_of_tongue = Column(Text, nullable=False, default="",
                           doc="舌苔，单独成列以支持舌象统计")
    pulse = Column(Text, nullable=False, default="",
                   doc="切诊，单独成列以支持脉象统计")
    other_cond = Column(Text, nullable=False, default="",
                        doc="其他望闻切诊，自由文本")
    physical_exam = Column(Text, nullable=False, default="",
                           doc="体格检查，自由文本")
    auxiliary_exam = Column(Text, nullable=False, default="",
                            doc="辅助检查，自由文本；含日期、外院机构、项目与结果")
    notes = Column(Text, nullable=False, default="", doc="其他补充信息")
    raw_ocr_text = Column(Text, nullable=False, default="",
                          doc="OCR 原文，只写不改，用于溯源")


class Diagnosis(TimestampsMixin, Base):
    """诊断记录表 — free text, plus one optional dictionary key for syndrome.

    A separate one-row-per-diagnosis child table was dropped by design
    review: multiple western diagnoses are written as one semicolon
    separated string, which matches how the source documents read.
    """

    __tablename__ = "diagnosis"

    record_id = Column(Integer, primary_key=True, autoincrement=True,
                       doc="病历编号")
    patient_id = Column(Text, ForeignKey("info_patient.patient_id"),
                        nullable=False, doc="患者编号")
    tcm_disease = Column(Text, nullable=False, default="", doc="中医病名")
    syndrome = Column(Text, nullable=False, default="",
                      doc="中医证型原文，如“湿热瘀阻、脾虚证”")
    syndrome_id = Column(Text, ForeignKey("dict_syndrome.syndrome_id"),
                         nullable=True,
                         doc="证型字典编号，录入时由联想写入，用于频次统计")
    wm_diagnosis = Column(Text, nullable=False, default="",
                          doc="西医诊断，多条以中文分号分隔")
    patterns_analysis = Column(Text, nullable=False, default="",
                               doc="辨证分析，手写教学表单设有独立栏位")
    differential_diagnosis = Column(Text, nullable=False, default="",
                                    doc="鉴别诊断")
    notes = Column(Text, nullable=False, default="", doc="其他")
    raw_ocr_text = Column(Text, nullable=False, default="",
                          doc="OCR 原文，只写不改，用于溯源")


class Treatment(TimestampsMixin, Base):
    """治疗记录表 — prescription-level information, one row per visit.

    No JSON copy of the prescription is kept: the herb rows in
    ``prescription_item`` are the structured form and ``raw_ocr_text``
    preserves the original wording.
    """

    __tablename__ = "treatment"

    record_id = Column(Integer, primary_key=True, autoincrement=True,
                       doc="病历编号")
    patient_id = Column(Text, ForeignKey("info_patient.patient_id"),
                        nullable=False, doc="患者编号")
    treatment_principle = Column(Text, nullable=False, default="",
                                 doc="治法，如“清热祛湿、理气活血止痛”")
    formula_name = Column(Text, nullable=False, default="",
                          doc="方剂名，对应手写表单“方拟____加减治之”的空位")
    formula_id = Column(Text, ForeignKey("dict_formula.formula_id"),
                        nullable=True, doc="方剂字典编号")
    dose_count = Column(Integer, nullable=True, default=0, doc="付数（剂）")
    decoction = Column(Text, nullable=False, default="",
                       doc="煎煮法，自由文本；是否代煎直接写于此")
    usage = Column(Text, nullable=False, default="", doc="用法")
    advice = Column(Text, nullable=False, default="",
                    doc="医嘱与调护，含饮食起居调摄与复诊安排")
    other_treatment = Column(Text, nullable=False, default="",
                             doc="其他治疗：中成药、西医治疗、针灸外治等")
    raw_ocr_text = Column(Text, nullable=False, default="",
                          doc="处方原文，只写不改，用于溯源")


class PrescriptionItem(CreatedAtMixin, Base):
    """处方药味明细表 — the core table for herb frequency and dose analysis.

    A prescription is inherently a list of herbs, so recording one row
    per herb is the data's natural shape rather than redundant
    structuring.
    """

    __tablename__ = "prescription_item"

    item_id = Column(Integer, primary_key=True, autoincrement=True,
                     doc="明细编号")
    record_id = Column(Integer, ForeignKey("info_record.record_id"),
                       nullable=False, index=True, doc="病历编号")
    patient_id = Column(Text, ForeignKey("info_patient.patient_id"),
                        nullable=False, doc="患者编号")
    prescription_no = Column(Integer, nullable=False, default=1,
                             doc="第几张方")
    sequence = Column(Integer, nullable=False, default=0,
                      doc="方中顺序，君臣佐使顺序有意义")
    herb_id = Column(Text, ForeignKey("dict_herb.herb_id"), nullable=True,
                     doc="药材编号；未匹配到字典时为空，不影响保存")
    herb_name = Column(Text, nullable=False,
                       doc="药味原文，如“生地”“盐黄柏”")
    herb_name_norm = Column(Text, nullable=False, default="",
                            doc="归一药名；统计以此列为准")
    dose = Column(REAL, nullable=True, default=0, doc="剂量，不含单位")
    unit = Column(Text, nullable=False, default="g",
                  doc="单位，默认g；后处理需做单位白名单校验")
    total_quantity = Column(REAL, nullable=True, default=0,
                            doc="总量；HIS 中总量 = 剂量 × 付数，用作 OCR 校验")
    frequency = Column(Text, nullable=False, default="",
                       doc="频次，如 BID、QD；仅 HIS 单据具备")
    processing = Column(Text, nullable=False, default="",
                        doc="炮制，如炒、炙、醋制、盐制、砂烫")
    decoction_note = Column(Text, nullable=False, default="",
                            doc="煎煮要求，如先煎、后下、包煎、烊化、冲服")
    role = Column(Text, nullable=False, default="",
                  doc="君臣佐使，取值为君、臣、佐、使之一")
    needs_review = Column(Boolean, nullable=False, default=False,
                          doc="是否待校对，由置信度与算术校验共同决定")
    confidence = Column(REAL, nullable=True, default=1,
                        doc="识别置信度，人工录入为1")
