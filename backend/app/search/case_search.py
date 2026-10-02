"""Chinese full-text search over case records.

Design
------
Four tables contribute searchable text (the case narrative, the
diagnosis, the treatment and the individual herbs). Rather than indexing
each separately, they are aggregated into one row per visit in
``case_search``, which an external-content FTS5 table then indexes.
Triggers keep the aggregate in step with its sources, so a raw SQL edit
cannot silently desynchronise the index.

The pitfall this module exists to handle
----------------------------------------
FTS5's ``trigram`` tokenizer indexes three-character windows, so a query
shorter than three characters **never matches and returns an empty set
without raising an error**. In TCM that silent failure hits some of the
most frequent terms there are — 风热, 气虚, 血瘀, 肝郁, 脾虚, 痰湿, 阳虚,
阴虚. A user searching 风热 would conclude the archive has nothing.

Queries are therefore routed by length: three characters or more go to
FTS5 (indexed, ranked by bm25), anything shorter falls back to ``LIKE``.
At single-user scale the fallback is comfortably fast.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

#: Shortest query the trigram tokenizer can match.
MIN_FTS_QUERY_LEN = 3

#: Columns aggregated into the search text, per source table.
_SEARCH_SOURCES: dict[str, tuple[str, ...]] = {
    "case_narrative": (
        "complaint", "present_illness", "past_history", "personal_history",
        "allergy_history", "body_of_tongue", "fur_of_tongue", "pulse",
        "other_cond", "physical_exam", "auxiliary_exam", "notes",
    ),
    "diagnosis": (
        "tcm_disease", "syndrome", "wm_diagnosis", "patterns_analysis",
        "differential_diagnosis",
    ),
    "treatment": (
        "treatment_principle", "formula_name", "decoction", "usage",
        "advice", "other_treatment",
    ),
}

#: Tables whose changes must refresh the aggregate row.
_TRIGGER_TABLES = (
    "info_record", "case_narrative", "diagnosis", "treatment",
    "prescription_item",
)


def _aggregate_expr() -> str:
    """SQL expression concatenating every searchable column of one visit."""
    parts: list[str] = []
    for table, columns in _SEARCH_SOURCES.items():
        alias = {
            "case_narrative": "n", "diagnosis": "d", "treatment": "t",
        }[table]
        for column in columns:
            parts.append(f"coalesce({alias}.{column}, '')")
    parts.append("coalesce(p.herbs, '')")
    return " || ' ' || ".join(parts)


def _rebuild_statement(rid: str) -> str:
    """Upsert the aggregate row for one visit.

    ``rid`` is a SQL fragment: ``NEW.record_id`` or ``OLD.record_id``
    inside a trigger, or a bound parameter when rebuilding in bulk.
    """
    return f"""
INSERT INTO case_search (record_id, patient_id, search_text)
SELECT r.record_id,
       r.patient_id,
       trim({_aggregate_expr()})
  FROM info_record r
  LEFT JOIN case_narrative   n ON n.record_id = r.record_id
  LEFT JOIN diagnosis        d ON d.record_id = r.record_id
  LEFT JOIN treatment        t ON t.record_id = r.record_id
  LEFT JOIN (
        SELECT record_id,
               group_concat(
                   herb_name || ' ' || coalesce(herb_name_norm, '') || ' ' ||
                   coalesce(dose, '') || coalesce(unit, ''), ' '
               ) AS herbs
          FROM prescription_item
         GROUP BY record_id
  ) p ON p.record_id = r.record_id
 WHERE r.record_id = {rid}
ON CONFLICT(record_id) DO UPDATE
   SET patient_id = excluded.patient_id,
       search_text = excluded.search_text;
"""


def search_schema_sql() -> str:
    """DDL for the aggregate table, the FTS index and every sync trigger."""
    statements = [
        """
CREATE TABLE IF NOT EXISTS case_search (
    record_id   INTEGER PRIMARY KEY,
    patient_id  TEXT NOT NULL,
    search_text TEXT NOT NULL DEFAULT ''
);
""",
        # External-content FTS5: the text is not duplicated, the index
        # simply points back at case_search.
        """
CREATE VIRTUAL TABLE IF NOT EXISTS case_search_fts USING fts5(
    search_text,
    content='case_search',
    content_rowid='record_id',
    tokenize='trigram'
);
""",
        # Keep the FTS index in step with the aggregate table.
        """
CREATE TRIGGER IF NOT EXISTS case_search_ai AFTER INSERT ON case_search BEGIN
    INSERT INTO case_search_fts(rowid, search_text)
    VALUES (new.record_id, new.search_text);
END;
""",
        """
CREATE TRIGGER IF NOT EXISTS case_search_ad AFTER DELETE ON case_search BEGIN
    INSERT INTO case_search_fts(case_search_fts, rowid, search_text)
    VALUES ('delete', old.record_id, old.search_text);
