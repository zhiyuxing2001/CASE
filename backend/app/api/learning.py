"""跟师学习路由：学习笔记、导师点评、进度看板。"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session
from ulid import ULID

from .. import schemas
from ..models import (CaseNarrative, Diagnosis, InfoPatient, InfoRecord,
                      LearningNote, Mentor, MentorComment)
from ..services.report_service import generate_notes_report
from .deps import get_db

router = APIRouter(prefix="/api/learning", tags=["learning"])


def _word_count(markdown: str) -> int:
    return len([ch for ch in markdown if not ch.isspace()])


def _mentor_name(db: Session, mentor_id: str | None) -> str:
    if not mentor_id:
        return ""
    mentor = db.get(Mentor, mentor_id)
    return mentor.mentor_name if mentor else ""


def _summary(db: Session, note: LearningNote) -> schemas.NoteSummary:
    updated = note.updated_at or note.created_at
    return schemas.NoteSummary(
        note_id=note.note_id,
        note_type=note.note_type or 0,
        title=note.title,
        status=note.status or 0,
        record_id=note.record_id,
        mentor_name=_mentor_name(db, note.mentor_id),
        word_count=note.word_count or 0,
        is_ai_assisted=bool(note.is_ai_assisted),
        updated_at=updated.isoformat(sep=" "),
    )


def _comment_out(db: Session, comment: MentorComment) -> schemas.CommentOut:
    return schemas.CommentOut(
        comment_id=comment.comment_id,
        mentor_id=comment.mentor_id,
        mentor_name=_mentor_name(db, comment.mentor_id),
        content=comment.content,
        comment_type=comment.comment_type or 0,
        is_ai_generated=bool(comment.is_ai_generated),
        commented_at=comment.commented_at.isoformat(sep=" "),
    )


def _detail(db: Session, note: LearningNote) -> schemas.NoteDetail:
    comments = db.execute(
        select(MentorComment)
        .where(MentorComment.target_type == 0,
               MentorComment.target_id == note.note_id)
        .order_by(MentorComment.commented_at)
    ).scalars().all()

    record = None
    if note.record_id:
        rec = db.get(InfoRecord, note.record_id)
        if rec is not None:
            patient = db.scalar(select(InfoPatient).where(
                InfoPatient.patient_id == rec.patient_id))
            narrative = db.get(CaseNarrative, note.record_id)
            diagnosis = db.get(Diagnosis, note.record_id)
            record = {
                "record_id": rec.record_id,
                "clinic_date": rec.clinic_date.isoformat(),
                "patient_name": patient.patient_name if patient else "",
                "complaint": narrative.complaint if narrative else "",
                "syndrome": diagnosis.syndrome if diagnosis else "",
            }

    return schemas.NoteDetail(
        note_id=note.note_id,
        note_type=note.note_type or 0,
        title=note.title,
        content_md=note.content_md,
        status=note.status or 0,
        record_id=note.record_id,
        mentor_id=note.mentor_id,
        mentor_name=_mentor_name(db, note.mentor_id),
        word_count=note.word_count or 0,
        is_ai_assisted=bool(note.is_ai_assisted),
        created_at=note.created_at.isoformat(sep=" "),
        updated_at=(note.updated_at or note.created_at).isoformat(sep=" "),
        comments=[_comment_out(db, c) for c in comments],
        record=record,
    )


@router.get("/notes", response_model=schemas.NoteList)
def list_notes(
    note_type: int | None = None,
    status: int | None = None,
    q: str = "",
    db: Session = Depends(get_db),
) -> schemas.NoteList:
    stmt = select(LearningNote).where(LearningNote.is_deleted.is_(False))
    if note_type is not None:
        stmt = stmt.where(LearningNote.note_type == note_type)
    if status is not None:
        stmt = stmt.where(LearningNote.status == status)
    if q:
        stmt = stmt.where(or_(
            LearningNote.title.like(f"%{q}%"),
            LearningNote.content_md.like(f"%{q}%"),
        ))
    notes = db.execute(
        stmt.order_by(
            func.coalesce(LearningNote.updated_at, LearningNote.created_at).desc()
        )
    ).scalars().all()
    return schemas.NoteList(
        total=len(notes),
        items=[_summary(db, n) for n in notes],
    )


@router.post("/notes", response_model=schemas.NoteDetail, status_code=201)
def create_note(
    payload: schemas.NoteCreate,
    db: Session = Depends(get_db),
) -> schemas.NoteDetail:
    note = LearningNote(
        note_id=str(ULID()),
        note_type=payload.note_type,
        title=payload.title,
        content_md=payload.content_md,
        status=0,
        record_id=payload.record_id,
        mentor_id=payload.mentor_id,
        word_count=_word_count(payload.content_md),
        is_ai_assisted=False,
    )
    db.add(note)
    db.commit()
    return _detail(db, note)


@router.get("/notes/{note_id}", response_model=schemas.NoteDetail)
def get_note(note_id: str, db: Session = Depends(get_db)) -> schemas.NoteDetail:
    note = db.get(LearningNote, note_id)
    if note is None or note.is_deleted:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return _detail(db, note)


@router.put("/notes/{note_id}", response_model=schemas.NoteDetail)
def update_note(
    note_id: str,
    payload: schemas.NoteUpdate,
    db: Session = Depends(get_db),
) -> schemas.NoteDetail:
    note = db.get(LearningNote, note_id)
    if note is None or note.is_deleted:
        raise HTTPException(status_code=404, detail="笔记不存在")

    data = payload.model_dump(exclude_unset=True)
    if "content_md" in data and data["content_md"] is not None:
        note.word_count = _word_count(data["content_md"])
    for key, value in data.items():
        if value is not None:
            setattr(note, key, value)
    note.updated_at = datetime.now().replace(microsecond=0)
    db.commit()
    return _detail(db, note)


@router.post("/notes/{note_id}/comments", response_model=schemas.CommentOut,
             status_code=201)
def add_comment(
    note_id: str,
    payload: schemas.CommentCreate,
    db: Session = Depends(get_db),
) -> schemas.CommentOut:
    note = db.get(LearningNote, note_id)
    if note is None or note.is_deleted:
        raise HTTPException(status_code=404, detail="笔记不存在")
    comment = MentorComment(
        target_type=0,
        target_id=note_id,
        mentor_id=payload.mentor_id,
        content=payload.content,
        comment_type=payload.comment_type,
        is_ai_generated=payload.is_ai_generated,
    )
    db.add(comment)
    db.commit()
    return _comment_out(db, comment)


@router.get("/progress", response_model=schemas.ProgressOut)
def progress(db: Session = Depends(get_db)) -> schemas.ProgressOut:
    note_counts: dict[str, int] = {}
    for note_type, count in db.execute(
        select(LearningNote.note_type, func.count())
        .where(LearningNote.is_deleted.is_(False))
        .group_by(LearningNote.note_type)
    ):
        note_counts[str(note_type)] = count

    total_records = db.scalar(
        select(func.count()).select_from(InfoRecord)
        .where(InfoRecord.is_deleted.is_(False))
    ) or 0
    total_patients = db.scalar(
        select(func.count()).select_from(InfoPatient)
        .where(InfoPatient.is_deleted.is_(False))
    ) or 0
    total_syndromes = db.scalar(
        select(func.count(func.distinct(Diagnosis.syndrome)))
        .where(Diagnosis.syndrome != "")
    ) or 0

    syndrome_rows = db.execute(
        select(Diagnosis.syndrome, func.count())
        .where(Diagnosis.syndrome != "")
        .group_by(Diagnosis.syndrome)
        .order_by(func.count().desc())
        .limit(10)
    ).all()

    return schemas.ProgressOut(
        note_counts=note_counts,
        total_records=total_records,
        total_patients=total_patients,
        total_syndromes=total_syndromes,
        top_syndromes=[{"syndrome": s, "count": c}
                       for s, c in syndrome_rows if s],
    )


@router.post("/notes/delete", response_model=schemas.NoteBatchResult)
def delete_notes(
    payload: schemas.NoteBatchRequest,
    db: Session = Depends(get_db),
) -> schemas.NoteBatchResult:
    """软删除选中的学习心得。"""
    ids = payload.note_ids
    if not ids:
        raise HTTPException(status_code=400, detail="请选择要删除的心得")
    result = db.execute(
        update(LearningNote)
        .where(LearningNote.note_id.in_(ids))
        .values(is_deleted=True)
    )
    db.commit()
    return schemas.NoteBatchResult(deleted=result.rowcount or 0)


@router.post("/notes/export")
def export_notes(
    payload: schemas.NoteBatchRequest,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """把选中的学习心得导出为 Word 汇编（含导师点评）。"""
    ids = payload.note_ids
    if not ids:
        raise HTTPException(status_code=400, detail="请选择要导出的心得")
    buf = generate_notes_report(db, ids)
    if buf is None:
        raise HTTPException(status_code=404, detail="心得不存在")
    filename = f"notes-{datetime.now().strftime('%Y%m%d-%H%M%S')}.docx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
