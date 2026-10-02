"""OCR 作业路由：上传后识别、查看、校对入库。

通道 A（macOS Vision）始终本地执行。通道 B（DeepSeek 结构化）依赖
API Key，未配置时降级为仅通道 A——识别文本仍可用于人工校对。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ulid import ULID

from .. import schemas
from ..config import settings
from ..models import Attachment, CaseNarrative, InfoPatient, OcrJob
from ..ocr import lines_to_display, run_vision
from ..services.record_service import create_record
from .deps import get_db

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


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
