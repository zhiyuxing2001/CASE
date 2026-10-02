"""系统表：audit_log · app_setting.

``audit_log`` is what makes a study record trustworthy: every field-level
change to a case is recorded with its previous and new value, so the
learning history cannot be quietly rewritten.

Secrets do not belong here. API keys live in ``.env``, which is
gitignored; ``app_setting`` holds only non-sensitive preferences.
"""

from __future__ import annotations

from sqlalchemy import Column, Integer, TIMESTAMP, Text

from .base import Base, now
from .types import UnsignedTinyInt


class AuditLog(Base):
    """审计日志表 — field-level change history."""

    __tablename__ = "audit_log"

    log_id = Column(Integer, primary_key=True, autoincrement=True,
                    doc="日志编号")
    table_name = Column(Text, nullable=False, index=True, doc="被修改的表名")
    record_pk = Column(Text, nullable=False, doc="被修改记录的主键值")
    action = Column(UnsignedTinyInt, nullable=False,
                    doc="操作类型，详见附表A17")
    field_name = Column(Text, nullable=False, default="",
                        doc="字段名，修改操作记录到字段级")
    old_value = Column(Text, nullable=False, default="", doc="旧值")
    new_value = Column(Text, nullable=False, default="", doc="新值")
    changed_at = Column(TIMESTAMP, nullable=False, default=now, index=True,
                        doc="修改时间")
    note = Column(Text, nullable=False, default="",
                  doc="备注，如“AI归一化”“患者信息脱敏”")


class AppSetting(Base):
    """应用设置表 — non-sensitive preferences only."""

    __tablename__ = "app_setting"

    key = Column(Text, primary_key=True, doc="设置项")
    value = Column(Text, nullable=False, default="", doc="设置值")
    updated_at = Column(TIMESTAMP, nullable=True, onupdate=now, doc="修改时间")
