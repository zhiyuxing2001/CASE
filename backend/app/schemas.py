"""API 输出模型（Pydantic v2）。

字段与 ORM 模型一一对应；前端据此生成 TypeScript 类型。
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel


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
