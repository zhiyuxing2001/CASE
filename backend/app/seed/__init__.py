"""Dictionary seeding.

Seed content lives in :mod:`app.seed.data` as plain Python literals; this
module turns it into rows. Seeding is idempotent — it matches on natural
keys (herb name, syndrome name, formula name, term) so re-running
``init_db.py`` never duplicates an entry, and it never overwrites a row a
user has since edited.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from ulid import ULID

from ..models import (DictFormula, DictHerb, DictHerbAlias, DictSyndrome,
                      DictTerm)

try:  # pragma: no cover - the data module is generated content
    from . import data as seed_data
except ImportError:  # pragma: no cover
    seed_data = None  # type: ignore[assignment]


def _new_id() -> str:
    return str(ULID())


def _rows(name: str) -> list[dict[str, Any]]:
    if seed_data is None:
        return []
    return list(getattr(seed_data, name, []) or [])


def _seed_herbs(session: Session) -> int:
    """Insert base herbs, then processed herbs linked to their parent.

    Processed herbs are inserted second so ``parent_herb_id`` can be
    resolved against rows that already exist in the same pass.
    """
    added = 0
    known: dict[str, str] = {
        name: herb_id
        for name, herb_id in session.execute(
            select(DictHerb.herb_name, DictHerb.herb_id)
        )
    }

    for row in _rows("HERBS"):
        name = (row.get("name") or "").strip()
        if not name or name in known:
            continue
        herb_id = _new_id()
        session.add(DictHerb(
            herb_id=herb_id,
            herb_name=name,
            pinyin=row.get("pinyin", ""),
            category=row.get("category", ""),
            nature=row.get("nature", ""),
            flavor=row.get("flavor", ""),
            meridians=row.get("meridians", ""),
            functions=row.get("functions", ""),
            is_processed=False,
        ))
        known[name] = herb_id
        added += 1

    session.flush()

    for row in _rows("PROCESSED_HERBS"):
        name = (row.get("herb") or "").strip()
        parent = (row.get("parent") or "").strip()
        if not name or name in known:
            continue
        if parent not in known:
            # Parent herb is not in the dictionary; skip rather than
            # store a dangling reference.
            continue
        herb_id = _new_id()
        session.add(DictHerb(
            herb_id=herb_id,
            herb_name=name,
            parent_herb_id=known[parent],
            is_processed=True,
            processing=row.get("processing", ""),
        ))
        known[name] = herb_id
        added += 1
    return added


def _seed_aliases(session: Session) -> int:
    herbs: dict[str, str] = {
        name: herb_id
        for name, herb_id in session.execute(
            select(DictHerb.herb_name, DictHerb.herb_id)
        )
    }
    existing = {
        (herb_id, alias)
        for herb_id, alias in session.execute(
            select(DictHerbAlias.herb_id, DictHerbAlias.alias)
        )
    }
    added = 0
    for row in _rows("ALIASES"):
        herb = (row.get("herb") or "").strip()
        alias = (row.get("alias") or "").strip()
        herb_id = herbs.get(herb)
        if not herb_id or not alias or (herb_id, alias) in existing:
            continue
        session.add(DictHerbAlias(
            herb_id=herb_id,
            alias=alias,
            alias_type=int(row.get("alias_type", 0) or 0),
            ambiguity_note=row.get("ambiguity_note", ""),
            source=row.get("source", ""),
        ))
        existing.add((herb_id, alias))
        added += 1
    return added


def _seed_syndromes(session: Session) -> int:
    existing = set(session.scalars(select(DictSyndrome.syndrome_name)))
    added = 0
    for row in _rows("SYNDROMES"):
        name = (row.get("name") or "").strip()
        if not name or name in existing:
            continue
        session.add(DictSyndrome(
            syndrome_id=_new_id(),
            syndrome_name=name,
            category=row.get("category", ""),
            key_symptoms=row.get("key_symptoms", ""),
            treatment=row.get("treatment", ""),
            common_formula=row.get("common_formula", ""),
            description=row.get("description", ""),
        ))
        existing.add(name)
        added += 1
    return added


def _seed_formulas(session: Session) -> int:
    syndromes: dict[str, str] = {
        name: syndrome_id
        for name, syndrome_id in session.execute(
            select(DictSyndrome.syndrome_name, DictSyndrome.syndrome_id)
        )
    }
    existing = set(session.scalars(select(DictFormula.formula_name)))
    added = 0
    for row in _rows("FORMULAS"):
        name = (row.get("name") or "").strip()
        if not name or name in existing:
            continue
        syndrome_name = (row.get("syndrome") or "").strip()
        session.add(DictFormula(
            formula_id=_new_id(),
            formula_name=name,
            alias=row.get("alias", ""),
            source=row.get("source", ""),
            category=row.get("category", ""),
            functions=row.get("functions", ""),
            indications=row.get("indications", ""),
            syndrome_id=syndromes.get(syndrome_name),
            composition_text=row.get("composition_text", ""),
            usage_text=row.get("usage_text", ""),
        ))
        existing.add(name)
        added += 1
    return added


def _seed_terms(session: Session) -> int:
    existing = {
        (term_type, term)
        for term_type, term in session.execute(
            select(DictTerm.term_type, DictTerm.term)
        )
    }
    added = 0
    for row in _rows("TERMS"):
        term = (row.get("term") or "").strip()
        term_type = int(row.get("term_type", 0) or 0)
        if not term or not term_type or (term_type, term) in existing:
            continue
        session.add(DictTerm(
            term_type=term_type,
            term=term,
            description=row.get("description", ""),
        ))
        existing.add((term_type, term))
        added += 1
    return added


def seed_dictionaries(engine: Engine) -> dict[str, int]:
    """Seed every dictionary; returns the number of rows inserted per table."""
    if seed_data is None:
        return {}

    with Session(engine) as session:
        counts = {
            "dict_herb": _seed_herbs(session),
            "dict_herb_alias": _seed_aliases(session),
            "dict_syndrome": _seed_syndromes(session),
            "dict_formula": _seed_formulas(session),
            "dict_term": _seed_terms(session),
        }
        session.commit()
        return {name: count for name, count in counts.items() if count}


__all__ = ["seed_dictionaries"]
