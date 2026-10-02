"""跟师学习：learning_note · mentor_comment · note_record_link.

This is what makes CASE a mentorship-learning system rather than a plain
case archive. Two integrity rules matter here:

* A mentor's comment is authoritative teaching content. ``is_ai_generated``
  keeps machine-written suggestions from ever being mistaken for it.
* ``is_ai_assisted`` records whether AI helped write a reflection, for
  academic-integrity traceability.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, TIMESTAMP, Text

from .base import Base, CreatedAtMixin, SoftDeleteMixin, TimestampsMixin, now
from .types import UnsignedTinyInt


class LearningNote(SoftDeleteMixin, TimestampsMixin, Base):
    """学习笔记表 — one table covers follow-up logs and reflections.

    ``note_type`` separates 跟诊日志 from 学习心得 rather than giving
    near-identical structures their own tables.
    """

    __tablename__ = "learning_note"

    note_id = Column(Text, primary_key=True, doc="笔记编号，ULID")
    note_type = Column(UnsignedTinyInt, nullable=False, default=0,
                       doc="笔记类型，详见附表A6")
    title = Column(Text, nullable=False, doc="标题，≤100个Unicode字符")
    content_md = Column(Text, nullable=False, default="",
                        doc="正文，Markdown 富文本")
    status = Column(UnsignedTinyInt, nullable=True, default=0,
                    doc="状态，详见附表A7")
    record_id = Column(Integer, ForeignKey("info_record.record_id"),
                       nullable=True, doc="关联病历编号")
    mentor_id = Column(Text, ForeignKey("mentor.mentor_id"), nullable=True,
                       doc="带教老师编号")
    word_count = Column(Integer, nullable=True, default=0,
                        doc="字数，用于学习进度统计")
    is_ai_assisted = Column(Boolean, nullable=False, default=False,
                            doc="是否使用AI辅助，界面须显式标注")


class MentorComment(CreatedAtMixin, Base):
    """导师点评表 — the authoritative voice in a mentorship relationship."""

    __tablename__ = "mentor_comment"

    comment_id = Column(Integer, primary_key=True, autoincrement=True,
                        doc="点评编号")
    target_type = Column(UnsignedTinyInt, nullable=False,
                         doc="点评对象类型，详见附表A8")
    target_id = Column(Text, nullable=False, doc="点评对象编号")
    mentor_id = Column(Text, ForeignKey("mentor.mentor_id"), nullable=True,
                       doc="老师编号")
    content = Column(Text, nullable=False, doc="点评原文")
    comment_type = Column(UnsignedTinyInt, nullable=True, default=0,
                          doc="点评类型，详见附表A9")
    is_ai_generated = Column(Boolean, nullable=False, default=False,
                             doc="是否AI生成，界面须与真实导师点评视觉区分")
    commented_at = Column(TIMESTAMP, nullable=False, default=now,
                          doc="点评时间")


class NoteRecordLink(CreatedAtMixin, Base):
    """笔记与病案关联表 — two-way reference between a reflection and a case."""

    __tablename__ = "note_record_link"

    link_id = Column(Integer, primary_key=True, autoincrement=True,
                     doc="关联编号")
    note_id = Column(Text, ForeignKey("learning_note.note_id"),
                     nullable=False, doc="笔记编号")
    record_id = Column(Integer, ForeignKey("info_record.record_id"),
                       nullable=False, doc="病历编号")
    relation = Column(UnsignedTinyInt, nullable=True, default=0,
                      doc="关联类型，详见附表A10")
    notes = Column(Text, nullable=False, default="", doc="说明")
