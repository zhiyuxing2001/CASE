"""Search behaviour, including the FTS5 trigram pitfall.

The most important test here is
``test_short_terms_would_fail_on_fts_alone``: it proves the length-based
routing is load-bearing rather than defensive padding.
"""

from __future__ import annotations

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.models import CaseNarrative, Diagnosis, PrescriptionItem
from app.search import (MIN_FTS_QUERY_LEN, search_cases, search_mode)


# --------------------------------------------------------------------------
# The pitfall
# --------------------------------------------------------------------------
def test_trigram_rejects_short_terms_but_like_finds_them(
    engine: Engine, session: Session, sample_case: int
) -> None:
    """Two-character TCM terms silently fail on FTS5 trigram.

    风热, 气虚, 血瘀 and friends are among the most common search terms in
    TCM, yet the trigram tokenizer indexes three-character windows and
    returns an empty set for anything shorter — without raising. This test
    pins that behaviour down so the fallback cannot be removed by accident.
    """
    with engine.connect() as connection:
        raw_fts = connection.execute(
            text("SELECT count(*) FROM case_search_fts WHERE case_search_fts MATCH :q"),
            {"q": '"弦细"'},
        ).scalar_one()
        raw_like = connection.execute(
            text("SELECT count(*) FROM case_search WHERE search_text LIKE :q"),
            {"q": "%弦细%"},
        ).scalar_one()

    assert raw_fts == 0, "trigram 不应匹配 2 字查询；FTS5 行为已变化，需重审路由"
    assert raw_like == 1

    # The routed API returns the hit the raw FTS query missed.
    hits = search_cases(session, "弦细")
    assert [h["record_id"] for h in hits] == [sample_case]


def test_all_short_tcm_terms_are_findable(
    session: Session, sample_case: int
) -> None:
    """Every two-character term in the sample must be reachable."""
    for term in ("柴胡", "弦细", "嗳气", "薄白", "淡红"):
        assert search_cases(session, term), f"{term} 应能检索到"


def test_routing_boundary() -> None:
    assert search_mode("ab") == "like"
    assert search_mode("abc") == "fts"
    assert search_mode("胃脘") == "like"          # 2 chars
    assert search_mode("胃脘痛") == "fts"          # 3 chars
    assert MIN_FTS_QUERY_LEN == 3


# --------------------------------------------------------------------------
# FTS path
# --------------------------------------------------------------------------
def test_three_character_terms_use_fts(
    engine: Engine, session: Session, sample_case: int
) -> None:
    with engine.connect() as connection:
        indexed = connection.execute(
            text("SELECT count(*) FROM case_search_fts WHERE case_search_fts MATCH :q"),
            {"q": '"胃脘胀痛"'},
        ).scalar_one()
    assert indexed == 1
    assert search_cases(session, "胃脘胀痛")[0]["record_id"] == sample_case


def test_search_covers_every_contributing_table(
    session: Session, sample_case: int
) -> None:
    """Text from the narrative, diagnosis, treatment and herbs is indexed."""
    for term in ("胃脘胀痛",      # case_narrative
                 "肝胃不和证",    # diagnosis
                 "疏肝理气",      # treatment
                 "白芍"):         # prescription_item
        assert search_cases(session, term), term


def test_empty_keyword_returns_nothing(session: Session, sample_case: int) -> None:
    assert search_cases(session, "") == []
    assert search_cases(session, "   ") == []


# --------------------------------------------------------------------------
# Index maintenance
# --------------------------------------------------------------------------
def test_index_follows_narrative_updates(
    session: Session, sample_case: int
) -> None:
    assert search_cases(session, "腰膝酸软") == []

    narrative = session.get(CaseNarrative, sample_case)
    narrative.present_illness = "近加腰膝酸软，夜尿频。"
    session.commit()

    assert search_cases(session, "腰膝酸软"), "更新后应能检索到新内容"


def test_index_follows_herb_changes(session: Session, sample_case: int) -> None:
    assert search_cases(session, "茯苓") == []

    session.add(PrescriptionItem(
        record_id=sample_case, patient_id="P-TEST", sequence=9,
        herb_name="茯苓", herb_name_norm="茯苓", dose=15, unit="g",
    ))
    session.commit()

    assert search_cases(session, "茯苓"), "新增药味后应能检索到"


def test_index_drops_deleted_visits(session: Session, sample_case: int) -> None:
    assert search_cases(session, "胃脘胀痛")

    session.delete(session.get(Diagnosis, sample_case))
    session.delete(session.get(CaseNarrative, sample_case))
    session.commit()

    # Narrative gone, so its text is no longer indexed.
    assert search_cases(session, "胃脘胀痛") == []


def test_soft_deleted_visits_are_excluded(
    session: Session, sample_case: int
) -> None:
    from app.models import InfoRecord

    record = session.get(InfoRecord, sample_case)
    record.is_deleted = True
    session.commit()
    assert search_cases(session, "胃脘胀痛") == []


def test_rebuild_search_index_restores_consistency(
    engine: Engine, session: Session, sample_case: int
) -> None:
    from app.search import rebuild_search_index

    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM case_search")

    assert search_cases(session, "胃脘胀痛") == []

    indexed = rebuild_search_index(engine)
    assert indexed == 1
    assert search_cases(session, "胃脘胀痛")


def test_search_cases_multi_extracts_terms_from_question(
    session: Session, sample_case: int
) -> None:
    """自然语言问题能抽取术语并检索到病案（证型名优先）。"""
    from app.models import DictSyndrome
    from app.search import extract_terms, search_cases_multi

    session.add(DictSyndrome(syndrome_id="S-QA", syndrome_name="肝胃不和证"))
    session.commit()

    terms = extract_terms(session, "肝胃不和证在我整理的病案里怎么治？")
    assert "肝胃不和证" in terms

    hits = search_cases_multi(session, "肝胃不和证在我整理的病案里怎么治？")
    assert hits
    assert hits[0]["record_id"] == sample_case
