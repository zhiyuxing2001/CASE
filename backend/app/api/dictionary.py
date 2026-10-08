"""字典路由：药名解析与联想、证型、术语、方剂。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from ulid import ULID

from .. import schemas
from ..dictionary import resolve_herb, suggest_herbs
from ..llm import ChatRequest, Message, Task, get_router, parse_json
from ..llm import prompts
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


@router.post("/herbs/normalize", response_model=schemas.HerbResolution)
def normalize_herb(
    payload: schemas.TermNormalizeRequest,
    db: Session = Depends(get_db),
) -> schemas.HerbResolution:
    """术语归一：本地字典优先，未命中才调模型兜底。"""
    local = resolve_herb(db, payload.term)
    if local.herb_id:
        return schemas.HerbResolution(
            entered=payload.term, normalised=local.normalised,
            herb_id=local.herb_id, matched_by="local",
            is_ocr_misread=local.is_ocr_misread,
        )

    unmatched = schemas.HerbResolution(
        entered=payload.term, normalised=payload.term, herb_id=None,
        matched_by="none", is_ocr_misread=False,
    )
    router = get_router()
    if not router.configured:
        return unmatched

    candidates = [name for _, name, _ in suggest_herbs(db, payload.term, limit=10)]
    messages = [
        Message("system", prompts.get_system_prompt("term_normalize")),
        Message("user", prompts.term_normalize_user(payload.term, candidates)),
    ]
    resp = router.chat(ChatRequest(
        task=Task.TERM_NORMALIZE, messages=messages,
        json_schema={"type": "object"}, temperature=0.1,
    ))
    if resp is None or not resp.text:
        return unmatched
    try:
        parsed = parse_json(resp.text)
    except Exception:  # noqa: BLE001
        return unmatched

    normalized = parsed.get("normalized", payload.term)
    if not parsed.get("matched") or not normalized or normalized == payload.term:
        return unmatched

    herb = db.scalar(select(DictHerb).where(
        DictHerb.herb_name == normalized, DictHerb.is_active.is_(True)))
    return schemas.HerbResolution(
        entered=payload.term, normalised=normalized,
        herb_id=herb.herb_id if herb else None,
        matched_by="llm", is_ocr_misread=True,
    )


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
        schemas.TermOption(term_id=t.term_id, term_type=t.term_type or 0,
                           term=t.term, description=t.description)
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


# ---------------------------------------------------------------------------
# 字典维护（增删改，删除为软删除）
# ---------------------------------------------------------------------------

def _herb_option(h: DictHerb) -> schemas.HerbOption:
    return schemas.HerbOption(
        herb_id=h.herb_id, herb_name=h.herb_name, pinyin=h.pinyin,
        category=h.category, is_processed=bool(h.is_processed),
    )


@router.post("/herbs", response_model=schemas.HerbOption, status_code=201)
def create_herb(payload: schemas.HerbUpsert,
                db: Session = Depends(get_db)) -> schemas.HerbOption:
    herb_id = str(ULID())
    db.add(DictHerb(herb_id=herb_id, **payload.model_dump()))
    db.commit()
    return _herb_option(db.get(DictHerb, herb_id))


@router.put("/herbs/{herb_id}", response_model=schemas.HerbOption)
def update_herb(herb_id: str, payload: schemas.HerbUpsert,
                db: Session = Depends(get_db)) -> schemas.HerbOption:
    herb = db.get(DictHerb, herb_id)
    if herb is None:
        raise HTTPException(status_code=404, detail="药名不存在")
    for key, value in payload.model_dump().items():
        setattr(herb, key, value)
    db.commit()
    return _herb_option(herb)


@router.delete("/herbs/{herb_id}", status_code=204)
def delete_herb(herb_id: str, db: Session = Depends(get_db)) -> None:
    herb = db.get(DictHerb, herb_id)
    if herb is None:
        raise HTTPException(status_code=404, detail="药名不存在")
    herb.is_active = False
    db.commit()


def _syndrome_option(s: DictSyndrome) -> schemas.SyndromeOption:
    return schemas.SyndromeOption(
        syndrome_id=s.syndrome_id, syndrome_name=s.syndrome_name,
        category=s.category,
    )


@router.post("/syndromes", response_model=schemas.SyndromeOption, status_code=201)
def create_syndrome(payload: schemas.SyndromeUpsert,
                    db: Session = Depends(get_db)) -> schemas.SyndromeOption:
    syndrome_id = str(ULID())
    db.add(DictSyndrome(syndrome_id=syndrome_id, **payload.model_dump()))
    db.commit()
    return _syndrome_option(db.get(DictSyndrome, syndrome_id))


@router.put("/syndromes/{syndrome_id}", response_model=schemas.SyndromeOption)
def update_syndrome(syndrome_id: str, payload: schemas.SyndromeUpsert,
                    db: Session = Depends(get_db)) -> schemas.SyndromeOption:
    syndrome = db.get(DictSyndrome, syndrome_id)
    if syndrome is None:
        raise HTTPException(status_code=404, detail="证型不存在")
    for key, value in payload.model_dump().items():
        setattr(syndrome, key, value)
    db.commit()
    return _syndrome_option(syndrome)


@router.delete("/syndromes/{syndrome_id}", status_code=204)
def delete_syndrome(syndrome_id: str, db: Session = Depends(get_db)) -> None:
    syndrome = db.get(DictSyndrome, syndrome_id)
    if syndrome is None:
        raise HTTPException(status_code=404, detail="证型不存在")
    syndrome.is_active = False
    db.commit()


@router.post("/terms", response_model=schemas.TermOption, status_code=201)
def create_term(payload: schemas.TermUpsert,
                db: Session = Depends(get_db)) -> schemas.TermOption:
    term = DictTerm(**payload.model_dump())
    db.add(term)
    db.commit()
    return schemas.TermOption(term_id=term.term_id, term_type=term.term_type or 0,
                              term=term.term, description=term.description)


@router.put("/terms/{term_id}", response_model=schemas.TermOption)
def update_term(term_id: int, payload: schemas.TermUpsert,
                db: Session = Depends(get_db)) -> schemas.TermOption:
    term = db.get(DictTerm, term_id)
    if term is None:
        raise HTTPException(status_code=404, detail="术语不存在")
    for key, value in payload.model_dump().items():
        setattr(term, key, value)
    db.commit()
    return schemas.TermOption(term_id=term.term_id, term_type=term.term_type or 0,
                              term=term.term, description=term.description)


@router.delete("/terms/{term_id}", status_code=204)
def delete_term(term_id: int, db: Session = Depends(get_db)) -> None:
    term = db.get(DictTerm, term_id)
    if term is None:
        raise HTTPException(status_code=404, detail="术语不存在")
    term.is_active = False
    db.commit()


@router.post("/formulas", response_model=schemas.FormulaOption, status_code=201)
def create_formula(payload: schemas.FormulaUpsert,
                   db: Session = Depends(get_db)) -> schemas.FormulaOption:
    formula_id = str(ULID())
    db.add(DictFormula(formula_id=formula_id, **payload.model_dump()))
    db.commit()
    formula = db.get(DictFormula, formula_id)
    return schemas.FormulaOption(formula_id=formula.formula_id,
                                 formula_name=formula.formula_name,
                                 source=formula.source)


@router.put("/formulas/{formula_id}", response_model=schemas.FormulaOption)
def update_formula(formula_id: str, payload: schemas.FormulaUpsert,
                   db: Session = Depends(get_db)) -> schemas.FormulaOption:
    formula = db.get(DictFormula, formula_id)
    if formula is None:
        raise HTTPException(status_code=404, detail="方剂不存在")
    for key, value in payload.model_dump().items():
        setattr(formula, key, value)
    db.commit()
    return schemas.FormulaOption(formula_id=formula.formula_id,
                                 formula_name=formula.formula_name,
                                 source=formula.source)


@router.delete("/formulas/{formula_id}", status_code=204)
def delete_formula(formula_id: str, db: Session = Depends(get_db)) -> None:
    formula = db.get(DictFormula, formula_id)
    if formula is None:
        raise HTTPException(status_code=404, detail="方剂不存在")
    formula.is_active = False
    db.commit()


# 详情（维护表单编辑回填用），须定义在 /herbs/resolve、/herbs/suggest 之后
def _dump(obj) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


@router.get("/herbs/{herb_id}")
def get_herb(herb_id: str, db: Session = Depends(get_db)) -> dict:
    herb = db.get(DictHerb, herb_id)
    if herb is None:
        raise HTTPException(status_code=404, detail="药名不存在")
    return _dump(herb)


@router.get("/syndromes/{syndrome_id}")
def get_syndrome(syndrome_id: str, db: Session = Depends(get_db)) -> dict:
    syndrome = db.get(DictSyndrome, syndrome_id)
    if syndrome is None:
        raise HTTPException(status_code=404, detail="证型不存在")
    return _dump(syndrome)


@router.get("/terms/{term_id}")
def get_term(term_id: int, db: Session = Depends(get_db)) -> dict:
    term = db.get(DictTerm, term_id)
    if term is None:
        raise HTTPException(status_code=404, detail="术语不存在")
    return _dump(term)


@router.get("/formulas/{formula_id}")
def get_formula(formula_id: str, db: Session = Depends(get_db)) -> dict:
    formula = db.get(DictFormula, formula_id)
    if formula is None:
        raise HTTPException(status_code=404, detail="方剂不存在")
    return _dump(formula)
