"""Herb name resolution against the dictionary.

Entered herb names are kept verbatim in ``prescription_item.herb_name`` so
the original wording survives, while a resolved ``herb_id`` and a
normalised name feed the statistics. This module performs that resolution.

Resolution order
----------------
1. **Exact match** on the standard name.
2. **Alias match** — this is where OCR misreads land. Errors on real scans
   are almost always visually similar characters (黄芩 recorded as 黄苓,
   黄柏 as 黄相, 莪术 as 获术), and the correct form is nearly always
   already a dictionary entry, so a seeded type-4 alias fixes it outright.
3. **Normalised match** — strip whitespace, unify traditional/variant
   forms the dictionary lists, and retry.

When nothing matches, :func:`suggest_herbs` offers the closest entries so
the review screen can propose a correction instead of demanding one. A
name that matches nothing is still saved: the dictionary is a convenience,
never a gate.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session
from ulid import ULID

from .models import DictHerb, DictHerbAlias, DictSyndrome, DictTerm

#: Aliases of this type are known OCR misreads; they resolve silently.
OCR_MISREAD = 4

#: Minimum similarity before a fuzzy suggestion is worth showing.
#:
#: Set at 0.5 rather than the more usual 0.6 because CJK herb names are
#: short: a single wrong character in a two-character name already halves
#: the ratio (黄岑 vs 黄芩 scores exactly 0.5). A higher cutoff would
#: reject precisely the visually-similar-character errors this feature
#: exists to catch.
SUGGESTION_CUTOFF = 0.5

# Variant characters that appear in handwritten and older prescriptions.
# Applied before a final lookup, not stored.
_NORMALISE_MAP = str.maketrans({
    "參": "参", "耆": "芪", "朮": "术", "藭": "芎", "藿": "藿",
    "麸": "麸", "澀": "涩", "黃": "黄", "蘇": "苏", "陳": "陈",
})


@dataclass(frozen=True)
class HerbResolution:
    """Outcome of resolving one entered herb name."""

    entered: str
    normalised: str
    herb_id: str | None
    matched_by: str          # exact | alias | normalised | none
    is_ocr_misread: bool = False


def _normalise(name: str) -> str:
    return name.strip().translate(_NORMALISE_MAP)


def resolve_herb(session: Session, name: str) -> HerbResolution:
    """Resolve one entered herb name to a dictionary entry, if possible."""
    entered = (name or "").strip()
    if not entered:
        return HerbResolution(entered, "", None, "none")

    # 1. exact standard name
    herb_id = session.scalar(
        select(DictHerb.herb_id).where(DictHerb.herb_name == entered)
    )
    if herb_id:
        return HerbResolution(entered, entered, herb_id, "exact")

    # 2. alias, preferring known OCR misreads
    alias_rows = session.execute(
        select(DictHerbAlias.herb_id, DictHerbAlias.alias_type,
               DictHerb.herb_name)
        .join(DictHerb, DictHerb.herb_id == DictHerbAlias.herb_id)
        .where(DictHerbAlias.alias == entered)
        .order_by(DictHerbAlias.alias_type.desc())
    ).all()
    if alias_rows:
        herb_id, alias_type, standard = alias_rows[0]
        return HerbResolution(
            entered, standard, herb_id, "alias",
            is_ocr_misread=alias_type == OCR_MISREAD,
        )

    # 3. variant-character normalisation, then retry both lookups
    cleaned = _normalise(entered)
    if cleaned != entered:
        herb_id = session.scalar(
            select(DictHerb.herb_id).where(DictHerb.herb_name == cleaned)
        )
        if herb_id:
            return HerbResolution(entered, cleaned, herb_id, "normalised")
        alias = session.execute(
            select(DictHerbAlias.herb_id, DictHerb.herb_name)
            .join(DictHerb, DictHerb.herb_id == DictHerbAlias.herb_id)
            .where(DictHerbAlias.alias == cleaned)
        ).first()
        if alias:
            return HerbResolution(entered, alias[1], alias[0], "normalised")

    return HerbResolution(entered, entered, None, "none")


def resolve_herbs(session: Session, names: list[str]) -> list[HerbResolution]:
    return [resolve_herb(session, name) for name in names]


def suggest_herbs(session: Session, name: str,
                  limit: int = 5) -> list[tuple[str, str, float]]:
    """Closest dictionary entries as ``(herb_id, herb_name, similarity)``.

    Candidates are compared on both standard names and aliases, so an
    unlisted misread of a listed alias is still recoverable. Uses difflib
    rather than a heavier similarity library: at dictionary scale the
    difference is immaterial and the stdlib dependency is free.
    """
    target = _normalise(name)
    if not target:
        return []

    candidates: list[tuple[str, str]] = [
        (herb_id, herb_name)
        for herb_id, herb_name in session.execute(
            select(DictHerb.herb_id, DictHerb.herb_name)
        )
    ]
    candidates += [
        (herb_id, herb_name)
        for herb_id, herb_name in session.execute(
            select(DictHerbAlias.herb_id, DictHerb.herb_name)
            .join(DictHerb, DictHerb.herb_id == DictHerbAlias.herb_id)
        )
    ]

    scored: dict[str, tuple[str, float]] = {}
    for herb_id, herb_name in candidates:
        ratio = difflib.SequenceMatcher(None, target, herb_name).ratio()
        if ratio < SUGGESTION_CUTOFF:
            continue
        if herb_id not in scored or ratio > scored[herb_id][1]:
            scored[herb_id] = (herb_name, ratio)

    ranked = sorted(scored.items(), key=lambda item: item[1][1], reverse=True)
    return [(herb_id, name_, ratio) for herb_id, (name_, ratio) in ranked[:limit]]


__all__ = ["HerbResolution", "OCR_MISREAD", "resolve_herb", "resolve_herbs",
           "suggest_herbs", "collect_dictionary"]


# ---------------------------------------------------------------------------
# 半自动字典收集
# ---------------------------------------------------------------------------

def _split(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"[、，；;,\s]+", text or "") if p.strip()]


def collect_dictionary(session: Session, payload) -> int:
    """从病案 payload 收集字典未收录的新药名/证型/术语（半自动）。

    只登记归一失败的真·新词，已匹配的不动；自动条目以 is_auto=1 标记，
    便于在字典维护页识别与整理。返回新增条数。
    """
    added = 0
    added += _collect_herbs(session, [h.herb_name for h in payload.herbs])
    added += _collect_syndromes(session, payload.diagnosis.syndrome)
    added += _collect_terms(session, payload.narrative)
    return added


def _collect_herbs(session: Session, names: list[str]) -> int:
    added = 0
    seen: set[str] = set()
    for raw in names:
        name = (raw or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        if resolve_herb(session, name).matched_by != "none":
            continue
        session.add(DictHerb(
            herb_id=str(ULID()), herb_name=name, is_auto=True,
            is_common=False,  # 自动收集的新药先不作常用药
        ))
        added += 1
    return added


def _collect_syndromes(session: Session, syndrome_text: str) -> int:
    added = 0
    for part in _split(syndrome_text):
        exists = session.scalar(
            select(DictSyndrome.syndrome_id)
            .where(DictSyndrome.syndrome_name == part)
        )
        if exists:
            continue
        session.add(DictSyndrome(
            syndrome_id=str(ULID()), syndrome_name=part, is_auto=True))
        added += 1
    return added


def _collect_terms(session: Session, narrative) -> int:
    added = 0
    for term_type, field in ((1, "body_of_tongue"), (2, "fur_of_tongue"),
                             (3, "pulse")):
        value = getattr(narrative, field, "") or ""
        for part in _split(value):
            exists = session.scalar(
                select(DictTerm.term_id)
                .where(DictTerm.term_type == term_type, DictTerm.term == part)
            )
            if exists:
                continue
            session.add(DictTerm(
                term_type=term_type, term=part, is_auto=True))
            added += 1
    return added
