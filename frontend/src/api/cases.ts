import { getJSON, postJSON } from "@/lib/api"
import type {
  AuditEntry,
  CourseList,
  FormulaOption,
  HerbOption,
  HerbResolution,
  HerbSuggestion,
  MentorOption,
  PatientOption,
  RecordDetail,
  RecordList,
  SyndromeOption,
  TermOption,
} from "./types"

export interface RecordQuery {
  page?: number
  page_size?: number
  q?: string
  syndrome?: string
  herb?: string
  mentor_id?: string
  patient_id?: string
  date_from?: string
  date_to?: string
  visit_type?: number
}

function qs(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value))
    }
  }
  const s = search.toString()
  return s ? `?${s}` : ""
}

export function fetchRecords(query: RecordQuery = {}): Promise<RecordList> {
  return getJSON<RecordList>(`/api/records${qs(query as Record<string, string | number | undefined>)}`)
}

export function fetchCourses(query: RecordQuery = {}): Promise<CourseList> {
  return getJSON<CourseList>(`/api/courses${qs(query as Record<string, string | number | undefined>)}`)
}

export function fetchRecord(recordId: number): Promise<RecordDetail> {
  return getJSON<RecordDetail>(`/api/records/${recordId}`)
}

export function fetchRecordHistory(recordId: number): Promise<AuditEntry[]> {
  return getJSON<AuditEntry[]>(`/api/records/${recordId}/history`)
}

export function fetchMentors(): Promise<MentorOption[]> {
  return getJSON<MentorOption[]>("/api/mentors")
}

export function fetchSyndromes(q = ""): Promise<SyndromeOption[]> {
  return getJSON<SyndromeOption[]>(`/api/dict/syndromes${qs({ q })}`)
}

export function fetchHerbs(q = ""): Promise<HerbOption[]> {
  return getJSON<HerbOption[]>(`/api/dict/herbs${qs({ q })}`)
}

export function resolveHerb(name: string): Promise<HerbResolution> {
  return getJSON<HerbResolution>(`/api/dict/herbs/resolve${qs({ name })}`)
}

export function suggestHerbs(name: string): Promise<HerbSuggestion[]> {
  return getJSON<HerbSuggestion[]>(`/api/dict/herbs/suggest${qs({ name })}`)
}

export function fetchTerms(term_type: number, q = ""): Promise<TermOption[]> {
  return getJSON<TermOption[]>(`/api/dict/terms${qs({ term_type, q })}`)
}

export function fetchFormulas(q = ""): Promise<FormulaOption[]> {
  return getJSON<FormulaOption[]>(`/api/dict/formulas${qs({ q })}`)
}

// ---------------------------------------------------------------------------
// 写入
// ---------------------------------------------------------------------------

export interface PatientCreatePayload {
  patient_name: string
  gender: boolean
  birthday: string
  nationality?: string
}

export interface HerbPayload {
  herb_name: string
  dose?: number | null
  unit?: string
  processing?: string
  decoction_note?: string
  role?: string
  sequence: number
}

export interface RecordCreatePayload {
  patient_id: string
  clinic_date: string
  visit_type?: number
  age?: number | null
  mentor_id?: string | null
  department?: string
  addr?: string
  parent_record_id?: number | null
  narrative: Record<string, string>
  diagnosis: Record<string, string | null>
  treatment: Record<string, string | number | null>
  herbs: HerbPayload[]
}

export function createPatient(
  payload: PatientCreatePayload,
): Promise<{ patient_id: string }> {
  return postJSON<{ patient_id: string }>("/api/patients", payload)
}

export function createRecord(
  payload: RecordCreatePayload,
): Promise<{ record_id: number }> {
  return postJSON<{ record_id: number }>("/api/records", payload)
}

export function fetchPatients(q = ""): Promise<PatientOption[]> {
  return getJSON<PatientOption[]>(`/api/patients${qs({ q })}`)
}

export function fetchPatient(id: string): Promise<PatientOption> {
  return getJSON<PatientOption>(`/api/patients/${id}`)
}

export function deleteCourses(courseIds: string[]): Promise<{ deleted: number }> {
  return postJSON<{ deleted: number }>("/api/courses/delete", { course_ids: courseIds })
}

export async function exportCourses(courseIds: string[]): Promise<void> {
  const res = await fetch("/api/courses/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ course_ids: courseIds }),
  })
  if (!res.ok) {
    throw new Error(`导出失败 (${res.status})`)
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  const cd = res.headers.get("Content-Disposition") ?? ""
  const match = /filename="?([^"]+)"?/.exec(cd)
  a.download = match?.[1] ?? "case-export.xlsx"
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
