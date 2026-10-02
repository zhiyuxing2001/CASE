"""字典路由：药名解析与联想、证型、术语、方剂。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import schemas
from ..dictionary import resolve_herb, suggest_herbs
from ..models import DictFormula, DictHerb, DictSyndrome, DictTerm
from .deps import get_db

router = APIRouter(prefix="/api/dict", tags=["dict"])


@router.get("/herbs", response_model=list[schemas.HerbOption])
def list_herbs(
    q: str = "",
    category: str = "",
    is_processed: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(DictHerb).where(DictHerb.is_active.is_(True))
    if q:
        stmt = stmt.where(or_(
            DictHerb.herb_name.like(f"%{q}%"),
            DictHerb.pinyin.like(f"%{q.lower()}%"),
        ))
    if category:
        stmt = stmt.where(DictHerb.category == category)
    if is_processed is not None:
        stmt = stmt.where(DictHerb.is_processed.is_(is_processed))
    herbs = db.execute(stmt.order_by(DictHerb.is_common.desc(), DictHerb.herb_name).limit(limit)).scalars().all()
    return [
        schemas.HerbOption(
            herb_id=h.herb_id, herb_name=h.herb_name, pinyin=h.pinyin,
            category=h.category, is_processed=bool(h.is_processed),
        )
        for h in herbs
    ]


@router.get("/herbs/resolve", response_model=schemas.HerbResolution)
def resolve(name: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    result = resolve_herb(db, name)
    return schemas.HerbResolution(
        entered=result.entered, normalised=result.normalised,
        herb_id=result.herb_id, matched_by=result.matched_by,
        is_ocr_misread=result.is_ocr_misread,
    )


@router.get("/herbs/suggest", response_model=list[schemas.HerbSuggestion])
def suggest(
    name: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return [
        schemas.HerbSuggestion(herb_id=herb_id, herb_name=herb_name,
                               similarity=round(score, 4))
        for herb_id, herb_name, score in suggest_herbs(db, name, limit=limit)
    ]


@router.get("/syndromes", response_model=list[schemas.SyndromeOption])
def list_syndromes(
    q: str = "",
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(DictSyndrome).where(DictSyndrome.is_active.is_(True))
    if q:
        stmt = stmt.where(DictSyndrome.syndrome_name.like(f"%{q}%"))
    rows = db.execute(stmt.order_by(DictSyndrome.syndrome_name).limit(limit)).scalars().all()
    return [
        schemas.SyndromeOption(syndrome_id=s.syndrome_id,
                               syndrome_name=s.syndrome_name,
                               category=s.category)
        for s in rows
    ]


@router.get("/terms", response_model=list[schemas.TermOption])
def list_terms(
    term_type: int | None = None,
    q: str = "",
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(DictTerm).where(DictTerm.is_active.is_(True))
    if term_type is not None:
        stmt = stmt.where(DictTerm.term_type == term_type)
    if q:
        stmt = stmt.where(DictTerm.term.like(f"%{q}%"))
    rows = db.execute(
        stmt.order_by(DictTerm.usage_count.desc(), DictTerm.term).limit(limit)
    ).scalars().all()
    return [
        schemas.TermOption(term_id=t.term_id, term=t.term,
                           description=t.description)
        for t in rows
    ]


@router.get("/formulas", response_model=list[schemas.FormulaOption])
def list_formulas(
    q: str = "",
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(DictFormula).where(DictFormula.is_active.is_(True))
    if q:
        stmt = stmt.where(DictFormula.formula_name.like(f"%{q}%"))
    rows = db.execute(stmt.order_by(DictFormula.formula_name).limit(limit)).scalars().all()
    return [
        schemas.FormulaOption(formula_id=f.formula_id,
                              formula_name=f.formula_name,
                              source=f.source)
        for f in rows
    ]
