"""API 输出模型（Pydantic v2）。

字段与 ORM 模型一一对应；前端据此生成 TypeScript 类型。
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class Health(BaseModel):
    status: str
    database: str
    ai_configured: bool
    version: str


class PatientBrief(BaseModel):
    patient_id: str
    patient_name: str
    gender: bool
    age: float | None = None


class RecordSummary(BaseModel):
    record_id: int
    clinic_date: date
    visit_no: int
    visit_type: int
    patient_id: str
    patient_name: str
    complaint: str
    syndrome: str
    tcm_disease: str
    herb_count: int
    mentor_name: str
    needs_review: bool


class RecordList(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[RecordSummary]


class CourseSummary(BaseModel):
    """病程系列摘要：一个系列一行（初诊为系列头）。"""
    course_id: int
    patient_id: str
    patient_name: str
    first_date: date
    last_date: date
    visit_count: int
    complaint: str
    syndrome: str
    tcm_disease: str
    mentor_name: str
    needs_review: bool


class CourseList(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CourseSummary]


class HerbItem(BaseModel):
    sequence: int
    herb_name: str
    herb_name_norm: str
    herb_id: str | None = None
    dose: float | None = None
    unit: str
    processing: str
    decoction_note: str
    role: str
    needs_review: bool


class RecordDetail(BaseModel):
    record: dict[str, Any]
    patient: PatientBrief
    narrative: dict[str, Any]
    diagnosis: dict[str, Any]
    treatment: dict[str, Any]
    herbs: list[HerbItem]
    course: list[dict[str, Any]]


class HerbOption(BaseModel):
    herb_id: str
    herb_name: str
    pinyin: str
    category: str
    is_processed: bool


class HerbResolution(BaseModel):
    entered: str
    normalised: str
    herb_id: str | None
    matched_by: str
    is_ocr_misread: bool


class HerbSuggestion(BaseModel):
    herb_id: str
    herb_name: str
    similarity: float


class TermNormalizeRequest(BaseModel):
    term: str


class SyndromeOption(BaseModel):
    syndrome_id: str
    syndrome_name: str
    category: str


class TermOption(BaseModel):
    term_id: int
    term_type: int
    term: str
    description: str


class FormulaOption(BaseModel):
    formula_id: str
    formula_name: str
    source: str


class MentorOption(BaseModel):
    mentor_id: str
    mentor_name: str
    title: str


class PatientOption(BaseModel):
    patient_id: str
    patient_name: str
    gender: bool


class SearchResult(BaseModel):
    record_id: int
    patient_id: str
    clinic_date: date | None
    search_text: str


# ---------------------------------------------------------------------------
# 写入请求模型
# ---------------------------------------------------------------------------

class PatientCreate(BaseModel):
    patient_name: str
    gender: bool = False
    birthday: date
    nationality: str = "CHN"
    id_no: str = ""
    job: str = ""
    tel: str = ""
    addr_region: str = ""


class PatientCreated(BaseModel):
    patient_id: str


class NarrativeCreate(BaseModel):
    complaint: str = ""
    present_illness: str = ""
    past_history: str = ""
    personal_history: str = ""
    allergy_history: str = ""
    body_of_tongue: str = ""
    fur_of_tongue: str = ""
    pulse: str = ""
    other_cond: str = ""
    physical_exam: str = ""
    auxiliary_exam: str = ""
    notes: str = ""


class DiagnosisCreate(BaseModel):
    tcm_disease: str = ""
    syndrome: str = ""
    syndrome_id: str | None = None
    wm_diagnosis: str = ""
    patterns_analysis: str = ""
    differential_diagnosis: str = ""
    notes: str = ""


class TreatmentCreate(BaseModel):
    treatment_principle: str = ""
    formula_name: str = ""
    formula_id: str | None = None
    dose_count: int | None = None
    decoction: str = ""
    usage: str = ""
    advice: str = ""
    other_treatment: str = ""


class HerbCreate(BaseModel):
    herb_name: str
    dose: float | None = None
    unit: str = "g"
    processing: str = ""
    decoction_note: str = ""
    role: str = ""
    sequence: int = 0
    needs_review: bool = False
    confidence: float = 1.0


class RecordCreate(BaseModel):
    patient_id: str
    clinic_date: date
    visit_type: int = 0
    age: float | None = None
    mentor_id: str | None = None
    department: str = ""
    addr: str = ""
    doctor_name: str = ""
    parent_record_id: int | None = None
    narrative: NarrativeCreate = Field(default_factory=NarrativeCreate)
    diagnosis: DiagnosisCreate = Field(default_factory=DiagnosisCreate)
    treatment: TreatmentCreate = Field(default_factory=TreatmentCreate)
    herbs: list[HerbCreate] = Field(default_factory=list)


class RecordCreated(BaseModel):
    record_id: int


class AuditEntry(BaseModel):
    table_name: str
    action: int
    field_name: str
    old_value: str
    new_value: str
    changed_at: str
    note: str


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

class QualityReport(BaseModel):
    width: int
    height: int
    sharpness: float
    blurry: bool


class AttachmentCreated(BaseModel):
    attach_id: str
    quality: QualityReport


class OcrLine(BaseModel):
    text: str
    confidence: float
    bbox: list[float]  # 归一化 [x, y, w, h]，原点左上角


class OcrJobCreate(BaseModel):
    attach_id: str
    doc_type: int = 0


class OcrJobOut(BaseModel):
    job_id: str
    attach_id: str
    status: int
    degraded_mode: int
    vision_text: str
    lines: list[OcrLine]


class OcrHerb(BaseModel):
    sequence: int = 0
    herb_name: str = ""
    dose: float | None = None
    unit: str = "g"
    processing: str = ""
    decoction_note: str = ""
    role: str = ""
    needs_review: bool = False
    confidence: float = 1.0


class OcrStructured(BaseModel):
    """通道 B 的结构化输出，字段与写入模型一致，可直接落库。"""
    narrative: NarrativeCreate = Field(default_factory=NarrativeCreate)
    diagnosis: DiagnosisCreate = Field(default_factory=DiagnosisCreate)
    treatment: TreatmentCreate = Field(default_factory=TreatmentCreate)
    herbs: list[OcrHerb] = Field(default_factory=list)


class StructureResult(BaseModel):
    structured: OcrStructured
    model: str
    prompt_version: str
    degraded: bool
    ai_configured: bool


class OcrCommit(BaseModel):
    patient_name: str = ""
    patient_id: str | None = None
    gender: bool = False
    birthday: date | None = None
    clinic_date: date
    # 通道 B 结构化结果（优先）；为空时回落到下面两个字段
    structured: OcrStructured | None = None
    complaint: str = ""
    present_illness: str = ""


# ---------------------------------------------------------------------------
# 跟师学习
# ---------------------------------------------------------------------------

class NoteCreate(BaseModel):
    note_type: int = 1
    title: str
    content_md: str = ""
    record_id: int | None = None
    mentor_id: str | None = None


class NoteUpdate(BaseModel):
    note_type: int | None = None
    title: str | None = None
    content_md: str | None = None
    status: int | None = None
    record_id: int | None = None
    mentor_id: str | None = None


class CommentCreate(BaseModel):
    mentor_id: str | None = None
    content: str
    comment_type: int = 0
    is_ai_generated: bool = False


class CommentOut(BaseModel):
    comment_id: int
    mentor_id: str | None
    mentor_name: str
    content: str
    comment_type: int
    is_ai_generated: bool
    commented_at: str


class NoteSummary(BaseModel):
    note_id: str
    note_type: int
    title: str
    status: int
    record_id: int | None
    mentor_name: str
    word_count: int
    is_ai_assisted: bool
    updated_at: str


class NoteList(BaseModel):
    total: int
    items: list[NoteSummary]


class NoteDetail(BaseModel):
    note_id: str
    note_type: int
    title: str
    content_md: str
    status: int
    record_id: int | None
    mentor_id: str | None = None
    mentor_name: str
    word_count: int
    is_ai_assisted: bool
    created_at: str
    updated_at: str
    comments: list[CommentOut]
    record: dict | None


class ProgressOut(BaseModel):
    note_counts: dict[str, int]
    total_records: int
    total_patients: int
    total_syndromes: int
    top_syndromes: list[dict]


# ---------------------------------------------------------------------------
# 字典维护
# ---------------------------------------------------------------------------

class HerbUpsert(BaseModel):
    herb_name: str
    pinyin: str = ""
    category: str = ""
    nature: str = ""
    flavor: str = ""
    meridians: str = ""
    functions: str = ""
    is_processed: bool = False
    processing: str = ""
    is_common: bool = True


class SyndromeUpsert(BaseModel):
    syndrome_name: str
    category: str = ""
    key_symptoms: str = ""
    treatment: str = ""
    common_formula: str = ""


class TermUpsert(BaseModel):
    term: str
    term_type: int
    description: str = ""


class FormulaUpsert(BaseModel):
    formula_name: str
    source: str = ""
    category: str = ""
    functions: str = ""
    indications: str = ""
    composition_text: str = ""
    usage_text: str = ""


# ---------------------------------------------------------------------------
# 数据管理
# ---------------------------------------------------------------------------

class TableStat(BaseModel):
    table: str
    rows: int


class AdminStats(BaseModel):
    tables: list[TableStat]
    database_size: int


class BackupInfo(BaseModel):
    name: str
    size: int
    created_at: str


class BackupCreated(BaseModel):
    path: str
    size: int


class AuditPage(BaseModel):
    total: int
    items: list[AuditEntry]


class CheckResult(BaseModel):
    ok: bool
    foreign_key_violations: int
    tables: list[TableStat]
    messages: list[str]


# ---------------------------------------------------------------------------
# AI 助手
# ---------------------------------------------------------------------------

class AiStatus(BaseModel):
    configured: bool
    provider: str
    model: str


class AiSettingsOut(BaseModel):
    configured: bool
    api_key_masked: str
    base_url: str
    model: str


class AiSettingsUpdate(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


class AiChatRequest(BaseModel):
    question: str
    case_id: int | None = None


class AiSource(BaseModel):
    record_id: int
    patient_name: str
    clinic_date: str
    complaint: str
    syndrome: str
    snippet: str


class AiChatResponse(BaseModel):
    answer: str
    sources: list[AiSource]
    degraded: bool
    ai_configured: bool


class AiDraftRequest(BaseModel):
    topic: str
    note_type: int = 1
    case_id: int | None = None


class AiPolishRequest(BaseModel):
    text: str


class AiDraftResponse(BaseModel):
    text: str
    degraded: bool
    ai_configured: bool

