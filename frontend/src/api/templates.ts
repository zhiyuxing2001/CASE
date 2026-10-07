import { delJSON, getJSON, postJSON, putJSON } from "@/lib/api"

export interface TemplateAnchor {
  label: string
  field: string
}

export interface Template {
  template_id: string
  name: string
  doc_type: number
  field_anchors: TemplateAnchor[]
  table_columns: TemplateAnchor[]
}

export const DOC_TYPES: Record<number, string> = {
  0: "病历",
  1: "医嘱/处方",
  2: "其他",
}

/** 病历类字段目录：字段路径 → 中文名（供模板编辑器选择） */
export const FIELD_CATALOG: { field: string; label: string }[] = [
  { field: "narrative.complaint", label: "主诉" },
  { field: "narrative.present_illness", label: "现病史" },
  { field: "narrative.past_history", label: "既往史" },
  { field: "narrative.personal_history", label: "个人史及婚育史" },
  { field: "narrative.allergy_history", label: "过敏史" },
  { field: "narrative.body_of_tongue", label: "舌质" },
  { field: "narrative.fur_of_tongue", label: "舌苔" },
  { field: "narrative.pulse", label: "脉象" },
  { field: "narrative.other_cond", label: "其他望闻切诊" },
  { field: "narrative.physical_exam", label: "体格检查" },
  { field: "narrative.auxiliary_exam", label: "辅助检查" },
  { field: "diagnosis.tcm_disease", label: "中医病名" },
  { field: "diagnosis.syndrome", label: "证型" },
  { field: "diagnosis.wm_diagnosis", label: "西医诊断" },
  { field: "diagnosis.patterns_analysis", label: "辨证分析" },
  { field: "diagnosis.differential_diagnosis", label: "鉴别诊断" },
  { field: "treatment.treatment_principle", label: "治法" },
  { field: "treatment.formula_name", label: "方剂名" },
  { field: "treatment.dose_count", label: "付数" },
  { field: "treatment.decoction", label: "煎煮法" },
  { field: "treatment.usage", label: "用法" },
  { field: "treatment.advice", label: "医嘱" },
  { field: "treatment.western_medicine", label: "西药" },
  { field: "treatment.other_treatment", label: "其他治疗" },
]

/** 处方/医嘱表格列目录：字段路径 → 表头 */
export const TABLE_FIELDS: { field: string; label: string }[] = [
  { field: "herbs[].herb_name", label: "药名" },
  { field: "herbs[].dose", label: "剂量" },
  { field: "herbs[].unit", label: "单位" },
  { field: "herbs[].frequency", label: "频次" },
  { field: "herbs[].processing", label: "炮制" },
  { field: "herbs[].decoction_note", label: "煎煮要求" },
]

export function fetchTemplates(): Promise<Template[]> {
  return getJSON<Template[]>("/api/templates")
}

export function fetchTemplateDetail(templateId: string): Promise<Template> {
  return getJSON<Template>(`/api/templates/${templateId}`)
}

export function createTemplate(payload: Omit<Template, "template_id">): Promise<Template> {
  return postJSON<Template>("/api/templates", payload)
}

export function updateTemplate(templateId: string, payload: Omit<Template, "template_id">): Promise<Template> {
  return putJSON<Template>(`/api/templates/${templateId}`, payload)
}

export function deleteTemplate(templateId: string): Promise<void> {
  return delJSON(`/api/templates/${templateId}`)
}