END;
""",
        """
CREATE TRIGGER IF NOT EXISTS case_search_au AFTER UPDATE ON case_search BEGIN
    INSERT INTO case_search_fts(case_search_fts, rowid, search_text)
    VALUES ('delete', old.record_id, old.search_text);
    INSERT INTO case_search_fts(rowid, search_text)
    VALUES (new.record_id, new.search_text);
END;
""",
    ]

    # Refresh the aggregate whenever a contributing table changes.
    for table in _TRIGGER_TABLES:
        if table == "info_record":
            statements.append(f"""
CREATE TRIGGER IF NOT EXISTS case_search_src_{table}_ai
AFTER INSERT ON {table} BEGIN
{_rebuild_statement("NEW.record_id")}
END;
""")
            statements.append(f"""
CREATE TRIGGER IF NOT EXISTS case_search_src_{table}_au
AFTER UPDATE ON {table} BEGIN
{_rebuild_statement("NEW.record_id")}
END;
""")
            # The visit itself is gone: drop its search row entirely.
            statements.append(f"""
CREATE TRIGGER IF NOT EXISTS case_search_src_{table}_ad
AFTER DELETE ON {table} BEGIN
    DELETE FROM case_search WHERE record_id = old.record_id;
END;
""")
        else:
            for event, ref in (("ai", "NEW"), ("au", "NEW"), ("ad", "OLD")):
                statements.append(f"""
CREATE TRIGGER IF NOT EXISTS case_search_src_{table}_{event}
AFTER {'INSERT' if event == 'ai' else 'UPDATE' if event == 'au' else 'DELETE'}
ON {table} BEGIN
{_rebuild_statement(f"{ref}.record_id")}
END;
""")
    return "\n".join(statements)


def _exec_script(engine: Engine, script: str) -> None:
    """Run a multi-statement SQL script.

    ``driver.executescript`` is required rather than
    ``exec_driver_sql``: the trigger bodies contain semicolons, so the
    script cannot be split on ``;`` and must be handed to SQLite whole.
    """
    raw = engine.raw_connection()
    try:
        raw.executescript(script)
        raw.commit()
    finally:
        raw.close()


def install_search_schema(engine: Engine) -> None:
    """Create the aggregate table, FTS index and triggers (idempotent)."""
    _exec_script(engine, search_schema_sql())


def rebuild_search_index(engine: Engine) -> int:
    """Rebuild the aggregate from scratch and reindex FTS5.

    Used after a bulk import or a migration, where per-row triggers would
    be needlessly slow.
    """
    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM case_search")
        # No WHERE clause: rebuild every visit.
        connection.exec_driver_sql(_rebuild_statement("r.record_id"))
        connection.exec_driver_sql(
            "INSERT INTO case_search_fts(case_search_fts) VALUES('rebuild')"
        )
        return connection.execute(
            text("SELECT count(*) FROM case_search")
        ).scalar_one()


def _fts_phrase(keyword: str) -> str:
    """Quote a keyword so FTS5 treats it as a literal phrase."""
    return '"' + keyword.replace('"', '""') + '"'


def search_mode(keyword: str) -> str:
    """Which engine a keyword will use — ``fts`` or ``like``.

    Exposed so the routing rule is testable and visible rather than
    buried in the query builder.
    """
    return "fts" if len(keyword.strip()) >= MIN_FTS_QUERY_LEN else "like"


def search_cases(
    session: Session,
    keyword: str,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Search case records, routing short queries away from FTS5.

    Returns records ordered by relevance for FTS5 queries and by date for
    the ``LIKE`` fallback.
    """
    term = (keyword or "").strip()
    if not term:
        return []

    if search_mode(term) == "fts":
        sql = text("""
            SELECT r.record_id, r.patient_id, r.clinic_date,
                   s.search_text, bm25(case_search_fts) AS rank
              FROM case_search_fts
              JOIN case_search  s ON s.record_id = case_search_fts.rowid
              JOIN info_record  r ON r.record_id = case_search_fts.rowid
             WHERE case_search_fts MATCH :q
               AND r.is_deleted = 0
             ORDER BY rank
             LIMIT :lim
        """)
        params = {"q": _fts_phrase(term), "lim": limit}
    else:
        sql = text("""
            SELECT r.record_id, r.patient_id, r.clinic_date,
                   s.search_text, 0.0 AS rank
              FROM case_search s
              JOIN info_record r ON r.record_id = s.record_id
             WHERE s.search_text LIKE :q
               AND r.is_deleted = 0
             ORDER BY r.clinic_date DESC
             LIMIT :lim
        """)
        params = {"q": f"%{term}%", "lim": limit}

    return [dict(row._mapping) for row in session.execute(sql, params)]
