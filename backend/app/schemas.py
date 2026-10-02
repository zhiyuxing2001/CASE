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


class SyndromeOption(BaseModel):
    syndrome_id: str
    syndrome_name: str
    category: str


class TermOption(BaseModel):
    term_id: int
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


class OcrCommit(BaseModel):
    patient_name: str = ""
    patient_id: str | None = None
    gender: bool = False
    birthday: date | None = None
    clinic_date: date
    complaint: str = ""
    present_illness: str = ""

