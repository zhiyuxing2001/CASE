"""All CASE ORM models.

Importing this package registers every table on ``Base.metadata``, which
is what Alembic autogenerate and the DDL drift check rely on.
"""

from .base import Base, CreatedAtMixin, SoftDeleteMixin, TimestampsMixin
from .clinical import (CaseNarrative, Diagnosis, ExamReport, LabResult,
                       PrescriptionItem, Treatment)
from .dictionary import (DictFormula, DictHerb, DictHerbAlias, DictSyndrome,
                         DictTemplate, DictTerm)
from .learning import LearningNote, MentorComment, NoteRecordLink
from .master import InfoPatient, InfoRecord, Mentor
from .provenance import (Attachment, OcrFieldConfidence, OcrJob,
                         SourceDocument)
from .system import AppSetting, AuditLog
from .types import UnsignedTinyInt

__all__ = [
    "Base",
    "TimestampsMixin",
    "CreatedAtMixin",
    "SoftDeleteMixin",
    "UnsignedTinyInt",
    # 主数据
    "InfoPatient",
    "InfoRecord",
    "Mentor",
    # 病案主体与诊疗
    "CaseNarrative",
    "Diagnosis",
    "Treatment",
    "PrescriptionItem",
    "LabResult",
    "ExamReport",
    # 字典
    "DictHerb",
    "DictHerbAlias",
    "DictSyndrome",
    "DictFormula",
    "DictTerm",
    "DictTemplate",
    # 跟师学习
    "LearningNote",
    "MentorComment",
    "NoteRecordLink",
    # 来源与溯源
    "SourceDocument",
    "Attachment",
    "OcrJob",
    "OcrFieldConfidence",
    # 系统
    "AuditLog",
    "AppSetting",
]
