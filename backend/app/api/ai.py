"""AI 助手路由：带出处问答、心得初稿、润色。

无 API Key 时优雅降级：问答退化为"检索结果直出"，写作类任务明确
返回未配置状态，其余功能不受影响。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..llm import ChatRequest, Message, Task, get_router
from ..llm import prompts
from ..models import (CaseNarrative, Diagnosis, InfoPatient, InfoRecord,
                      LearningNote)
from ..search import search_cases
from .deps import get_db

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _sources(db: Session, hits: list[dict]) -> list[schemas.AiSource]:
    result: list[schemas.AiSource] = []
    for hit in hits:
        rid = hit["record_id"]
        patient = db.scalar(select(InfoPatient).where(
            InfoPatient.patient_id == hit["patient_id"]))
        narrative = db.get(CaseNarrative, rid)
        diagnosis = db.get(Diagnosis, rid)
        result.append(schemas.AiSource(
            record_id=rid,
            patient_name=patient.patient_name if patient else "",
            clinic_date=str(hit.get("clinic_date") or ""),
            complaint=narrative.complaint if narrative else "",
            syndrome=diagnosis.syndrome if diagnosis else "",
            snippet=(hit.get("search_text") or "")[:200],
        ))
    return result


def _case_source(db: Session, record_id: int) -> schemas.AiSource | None:
    record = db.get(InfoRecord, record_id)
    if record is None:
        return None
    patient = db.scalar(select(InfoPatient).where(
        InfoPatient.patient_id == record.patient_id))
    narrative = db.get(CaseNarrative, record_id)
    diagnosis = db.get(Diagnosis, record_id)
    return schemas.AiSource(
        record_id=record_id,
        patient_name=patient.patient_name if patient else "",
        clinic_date=str(record.clinic_date),
        complaint=narrative.complaint if narrative else "",
        syndrome=diagnosis.syndrome if diagnosis else "",
        snippet=(narrative.present_illness if narrative else "")[:200],
    )


def _case_context(db: Session, case_id: int) -> str:
    record = db.get(InfoRecord, case_id)
    if record is None:
        return ""
    patient = db.scalar(select(InfoPatient).where(
        InfoPatient.patient_id == record.patient_id))
    narrative = db.get(CaseNarrative, case_id)
    diagnosis = db.get(Diagnosis, case_id)
    lines = [f"患者：{patient.patient_name if patient else ''}，"
             f"{record.clinic_date} 就诊"]
    if narrative:
        lines.append(f"主诉：{narrative.complaint}")
        lines.append(f"现病史：{narrative.present_illness}")
        lines.append(f"舌脉：{narrative.body_of_tongue} / {narrative.fur_of_tongue} / {narrative.pulse}")
    if diagnosis:
        lines.append(f"证型：{diagnosis.syndrome}")
        lines.append(f"辨证分析：{diagnosis.patterns_analysis}")
    return "\n".join(lines)


@router.get("/status", response_model=schemas.AiStatus)
def status() -> schemas.AiStatus:
    router = get_router()
    primary = router.primary()
    return schemas.AiStatus(
        configured=router.configured,
        provider=primary["provider"],
        model=primary["model"],
    )


@router.post("/chat", response_model=schemas.AiChatResponse)
def chat(payload: schemas.AiChatRequest,
         db: Session = Depends(get_db)) -> schemas.AiChatResponse:
    hits = search_cases(db, payload.question, limit=5)
    sources = _sources(db, hits)
    router = get_router()

    # 引用病案：无论 AI 是否配置，都把它放到来源首位
    if payload.case_id is not None:
        ref = _case_source(db, payload.case_id)
        if ref is not None:
            sources = [ref] + [s for s in sources
                               if s.record_id != payload.case_id]

    if not router.configured:
        # 降级：仅返回检索结果（含引用的病案），由前端呈现为"相关病案"
        return schemas.AiChatResponse(
            answer="", sources=sources, degraded=True, ai_configured=False,
        )

    context_blocks: list[str] = []
    # 引用某一份病案
    if payload.case_id is not None:
        ctx = _case_context(db, payload.case_id)
        if ctx:
            context_blocks.append(f"【参考病案】\n{ctx}")
    # 引用某一篇跟师笔记
    if payload.note_id is not None:
        note = db.get(LearningNote, payload.note_id)
        if note is not None and not note.is_deleted:
            context_blocks.append(
                f"【参考笔记】《{note.title}》\n{note.content_md}")

    if sources:
        context_blocks.append("【病案资料】\n" + "\n\n".join(
            f"[{i + 1}] {s.patient_name}，{s.clinic_date} 就诊，"
            f"主诉「{s.complaint}」，证型「{s.syndrome}」。资料：{s.snippet}"
            for i, s in enumerate(sources)
        ))

    if not context_blocks:
        return schemas.AiChatResponse(
            answer="未在病案库中检索到相关内容。",
            sources=[], degraded=False, ai_configured=True,
        )

    context = "\n\n".join(context_blocks)
    messages = [
        Message("system", prompts.SYSTEM_CASE_QA),
        Message("user", prompts.case_qa_user(context, payload.question)),
    ]
    resp = router.chat(ChatRequest(task=Task.CASE_QA, messages=messages))
    if resp is None:
        return schemas.AiChatResponse(
            answer="", sources=sources, degraded=True, ai_configured=True,
        )
    return schemas.AiChatResponse(
        answer=resp.text, sources=sources,
        degraded=resp.degraded, ai_configured=True,
    )


@router.post("/draft", response_model=schemas.AiDraftResponse)
def draft(payload: schemas.AiDraftRequest,
          db: Session = Depends(get_db)) -> schemas.AiDraftResponse:
    router = get_router()
    if not router.configured:
        return schemas.AiDraftResponse(text="", degraded=True, ai_configured=False)

    context = ""
    if payload.case_id:
        context = _case_context(db, payload.case_id)
    user = prompts.note_draft_user(payload.topic, context)
    messages = [Message("system", prompts.SYSTEM_NOTE_DRAFT), Message("user", user)]
    resp = router.chat(ChatRequest(task=Task.NOTE_DRAFT, messages=messages,
                                   temperature=0.5))
    if resp is None:
        return schemas.AiDraftResponse(text="", degraded=True, ai_configured=True)
    return schemas.AiDraftResponse(text=resp.text, degraded=False, ai_configured=True)


@router.post("/polish", response_model=schemas.AiDraftResponse)
def polish(payload: schemas.AiPolishRequest) -> schemas.AiDraftResponse:
    router = get_router()
    if not router.configured:
        return schemas.AiDraftResponse(text="", degraded=True, ai_configured=False)
    messages = [Message("system", prompts.SYSTEM_NOTE_POLISH),
                Message("user", prompts.note_polish_user(payload.text))]
    resp = router.chat(ChatRequest(task=Task.NOTE_POLISH, messages=messages,
                                   temperature=0.3))
    if resp is None:
        return schemas.AiDraftResponse(text="", degraded=True, ai_configured=True)
    return schemas.AiDraftResponse(text=resp.text, degraded=False, ai_configured=True)
