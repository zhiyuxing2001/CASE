"""病案分析：基于结构化字段的频次统计。

舌质、舌苔、脉象、证型、中医病名与药味明细是刻意保留的结构化字段，
本模块正是它们的用途所在——支撑检索之外，还支撑频次与剂量分析。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import schemas
from .deps import get_db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

_OVERVIEW = """
SELECT
  (SELECT COUNT(DISTINCT course_id) FROM info_record
     WHERE is_deleted = 0 AND course_id != '') AS total_courses,
  (SELECT COUNT(*) FROM info_record WHERE is_deleted = 0) AS total_visits,
  (SELECT COUNT(*) FROM info_patient WHERE is_deleted = 0) AS total_patients,
  (SELECT COUNT(*) FROM prescription_item) AS total_herbs,
  (SELECT COUNT(DISTINCT herb_name_norm) FROM prescription_item
     WHERE herb_name_norm != '') AS distinct_herbs,
  (SELECT COUNT(DISTINCT syndrome) FROM diagnosis
     WHERE syndrome != '') AS distinct_syndromes
"""


def _freq_rows(db: Session, sql: str, params: dict) -> list[schemas.FreqItem]:
    rows = db.execute(text(sql), params).all()
    return [schemas.FreqItem(label=row[0], count=row[1]) for row in rows]


@router.get("/overview", response_model=schemas.AnalyticsOverview)
def overview(db: Session = Depends(get_db)) -> schemas.AnalyticsOverview:
    row = db.execute(text(_OVERVIEW)).one()
    return schemas.AnalyticsOverview(
        total_courses=row.total_courses or 0,
        total_visits=row.total_visits or 0,
        total_patients=row.total_patients or 0,
        total_herbs=row.total_herbs or 0,
        distinct_herbs=row.distinct_herbs or 0,
        distinct_syndromes=row.distinct_syndromes or 0,
    )


@router.get("/syndromes", response_model=list[schemas.FreqItem])
def syndromes(
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return _freq_rows(db, """
        SELECT syndrome AS label, COUNT(*) AS c
          FROM diagnosis
         WHERE syndrome != ''
         GROUP BY syndrome ORDER BY c DESC LIMIT :lim
    """, {"lim": limit})


@router.get("/herbs", response_model=list[schemas.HerbFreq])
def herbs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows = db.execute(text("""
        SELECT herb_name_norm AS name, COUNT(*) AS c, AVG(dose) AS avg_dose
          FROM prescription_item
         WHERE herb_name_norm != ''
         GROUP BY herb_name_norm
         ORDER BY c DESC, name LIMIT :lim
    """), {"lim": limit}).all()
    return [
        schemas.HerbFreq(
            label=row.name,
            count=row.c,
            avg_dose=round(row.avg_dose, 1) if row.avg_dose is not None else None,
        )
        for row in rows
    ]


@router.get("/tongue", response_model=schemas.TongueDist)
def tongue(db: Session = Depends(get_db)) -> schemas.TongueDist:
    def col(column: str) -> list[schemas.FreqItem]:
        return _freq_rows(db, f"""
            SELECT {column} AS label, COUNT(*) AS c
              FROM case_narrative
             WHERE {column} != ''
             GROUP BY {column} ORDER BY c DESC LIMIT 10
        """, {})

    return schemas.TongueDist(
        body=col("body_of_tongue"),
        coating=col("fur_of_tongue"),
        pulse=col("pulse"),
    )


@router.get("/diseases", response_model=list[schemas.FreqItem])
def diseases(
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return _freq_rows(db, """
        SELECT tcm_disease AS label, COUNT(*) AS c
          FROM diagnosis
         WHERE tcm_disease != ''
         GROUP BY tcm_disease ORDER BY c DESC LIMIT :lim
    """, {"lim": limit})
