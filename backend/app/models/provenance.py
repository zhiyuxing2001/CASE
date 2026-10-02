"""来源与溯源：source_document · attachment · ocr_job · ocr_field_confidence.

The chain answers "which line of which image did this field come from" —
essential here because OCR output is a suggestion that a human confirms,
and because printed and handwritten content differ sharply in how far
they can be trusted.
"""

from __future__ import annotations

from sqlalchemy import (JSON, Boolean, Column, ForeignKey, Integer, REAL,
                        Text)

from .base import Base, CreatedAtMixin, CreatedAtMixin as _CA, SoftDeleteMixin
from .types import UnsignedTinyInt


class SourceDocument(CreatedAtMixin, Base):
    """来源单据表 — one row per physical source document.

    Real samples showed the same course of treatment arriving as a
    handwritten teaching form, a printed HIS record, or an HIS screenshot.
    The source determines both the parsing strategy and how much the
    extracted text can be trusted.
    """

    __tablename__ = "source_document"

    doc_id = Column(Text, primary_key=True, doc="单据编号，ULID")
    doc_type = Column(UnsignedTinyInt, nullable=False,
                      doc="单据类型，详见附表A11")
    template_name = Column(Text, nullable=False, default="",
                           doc="表单模板名，如“跟师学习临床医案”")
    hospital = Column(Text, nullable=False, default="", doc="机构名称")
    page_count = Column(Integer, nullable=True, default=1, doc="页数")
    ocr_strategy = Column(UnsignedTinyInt, nullable=True, default=0,
                          doc="解析策略，详见附表A12")
    file_name_origin = Column(Text, nullable=False, default="",
                              doc="原始文件名，可辅助推断元数据")
    notes = Column(Text, nullable=False, default="", doc="备注")


class Attachment(SoftDeleteMixin, CreatedAtMixin, Base):
    """附件表 — file bytes live under ``data/attachments/``; only the path
    and hash are stored."""

    __tablename__ = "attachment"

    attach_id = Column(Text, primary_key=True, doc="附件编号，ULID")
    record_id = Column(Integer, ForeignKey("info_record.record_id"),
                       nullable=True, doc="病历编号；可先上传后关联")
    doc_id = Column(Text, ForeignKey("source_document.doc_id"), nullable=True,
                    doc="单据编号")
    file_path = Column(Text, nullable=False, doc="相对 data/ 的文件路径")
    thumb_path = Column(Text, nullable=False, default="", doc="缩略图路径")
    file_type = Column(UnsignedTinyInt, nullable=False,
                       doc="文件类型，详见附表A13")
    mime_type = Column(Text, nullable=False, default="",
                       doc="MIME类型，按文件实际内容判断")
    file_size = Column(Integer, nullable=True, default=0, doc="文件大小（字节）")
    width = Column(Integer, nullable=True, default=0, doc="宽度（像素）")
    height = Column(Integer, nullable=True, default=0, doc="高度（像素）")
    sha256 = Column(Text, nullable=False, default="",
                    doc="文件哈希，用于去重与完整性校验")
    page_no = Column(Integer, nullable=True, default=1, doc="页码")
    sort_order = Column(Integer, nullable=True, default=0, doc="排序")


class OcrJob(CreatedAtMixin, Base):
    """OCR作业表 — full trace of one recognition run.

    Lane A is local macOS Vision (fast, free, offline, per-line
    confidence); lane B is the DeepSeek vision model refining lane A's
    text into structured fields. Prompt prefixes must be byte-stable so
    they hit the provider's context cache.
    """

    __tablename__ = "ocr_job"

    job_id = Column(Text, primary_key=True, doc="作业编号，ULID")
    attach_id = Column(Text, ForeignKey("attachment.attach_id"),
                       nullable=False, index=True, doc="附件编号")
    record_id = Column(Integer, ForeignKey("info_record.record_id"),
                       nullable=True, doc="病历编号")
    status = Column(UnsignedTinyInt, nullable=False, default=0, index=True,
                    doc="状态，详见附表A14")
    vision_engine = Column(Text, nullable=False, default="ocrmac/Vision",
                           doc="通道A引擎标识")
    vision_text = Column(Text, nullable=False, default="",
                         doc="通道A纯文本结果")
    vision_json = Column(JSON, nullable=True, default=list,
                         doc="通道A结构化结果，含 text、confidence、bbox")
    vision_ms = Column(Integer, nullable=True, default=0, doc="通道A耗时（毫秒）")
    model = Column(Text, nullable=False, default="", doc="通道B模型")
    prompt_version = Column(Text, nullable=False, default="",
                            doc="提示词版本，用于回归对比")
    structured_json = Column(JSON, nullable=True, default=dict,
                             doc="通道B结构化结果")
    degraded_mode = Column(UnsignedTinyInt, nullable=True, default=0,
                           doc="降级模式，详见附表A15")
    tokens_in = Column(Integer, nullable=True, default=0, doc="输入tokens")
    tokens_cached = Column(Integer, nullable=True, default=0,
                           doc="缓存命中tokens")
    tokens_out = Column(Integer, nullable=True, default=0, doc="输出tokens")
    cost_yuan = Column(REAL, nullable=True, default=0, doc="费用（元）")
    duration_ms = Column(Integer, nullable=True, default=0, doc="总耗时（毫秒）")
    error_message = Column(Text, nullable=False, default="", doc="错误信息")


class OcrFieldConfidence(_CA, Base):
    """OCR字段置信度表 — drives the review UI and feeds OCR evaluation.

    Measured on real samples: printed content scores 0.5–1.0 while
    handwriting sits around 0.3, so confidence can route refinement work
    to exactly the fields that need it.
    """

    __tablename__ = "ocr_field_confidence"

    conf_id = Column(Integer, primary_key=True, autoincrement=True,
                     doc="记录编号")
    job_id = Column(Text, ForeignKey("ocr_job.job_id"), nullable=False,
                    index=True, doc="作业编号")
    field_path = Column(Text, nullable=False,
                        doc="字段路径，如 prescription_item[3].dose")
    value = Column(Text, nullable=False, default="", doc="识别得到的值")
    confidence = Column(REAL, nullable=True, default=0,
                        doc="置信度[0,1]；印刷体约0.5~1.0，手写体约0.3")
    source = Column(UnsignedTinyInt, nullable=True, default=0,
                    doc="来源，详见附表A16")
    needs_review = Column(Boolean, nullable=False, default=False,
                          doc="是否待校对；低置信或算术校验失败时置1")
    evidence = Column(Text, nullable=False, default="",
                      doc="依据，如通道A的哪一行与坐标")
    suggestion = Column(Text, nullable=False, default="",
                        doc="归一建议，如“生地”→“生地黄”")
