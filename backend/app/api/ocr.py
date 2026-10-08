"""OCR 作业路由：上传后识别、查看、校对入库。

通道 A（macOS Vision）始终本地执行。通道 B（DeepSeek 结构化）依赖
API Key，未配置时降级为仅通道 A——识别文本仍可用于人工校对。
"""

from __future__ import annotations

import base64
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session
from ulid import ULID

from .. import schemas
from ..config import settings
from ..llm import ChatRequest, Message, Task, get_router, parse_json
from ..llm import prompts
from ..models import (Attachment, CaseNarrative, DictTemplate, InfoPatient,
                      OcrJob)
from ..ocr import lines_to_display, run_vision
from ..ocr.template import extract_fields
from ..services.record_service import create_record
from .deps import get_db

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


def _image_data_url(attachment: Attachment, path) -> str:
    mime = attachment.mime_type or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _flat_to_structured(flat: dict[str, str]) -> schemas.OcrStructured:
    """把 {字段路径: 值} 映射为 OcrStructured 嵌套结构。"""
    narrative = schemas.NarrativeCreate()
    diagnosis = schemas.DiagnosisCreate()
    treatment = schemas.TreatmentCreate()
    for path, value in flat.items():
        parts = path.split(".")
        if len(parts) != 2:
            continue
        group, field = parts
        target = {"narrative": narrative, "diagnosis": diagnosis,
                  "treatment": treatment}.get(group)
        if target is None:
            continue
        if field == "dose_count":
            try:
                target.dose_count = int(str(value))
            except (ValueError, TypeError):
                continue
        else:
            setattr(target, field, value)
    return schemas.OcrStructured(narrative=narrative, diagnosis=diagnosis,
                                 treatment=treatment)


def _template_hint(template: DictTemplate) -> str:
    anchors = template.field_anchors or []
    cols = template.table_columns or []
    parts = [f"这是「{template.name}」界面的结构："]
    if anchors:
        parts.append("文字结构（标签 → 字段）：" + "；".join(
            f"{a.get('label', '')}→{a.get('field', '')}" for a in anchors))
    if cols:
        parts.append("表格列（表头 → 字段）：" + "；".join(
            f"{c.get('label', '')}→{c.get('field', '')}" for c in cols))
    return "\n".join(parts)


def _job_out(job: OcrJob, raw_lines: list) -> schemas.OcrJobOut:
    return schemas.OcrJobOut(
        job_id=job.job_id,
        attach_id=job.attach_id,
        status=job.status or 0,
        degraded_mode=job.degraded_mode or 0,
        vision_text=job.vision_text or "",
        lines=lines_to_display(raw_lines),
    )


@router.post("/jobs", response_model=schemas.OcrJobOut, status_code=201)
def create_job(
    payload: schemas.OcrJobCreate,
    db: Session = Depends(get_db),
) -> schemas.OcrJobOut:
    attachment = db.get(Attachment, payload.attach_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="附件不存在")
    path = settings.data_dir / attachment.file_path
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件已丢失")

    # 未配置 DeepSeek Key → 仅通道 A（本地 Vision），降级模式记为 1
    degraded = 0 if settings.deepseek_api_key else 1

    job = OcrJob(
        job_id=str(ULID()),
        attach_id=payload.attach_id,
        status=1,
        degraded_mode=degraded,
        vision_engine="ocrmac/Vision",
    )
    db.add(job)
    db.commit()

    try:
        raw_lines = run_vision(str(path))
        job.vision_json = raw_lines
        job.vision_text = "\n".join(line["text"] for line in raw_lines)
        job.status = 2
        db.commit()
    except Exception as exc:  # noqa: BLE001
        job.status = 3
        job.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"识别失败：{exc}") from exc

    return _job_out(job, raw_lines)


