"""Herb name resolution: normalisation and OCR misread correction."""

from __future__ import annotations

import pytest
from sqlalchemy import Engine

from app.dictionary import resolve_herb, resolve_herbs, suggest_herbs
from app.models import Base
from app.search import install_search_schema
from app.seed import seed_dictionaries
from sqlalchemy.orm import Session


@pytest.fixture()
def dict_session(engine: Engine) -> Session:
    Base.metadata.create_all(engine)
    install_search_schema(engine)
    seed_dictionaries(engine)
    with Session(engine) as session:
        yield session


@pytest.mark.parametrize("wrong,right", [
    ("黄苓", "黄芩"),      # 苓 / 芩
    ("盐黄相", "黄柏"),    # 相 / 柏
    ("获术", "莪术"),      # 获 / 莪
    ("古参", "苦参"),      # 古 / 苦
    ("紫苑", "紫菀"),      # 苑 / 菀
    ("山查", "山楂"),      # 查 / 楂
    ("积实", "枳实"),      # 积 / 枳
    ("川弓", "川芎"),      # 弓 / 芎
])
def test_ocr_misreads_resolve_to_the_right_herb(
    dict_session: Session, wrong: str, right: str
) -> None:
    """These misreads were observed on the real scanned prescriptions."""
    resolution = resolve_herb(dict_session, wrong)
    assert resolution.normalised == right
    assert resolution.herb_id
    assert resolution.is_ocr_misread


def test_exact_name_takes_precedence(dict_session: Session) -> None:
    resolution = resolve_herb(dict_session, "黄芩")
    assert resolution.matched_by == "exact"
    assert resolution.normalised == "黄芩"


def test_prescription_style_alias_resolves(dict_session: Session) -> None:
    """生地 is how prescriptions write 生地黄."""
    resolution = resolve_herb(dict_session, "生地")
    assert resolution.normalised == "生地黄"
    assert resolution.matched_by == "alias"
    assert not resolution.is_ocr_misread


def test_processed_herb_is_its_own_entry(dict_session: Session) -> None:
    """盐黄柏 resolves as a herb in its own right, not as an alias of 黄柏."""
    resolution = resolve_herb(dict_session, "盐黄柏")
    assert resolution.matched_by == "exact"
    assert resolution.normalised == "盐黄柏"


def test_unknown_name_is_returned_unresolved_not_rejected(
    dict_session: Session,
) -> None:
    """The dictionary advises; it never blocks an entry."""
    resolution = resolve_herb(dict_session, "并不存在的药")
    assert resolution.herb_id is None
    assert resolution.matched_by == "none"
    assert resolution.entered == resolution.normalised


def test_suggestions_are_offered_for_unknown_names(
    dict_session: Session,
) -> None:
    suggestions = suggest_herbs(dict_session, "黄岑")   # 岑 is not a listed alias
    assert suggestions, "应能给出相似药名建议"
    assert "黄芩" in [name for _id, name, _score in suggestions]


def test_suggestions_respect_the_cutoff(dict_session: Session) -> None:
    assert suggest_herbs(dict_session, "zzzz") == []


def test_batch_resolution_preserves_order(dict_session: Session) -> None:
    names = ["柴胡", "黄苓", "白芍", "不存在的药"]
    results = resolve_herbs(dict_session, names)
    assert [r.entered for r in results] == names
    assert results[0].herb_id and results[2].herb_id
    assert results[3].herb_id is None
