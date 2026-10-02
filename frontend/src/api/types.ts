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
  term: string
  description: string
}

export interface FormulaOption {
  formula_id: string
  formula_name: string
  source: string
}
