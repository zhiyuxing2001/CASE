"""界面模板：字段目录与按模板提取。

字段目录定义了结构化字段路径 → 中文名的映射，供模板编辑与提取使用。
“按模板提取”是无 AI 的本地通道：根据模板的文字结构（标签），从 OCR 行
中按“标签：值”的模式提取字段，作为人工校对的预填。
"""

from __future__ import annotations

#: 病历类结构化字段目录：字段路径 → 中文名
FIELD_CATALOG: dict[str, str] = {
    "narrative.complaint": "主诉",
    "narrative.present_illness": "现病史",
    "narrative.past_history": "既往史",
    "narrative.personal_history": "个人史及婚育史",
    "narrative.allergy_history": "过敏史",
    "narrative.body_of_tongue": "舌质",
    "narrative.fur_of_tongue": "舌苔",
    "narrative.pulse": "脉象",
    "narrative.other_cond": "其他望闻切诊",
    "narrative.physical_exam": "体格检查",
    "narrative.auxiliary_exam": "辅助检查",
    "diagnosis.tcm_disease": "中医病名",
    "diagnosis.syndrome": "证型",
    "diagnosis.wm_diagnosis": "西医诊断",
    "diagnosis.patterns_analysis": "辨证分析",
    "diagnosis.differential_diagnosis": "鉴别诊断",
    "treatment.treatment_principle": "治法",
    "treatment.formula_name": "方剂名",
    "treatment.dose_count": "付数",
    "treatment.decoction": "煎煮法",
    "treatment.usage": "用法",
    "treatment.advice": "医嘱",
    "treatment.western_medicine": "西药",
    "treatment.other_treatment": "其他治疗",
}

#: 处方/医嘱表格列目录：字段路径 → 表头
TABLE_FIELDS: dict[str, str] = {
    "herbs[].herb_name": "药名",
    "herbs[].dose": "剂量",
    "herbs[].unit": "单位",
    "herbs[].frequency": "频次",
    "herbs[].processing": "炮制",
    "herbs[].decoction_note": "煎煮要求",
}


def _extract_one(lines: list[dict], label: str) -> str:
    for line in lines:
        text = (line.get("text") or "").strip()
        idx = text.find(label)
        if idx < 0:
            continue
        rest = text[idx + len(label):].lstrip("：: ").strip()
        if rest:
            return rest
    return ""


def extract_fields(lines: list[dict], field_anchors: list[dict]) -> dict[str, str]:
    """按模板文字结构从 OCR 行提取字段值。

    field_anchors: [{label, field}]，label 为界面上的标签（如“主诉”），
    field 为字段路径（如 narrative.complaint）。返回扁平 {field_path: value}。
    """
    result: dict[str, str] = {}
    for anchor in field_anchors:
        label = (anchor.get("label") or "").strip()
        field = (anchor.get("field") or "").strip()
        if not label or not field or field not in FIELD_CATALOG:
            continue
        value = _extract_one(lines, label)
        if value:
            result[field] = value
    return result
