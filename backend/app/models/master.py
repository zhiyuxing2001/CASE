"""主数据：info_patient · info_record · mentor.

Defaults are applied at the application layer rather than as SQL
``DEFAULT`` clauses. The specification phrases them as recording rules
("默认为空字符串", "计算机生成") — the same way the sibling sleep-disease
spec reads — so they belong to the write path, not the schema.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, REAL, Text

from .base import Base, SoftDeleteMixin, TimestampsMixin
from .types import UnsignedTinyInt


class InfoPatient(SoftDeleteMixin, TimestampsMixin, Base):
    """患者基本信息表.

    ``patient_id`` (ULID) is the only join key used across the database.
    ``patient_name`` and ``id_no`` are record-keeping fields that must be
    masked before any request leaves the machine.
    """

    __tablename__ = "info_patient"

    id = Column(Integer, primary_key=True, autoincrement=True, doc="自动编号")
    patient_id = Column(Text, unique=True, nullable=False,
                        doc="患者编号，ULID，全库关联主键")
    patient_name = Column(Text, nullable=False,
                          doc="患者姓名，≤20个Unicode字符")
    name_masked = Column(Boolean, nullable=False, default=False,
                         doc="姓名是否已脱敏，0为未脱敏，1为已脱敏")
    id_no = Column(Text, nullable=False, default="",
                   doc="身份证号，可缺省，独立于任何卡号存储")
    gender = Column(Boolean, nullable=False, default=False,
                    doc="性别，0为女性，1为男性")
    birthday = Column(Date, nullable=False, doc="出生日期")
    nationality = Column(Text, nullable=False, doc="国籍，GB/T 2659-2022")
    ethnicity = Column(UnsignedTinyInt, nullable=True, default=0,
                       doc="民族，详见附表A1")
    birthplace = Column(Text, nullable=False, default="", doc="出生地")
    job = Column(Text, nullable=False, default="", doc="职业")
    tel = Column(Text, nullable=False, default="",
                 doc="联系电话，上云前必须脱敏")
    addr_region = Column(Text, nullable=False, default="",
                         doc="居住地区，仅到区县一级")


class InfoRecord(SoftDeleteMixin, TimestampsMixin, Base):
    """就诊信息记录表 — one row per visit; every clinical table hangs off it.

    ``father_id`` chains a course of treatment with a single column: on a
    first visit it equals this row's own ``record_id``; on a follow-up it
    equals the first visit's ``record_id``. Retrieving a whole course is
    therefore one indexed lookup rather than a recursive query.

    The self-reference is deliberately **not** declared as a database
    foreign key: the value equals the row's own primary key on first
    visit, which no ordinary FK can satisfy at INSERT time. The invariant
    is enforced by the service layer and covered by tests.
    """

    __tablename__ = "info_record"

    record_id = Column(Integer, primary_key=True, autoincrement=True,
                       doc="病历编号")
    course_id = Column(Text, index=True, nullable=False, default="",
                       doc="病案编号（病程系列），ULID；同一患者可有多个病案")
    patient_id = Column(Text, ForeignKey("info_patient.patient_id"),
                        nullable=False, doc="患者编号")
    father_id = Column(Integer, nullable=False, index=True,
                       doc="父节点病历编号：初诊等于自身，复诊等于初诊")
    visit_no = Column(Integer, nullable=False, default=1, doc="第几诊")
    visit_type = Column(UnsignedTinyInt, nullable=True, default=0,
                        doc="就诊类型，详见附表A2")
    clinic_date = Column(Date, nullable=False, doc="就诊日期")
    age = Column(REAL, nullable=False, doc="就诊年龄，范围[0, 200]")
    doctor_name = Column(Text, nullable=False, default="",
                         doc="就诊医师，记录原始姓名写法")
    mentor_id = Column(Text, ForeignKey("mentor.mentor_id"), nullable=True,
                       doc="带教老师编号，用于按老师统计")
    department = Column(Text, nullable=False, default="",
                        doc="就诊科室；注意就诊科室不等于疾病所属专科")
    addr = Column(Text, nullable=False, default="", doc="就诊地点")
    solar_terms = Column(UnsignedTinyInt, nullable=True, default=0,
                         doc="就诊节气，详见附表A3")
    source_document_id = Column(Text,
                                ForeignKey("source_document.doc_id"),
                                nullable=True, doc="来源单据编号")


class Mentor(SoftDeleteMixin, TimestampsMixin, Base):
    """带教老师表 —核心主数据，用于按老师聚合病案与用药规律."""

    __tablename__ = "mentor"

    mentor_id = Column(Text, primary_key=True, doc="老师编号，ULID")
    mentor_name = Column(Text, nullable=False, doc="老师姓名")
    title = Column(Text, nullable=False, default="", doc="职称")
    affiliation = Column(Text, nullable=False, default="", doc="所属机构")
    department = Column(Text, nullable=False, default="", doc="所属科室")
    expertise = Column(Text, nullable=False, default="", doc="擅长领域")
    clinic_time = Column(Text, nullable=False, default="", doc="出诊时间，如“周二、四上午”")
    clinic_location = Column(Text, nullable=False, default="",
                             doc="出诊地点，如“门诊楼3层303室”")
    bio = Column(Text, nullable=False, default="", doc="导师简介")
    is_primary = Column(Boolean, nullable=False, default=False,
                        doc="是否主带教")
    notes = Column(Text, nullable=False, default="", doc="备注")
