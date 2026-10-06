// 与后端 schemas.py 对应的 TypeScript 类型。

export interface Health {
  status: string
  database: string
  ai_configured: boolean
  version: string
}

export interface RecordSummary {
  record_id: number
  clinic_date: string
  visit_no: number
  visit_type: number
  patient_id: string
  patient_name: string
  complaint: string
  syndrome: string
  tcm_disease: string
  herb_count: number
  mentor_name: string
  needs_review: boolean
}

export interface RecordList {
  total: number
  page: number
  page_size: number
  items: RecordSummary[]
}

export interface CourseSummary {
  course_id: string
  first_record_id: number
  patient_id: string
  patient_name: string
  first_date: string
  last_date: string
  visit_count: number
  complaint: string
  syndrome: string
  tcm_disease: string
  mentor_name: string
  needs_review: boolean
}

export interface CourseList {
  total: number
  page: number
  page_size: number
  items: CourseSummary[]
}

export interface MentorOption {
  mentor_id: string
  mentor_name: string
  title: string
}

export interface PatientOption {
  patient_id: string
  patient_name: string
  gender: boolean
}

export interface SyndromeOption {
  syndrome_id: string
  syndrome_name: string
  category: string
}

export interface HerbOption {
  herb_id: string
  herb_name: string
  pinyin: string
  category: string
  is_processed: boolean
}

export interface HerbResolution {
  entered: string
  normalised: string
  herb_id: string | null
  matched_by: string
  is_ocr_misread: boolean
}

export interface HerbSuggestion {
  herb_id: string
  herb_name: string
  similarity: number
}

export interface TermOption {
  term_id: number
  term_type: number
  term: string
  description: string
}

export interface FormulaOption {
  formula_id: string
  formula_name: string
  source: string
}

export interface HerbItem {
  sequence: number
  herb_name: string
  herb_name_norm: string
  herb_id: string | null
  dose: number | null
  unit: string
  processing: string
  decoction_note: string
  role: string
  needs_review: boolean
}

export interface CourseVisit {
  record_id: number
  clinic_date: string
  visit_no: number
  visit_type: number
}

export interface RecordDetail {
  record: Record<string, unknown>
  patient: { patient_id: string; patient_name: string; gender: boolean; age: number | null }
  narrative: Record<string, string>
  first_narrative: Record<string, string>
  diagnosis: Record<string, string | null>
  treatment: Record<string, string | number | null>
  herbs: HerbItem[]
  course: CourseVisit[]
}

export interface AuditEntry {
  table_name: string
  action: number
  field_name: string
  old_value: string
  new_value: string
  changed_at: string
  note: string
}