@router.get("/jobs/{job_id}", response_model=schemas.OcrJobOut)
def get_job(job_id: str, db: Session = Depends(get_db)) -> schemas.OcrJobOut:
    job = db.get(OcrJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    return _job_out(job, job.vision_json or [])


@router.post("/jobs/{job_id}/structure", response_model=schemas.StructureResult)
def structure_job(
    job_id: str,
    template_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> schemas.StructureResult:
    """通道 B：用 DeepSeek 视觉模型把通道 A 的文本结构化为字段。

    可选传入 template_id，把界面模板的结构注入提示词以提升准确度。
    无 Key 时降级返回空结构；解析失败记录到 job.error_message 并报错。
    """
    job = db.get(OcrJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    if job.status != 2:
        raise HTTPException(status_code=400, detail="通道 A 尚未完成，无法结构化")

    attachment = db.get(Attachment, job.attach_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="附件不存在")
    path = settings.data_dir / attachment.file_path
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件已丢失")

    router = get_router()
    empty = schemas.StructureResult(
        structured=schemas.OcrStructured(), model="",
        prompt_version=prompts.PROMPT_VERSION,
        degraded=True, ai_configured=router.configured,
    )
    if not router.configured:
        return empty

    user_prompt = prompts.ocr_structuring_user(job.vision_text or "")
    if template_id:
        template = db.get(DictTemplate, template_id)
        if template is not None:
            user_prompt = _template_hint(template) + "\n\n" + user_prompt

    data_url = _image_data_url(attachment, path)
    messages = [
        Message("system", prompts.get_system_prompt("ocr_structuring")),
        Message("user", user_prompt),
    ]
    resp = router.chat(ChatRequest(
        task=Task.OCR_STRUCTURING,
        messages=messages,
        images=[data_url],
        json_schema={"type": "object"},  # 触发 response_format=json_object
        temperature=0.1,
    ))
    if resp is None or not resp.text:
        return empty

    try:
        structured = schemas.OcrStructured.model_validate(parse_json(resp.text))
    except (json.JSONDecodeError, ValidationError) as exc:  # noqa: BLE001
        job.error_message = f"结构化解析失败：{exc}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"结构化结果解析失败：{exc}") from exc

    job.structured_json = structured.model_dump()
    job.model = resp.model
    job.prompt_version = prompts.PROMPT_VERSION
    job.tokens_in = resp.usage.tokens_in
    job.tokens_cached = resp.usage.tokens_cached
    job.tokens_out = resp.usage.tokens_out
    job.cost_yuan = resp.usage.cost_yuan
    job.duration_ms = resp.latency_ms
    db.commit()

    return schemas.StructureResult(
        structured=structured, model=resp.model,
        prompt_version=prompts.PROMPT_VERSION,
        degraded=False, ai_configured=True,
    )


@router.post("/jobs/{job_id}/extract", response_model=schemas.StructureResult)
def extract_job(
    job_id: str,
    payload: schemas.TemplateExtractRequest,
    db: Session = Depends(get_db),
) -> schemas.StructureResult:
    """按界面模板从通道 A 文本中提取字段（无 AI 的本地通道）。

    依据模板的 field_anchors（标签→字段）按“标签：值”模式提取，作为人工
    校对的预填，不依赖 API Key。
    """
    job = db.get(OcrJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    if job.status != 2:
        raise HTTPException(status_code=400, detail="通道 A 尚未完成，无法提取")
    template = db.get(DictTemplate, payload.template_id)
    if template is None or template.is_active is False:
        raise HTTPException(status_code=404, detail="模板不存在")

    lines = job.vision_json or []
    flat = extract_fields(lines, template.field_anchors or [])
    structured = _flat_to_structured(flat)
    return schemas.StructureResult(
        structured=structured, model="template-extract", prompt_version="",
        degraded=False, ai_configured=False,
    )


@router.post("/jobs/{job_id}/commit")
def commit_job(
    job_id: str,
    payload: schemas.OcrCommit,
    db: Session = Depends(get_db),
) -> dict:
    job = db.get(OcrJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    if job.status == 4:
        raise HTTPException(status_code=400, detail="该作业已入库")

    patient_id = payload.patient_id
    if not patient_id:
        if not payload.patient_name.strip() or payload.birthday is None:
            raise HTTPException(status_code=400, detail="请填写患者姓名与出生日期")
        patient_id = str(ULID())
        db.add(InfoPatient(
            patient_id=patient_id,
            patient_name=payload.patient_name.strip(),
            gender=payload.gender,
            birthday=payload.birthday,
            nationality="CHN",
        ))
        db.flush()

    if payload.structured is not None:
        s = payload.structured
        record_id = create_record(db, schemas.RecordCreate(
            patient_id=patient_id,
            clinic_date=payload.clinic_date,
            narrative=s.narrative,
            diagnosis=s.diagnosis,
            treatment=s.treatment,
            herbs=[
                schemas.HerbCreate(
                    herb_name=h.herb_name, dose=h.dose, unit=h.unit,
                    processing=h.processing, decoction_note=h.decoction_note,
                    role=h.role, sequence=h.sequence,
                    needs_review=h.needs_review, confidence=h.confidence,
                )
                for h in s.herbs
            ],
            lab_results=s.lab_results,
            exams=s.exams,
        ))
    else:
        record_id = create_record(db, schemas.RecordCreate(
            patient_id=patient_id,
            clinic_date=payload.clinic_date,
            narrative=schemas.NarrativeCreate(
                complaint=payload.complaint,
                present_illness=payload.present_illness,
            ),
        ))

    # OCR 原文入库，供溯源与将来通道 B 的结构化
    narrative = db.get(CaseNarrative, record_id)
    narrative.raw_ocr_text = job.vision_text or ""

    job.record_id = record_id
    job.status = 4
    attachment = db.get(Attachment, job.attach_id)
    if attachment is not None:
        attachment.record_id = record_id
    db.commit()

    return {"record_id": record_id}
