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
from ..models import CaseNarrative, Diagnosis, InfoPatient, InfoRecord
from ..search import search_cases
from .deps import get_db

router = APIRouter(prefix="/api/ai", tags=["ai"])

_SYSTEM_QA = (
    "你是中医跟诊学习助手。基于给定的病案资料回答问题，"
    "引用具体病案时用 [编号] 标注。若资料不足以回答，请明确说明。"
)
_SYSTEM_DRAFT = "你是中医跟诊学习助手，帮助撰写学习心得初稿，用 Markdown 输出。"
_SYSTEM_POLISH = "你是中医学术写作助手，把下面这段心得润色得更专业、条理清晰，保持原意与要点，用 Markdown 输出。"


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

    if not router.configured:
        # 降级：仅返回检索结果，由前端呈现为"检索到的相关病案"
        return schemas.AiChatResponse(
            answer="", sources=sources, degraded=True, ai_configured=False,
        )
    if not sources:
        return schemas.AiChatResponse(
            answer="未在病案库中检索到相关内容。",
            sources=[], degraded=False, ai_configured=True,
        )

    context = "\n\n".join(
        f"[{i + 1}] {s.patient_name}，{s.clinic_date} 就诊，主诉「{s.complaint}」，"
        f"证型「{s.syndrome}」。资料：{s.snippet}"
        for i, s in enumerate(sources)
    )
    messages = [
        Message("system", _SYSTEM_QA),
        Message("user", f"病案资料：\n{context}\n\n问题：{payload.question}"),
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
    user = f"主题：{payload.topic}\n" + (f"参考病案：\n{context}\n" if context else "")
    messages = [Message("system", _SYSTEM_DRAFT), Message("user", user)]
    resp = router.chat(ChatRequest(task=Task.NOTE_DRAFT, messages=messages,
                                   temperature=0.4))
    if resp is None:
        return schemas.AiDraftResponse(text="", degraded=True, ai_configured=True)
    return schemas.AiDraftResponse(text=resp.text, degraded=False, ai_configured=True)


@router.post("/polish", response_model=schemas.AiDraftResponse)
def polish(payload: schemas.AiPolishRequest) -> schemas.AiDraftResponse:
    router = get_router()
    if not router.configured:
        return schemas.AiDraftResponse(text="", degraded=True, ai_configured=False)
    messages = [Message("system", _SYSTEM_POLISH), Message("user", payload.text)]
    resp = router.chat(ChatRequest(task=Task.NOTE_POLISH, messages=messages,
                                   temperature=0.3))
    if resp is None:
        return schemas.AiDraftResponse(text="", degraded=True, ai_configured=True)
    return schemas.AiDraftResponse(text=resp.text, degraded=False, ai_configured=True)
