"""Field-level audit trail.

``audit_log`` exists so a study record cannot be quietly rewritten: every
change to a clinical table is recorded with the field, its previous value
and its new value.

How it works
------------
Column history is only available *before* a flush, but an inserted row
only has its primary key *after* the flush. The listener therefore runs
in two stages: :func:`_capture` collects pending changes during
``before_flush``, and :func:`_write` turns them into ``audit_log`` rows
during ``after_flush``, by which point every key is known.

Auditing is opt-in via :func:`enable_audit`, so tests and bulk imports can
choose not to generate a trail.
"""

from __future__ import annotations

from typing import Any, Iterator

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session, sessionmaker

from .models import AuditLog

#: Tables whose changes are worth tracing — the case itself and the
#: dictionary rows a user can edit. OCR job bookkeeping is excluded: it is
#: machine output and already carries its own timestamps and status.
AUDITED_TABLES: frozenset[str] = frozenset({
    "info_patient",
    "info_record",
    "case_narrative",
    "diagnosis",
    "treatment",
    "prescription_item",
    "learning_note",
    "mentor_comment",
})

# Action codes, matching 附表A17.
INSERT, UPDATE, DELETE, RESTORE, MASK = 0, 1, 2, 3, 4


def _table_name(obj: Any) -> str | None:
    mapper = inspect(obj, raiseerr=False)
    return None if mapper is None else mapper.mapper.local_table.name


def _primary_key(obj: Any) -> str:
    mapper = inspect(obj).mapper
    values = [getattr(obj, column.key, None) for column in mapper.primary_key]
    return "|".join("" if value is None else str(value) for value in values)


def _render(value: Any) -> str:
    return "" if value is None else str(value)


def _changed_fields(obj: Any) -> Iterator[tuple[str, str, str]]:
    """Yield ``(field, old, new)`` for every modified column of a row."""
    state = inspect(obj)
    for attribute in state.attrs:
        history = attribute.history
        if not history.has_changes():
            continue
        old = history.deleted[0] if history.deleted else None
        new = history.added[0] if history.added else None
        yield attribute.key, _render(old), _render(new)


def _capture(session: Session) -> list[dict[str, Any]]:
    """Collect pending changes before the flush clears column history."""
    captured: list[dict[str, Any]] = []

    for obj in session.new:
        table = _table_name(obj)
        if table in AUDITED_TABLES:
            captured.append({"action": INSERT, "obj": obj, "field": "",
                             "old": "", "new": "", "note": ""})

    for obj in session.dirty:
        table = _table_name(obj)
        if table not in AUDITED_TABLES:
            continue
        if not session.is_modified(obj, include_collections=False):
            continue
        for field, old, new in _changed_fields(obj):
            captured.append({"action": UPDATE, "obj": obj, "field": field,
                             "old": old, "new": new, "note": ""})

    for obj in session.deleted:
        table = _table_name(obj)
        if table in AUDITED_TABLES:
            captured.append({"action": DELETE, "obj": obj, "field": "",
                             "old": "", "new": "", "note": ""})

    return captured


def enable_audit(factory: sessionmaker[Session]) -> None:
    """Attach the two-stage audit listener to a session factory."""

    @event.listens_for(factory, "before_flush")
    def _before_flush(session: Session, _context, _instances) -> None:  # noqa: ANN001
        if session.info.get("_audit_off"):
            return
        session.info["_audit_pending"] = _capture(session)

    @event.listens_for(factory, "after_flush")
    def _after_flush(session: Session, _context) -> None:  # noqa: ANN001
        pending = session.info.pop("_audit_pending", None)
        if not pending:
            return
        for entry in pending:
            obj = entry["obj"]
            session.add(AuditLog(
                table_name=_table_name(obj) or "",
                record_pk=_primary_key(obj),
                action=entry["action"],
                field_name=entry["field"],
                old_value=entry["old"],
                new_value=entry["new"],
                note=entry["note"],
            ))


class suspend_audit:
    """Context manager that suppresses audit rows (bulk import, migration)."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.previous = False

    def __enter__(self) -> "suspend_audit":
        self.previous = bool(self.session.info.get("_audit_off"))
        self.session.info["_audit_off"] = True
        return self

    def __exit__(self, *_exc: object) -> None:
        self.session.info["_audit_off"] = self.previous


__all__ = ["AUDITED_TABLES", "enable_audit", "suspend_audit",
           "INSERT", "UPDATE", "DELETE", "RESTORE", "MASK"]
