"""字典：中药 · 别名 · 证型 · 方剂 · 通用术语.

These tables exist for two reasons the sibling sleep-disease database did
not need: normalising herb and syndrome names so frequency counts are
correct, and correcting OCR misreads. Herb-name errors are almost all
visually similar characters (黄芩→黄苓, 黄柏→黄相), and the correct form
is nearly always already in the dictionary, so edit distance or pinyin
similarity against ``dict_herb_alias`` can suggest the fix.
"""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, Text

from .base import Base, CreatedAtMixin
from .types import UnsignedTinyInt


class DictHerb(CreatedAtMixin, Base):
    """中药字典表 — processed herbs are first-class entries.

    Salt-prepared corktree bark, vinegar-prepared zedoary and fried
    jujube seed each get their own row, linked back to the base herb via
    ``parent_herb_id``, because that is how prescriptions and HIS order
    lines actually name them.
    """

    __tablename__ = "dict_herb"

    herb_id = Column(Text, primary_key=True, doc="药材编号，ULID")
    herb_name = Column(Text, unique=True, nullable=False,
                       doc="标准药名，如“生地黄”“盐黄柏”")
    pinyin = Column(Text, nullable=False, default="", doc="拼音，便于检索")
    parent_herb_id = Column(Text, ForeignKey("dict_herb.herb_id"),
                            nullable=True,
                            doc="基原药材编号，自引用；炮制品指向其基原")
    is_processed = Column(Boolean, nullable=False, default=False,
                          doc="是否炮制品")
    processing = Column(Text, nullable=False, default="",
                        doc="炮制方法，如盐炙、醋炙、炒、砂烫")
    category = Column(Text, nullable=False, default="", doc="类别")
    nature = Column(Text, nullable=False, default="", doc="四气")
    flavor = Column(Text, nullable=False, default="", doc="五味")
    meridians = Column(Text, nullable=False, default="", doc="归经，逗号分隔")
    functions = Column(Text, nullable=False, default="", doc="功效")
    standard_code = Column(Text, nullable=False, default="",
                           doc="标准编码，仅作建议不强制")
    is_common = Column(Boolean, nullable=False, default=True,
                       doc="是否常用药，影响录入联想排序")
    is_active = Column(Boolean, nullable=False, default=True, doc="是否启用")
    is_auto = Column(Boolean, nullable=False, default=False,
                     doc="是否自动收集（录入病案时自动登记的新药名）")


class DictHerbAlias(CreatedAtMixin, Base):
    """中药别名表 — same-thing-different-name and different-thing-same-name."""

    __tablename__ = "dict_herb_alias"

    alias_id = Column(Integer, primary_key=True, autoincrement=True,
                      doc="别名编号")
    herb_id = Column(Text, ForeignKey("dict_herb.herb_id"), nullable=False,
                     index=True, doc="药材编号")
    alias = Column(Text, nullable=False, index=True, doc="别名")
    alias_type = Column(UnsignedTinyInt, nullable=True, default=0,
                        doc="别名类型，详见附表A4")
    ambiguity_note = Column(Text, nullable=False, default="",
                            doc="同名异物提示，如“川贝”可能指多种贝母")
    source = Column(Text, nullable=False, default="", doc="依据来源")


class DictSyndrome(CreatedAtMixin, Base):
    """证型字典表 — basis for pattern standardisation and frequency counts."""

    __tablename__ = "dict_syndrome"

    syndrome_id = Column(Text, primary_key=True, doc="证型编号，ULID")
    syndrome_name = Column(Text, unique=True, nullable=False,
                           doc="证型名称，如“肝胃不和证”")
    category = Column(Text, nullable=False, default="", doc="辨证体系")
    standard_code = Column(Text, nullable=False, default="", doc="标准编码")
    key_symptoms = Column(Text, nullable=False, default="",
                          doc="主症要点，用于录入联想与学习提示")
    treatment = Column(Text, nullable=False, default="", doc="常用治法")
    common_formula = Column(Text, nullable=False, default="", doc="代表方")
    description = Column(Text, nullable=False, default="", doc="说明")
    is_active = Column(Boolean, nullable=False, default=True, doc="是否启用")
    is_auto = Column(Boolean, nullable=False, default=False,
                     doc="是否自动收集（录入病案时自动登记的新证型）")


class DictFormula(CreatedAtMixin, Base):
    """方剂字典表 — lets a prescription be traced back to its base formula."""

    __tablename__ = "dict_formula"

    formula_id = Column(Text, primary_key=True, doc="方剂编号，ULID")
    formula_name = Column(Text, unique=True, nullable=False, doc="方剂名称")
    alias = Column(Text, nullable=False, default="", doc="别名或简称")
    source = Column(Text, nullable=False, default="", doc="出处")
    category = Column(Text, nullable=False, default="", doc="类别")
    functions = Column(Text, nullable=False, default="", doc="功用")
    indications = Column(Text, nullable=False, default="", doc="主治")
    syndrome_id = Column(Text, ForeignKey("dict_syndrome.syndrome_id"),
                         nullable=True, doc="主治病证编号")
    composition_text = Column(Text, nullable=False, default="", doc="组成原文")
    usage_text = Column(Text, nullable=False, default="", doc="用法原文")
    is_active = Column(Boolean, nullable=False, default=True, doc="是否启用")


class DictTerm(Base):
    """通用术语字典表 — tongue, coating, pulse, processing, decoction.

    ``usage_count`` is maintained by the application and drives the
    ordering of autocomplete suggestions.
    """

    __tablename__ = "dict_term"

    term_id = Column(Integer, primary_key=True, autoincrement=True,
                     doc="术语编号")
    term_type = Column(UnsignedTinyInt, nullable=False, index=True,
                       doc="术语类型，详见附表A5")
    term = Column(Text, nullable=False, doc="术语原文，如“淡红”“薄白”“弦滑”")
    standard_code = Column(Text, nullable=False, default="", doc="标准编码")
    parent_id = Column(Integer, ForeignKey("dict_term.term_id"), nullable=True,
                       doc="上级术语编号，自引用")
    description = Column(Text, nullable=False, default="", doc="说明")
    usage_count = Column(Integer, nullable=False, default=0,
                         doc="使用频次，用于录入联想排序")
    is_active = Column(Boolean, nullable=False, default=True, doc="是否启用")
    is_auto = Column(Boolean, nullable=False, default=False,
                     doc="是否自动收集（录入病案时自动登记的新术语）")


class DictTemplate(CreatedAtMixin, Base):
    """界面模板表 — 特定 HIS 界面的结构，用于提升 OCR 识别准确度。

    常年跟诊同一家医院时，HIS 界面相对固定：病历界面的文字结构（如
    “主诉：”“现病史：”等标签及其顺序）与医嘱界面的表格列。把这些结构
    固化为模板，供通道 B 结构化提示与本地“按模板提取”使用。
    """

    __tablename__ = "dict_template"

    template_id = Column(Text, primary_key=True, doc="模板编号，ULID")
    name = Column(Text, nullable=False, doc="模板名，如“HIS 病历界面”")
    doc_type = Column(UnsignedTinyInt, nullable=False, default=0,
                      doc="单据类型，详见附表A11")
    field_anchors = Column(JSON, nullable=False, default=list,
                           doc="文字结构：[{label, field}]，标签→字段路径")
    table_columns = Column(JSON, nullable=False, default=list,
                           doc="表格列：[{header, field}]，表头→字段路径")
    is_active = Column(Boolean, nullable=False, default=True, doc="是否启用")
