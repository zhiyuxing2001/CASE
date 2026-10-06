"""病案病程（系列）列表。

一个「病案」是一段病程：初诊为系列头（father_id 指向自身），后续复诊/
随诊同属该系列。列表因此按系列聚合，每系列一行，而非每次就诊一行。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import schemas
from .deps import get_db

router = APIRouter(prefix="/api/courses", tags=["courses"])

_SELECT = """
SELECT
  r.record_id   AS course_id,
  r.patient_id  AS patient_id,
  p.patient_name AS patient_name,
  r.clinic_date AS first_date,
  n.complaint   AS complaint,
  d.syndrome    AS syndrome,
  d.tcm_disease AS tcm_disease,
  m.mentor_name AS mentor_name,
  (SELECT COUNT(*) FROM info_record v
     WHERE v.father_id = r.record_id AND v.is_deleted = 0) AS visit_count,
  (SELECT MAX(v.clinic_date) FROM info_record v
     WHERE v.father_id = r.record_id AND v.is_deleted = 0) AS last_date,
  EXISTS(SELECT 1 FROM info_record v
           JOIN prescription_item pi ON pi.record_id = v.record_id
          WHERE v.father_id = r.record_id AND pi.needs_review = 1) AS needs_review
FROM info_record r
JOIN info_patient p ON p.patient_id = r.patient_id
LEFT JOIN case_narrative n ON n.record_id = r.record_id
LEFT JOIN diagnosis d ON d.record_id = r.record_id
LEFT JOIN mentor m ON m.mentor_id = r.mentor_id
WHERE r.father_id = r.record_id AND r.is_deleted = 0
"""

_COUNT = """
SELECT COUNT(*)
FROM info_record r
JOIN info_patient p ON p.patient_id = r.patient_id
LEFT JOIN case_narrative n ON n.record_id = r.record_id
LEFT JOIN diagnosis d ON d.record_id = r.record_id
WHERE r.father_id = r.record_id AND r.is_deleted = 0
"""


def _as_date(value) -> date:
    return date.fromisoformat(str(value)) if value is not None else None


@router.get("", response_model=schemas.CourseList)
def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = "",
    syndrome: str = "",
    mentor_id: str = "",
    db: Session = Depends(get_db),
) -> schemas.CourseList:
    where = ""
    params: dict = {}
    if q:
        where += " AND (p.patient_name LIKE :q OR n.complaint LIKE :q OR d.syndrome LIKE :q)"
        params["q"] = f"%{q}%"
    if syndrome:
        where += " AND d.syndrome LIKE :syndrome"
        params["syndrome"] = f"%{syndrome}%"
    if mentor_id:
        where += " AND r.mentor_id = :mentor_id"
        params["mentor_id"] = mentor_id

    total = db.execute(text(_COUNT + where), params).scalar() or 0
    rows = db.execute(
        text(_SELECT + where + " ORDER BY r.clinic_date DESC LIMIT :lim OFFSET :off"),
        {**params, "lim": page_size, "off": (page - 1) * page_size},
    ).all()

    items = [
        schemas.CourseSummary(
            course_id=row.course_id,
            patient_id=row.patient_id,
            patient_name=row.patient_name or "",
            first_date=_as_date(row.first_date),
            last_date=_as_date(row.last_date) or _as_date(row.first_date),
            visit_count=row.visit_count or 1,
            complaint=row.complaint or "",
            syndrome=row.syndrome or "",
            tcm_disease=row.tcm_disease or "",
            mentor_name=row.mentor_name or "",
            needs_review=bool(row.needs_review),
        )
        for row in rows
    ]
    return schemas.CourseList(total=total, page=page, page_size=page_size, items=items)
