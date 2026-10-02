import { delJSON, getJSON, postJSON, putJSON } from "@/lib/api"

// ---------------------------------------------------------------------------
// 字典维护
// ---------------------------------------------------------------------------

export interface HerbUpsertPayload {
  herb_name: string
  pinyin?: string
  category?: string
  nature?: string
  flavor?: string
  meridians?: string
  functions?: string
  is_processed?: boolean
  processing?: string
  is_common?: boolean
}

export interface SyndromeUpsertPayload {
  syndrome_name: string
  category?: string
  key_symptoms?: string
  treatment?: string
  common_formula?: string
}

export interface TermUpsertPayload {
  term: string
  term_type: number
  description?: string
}

export interface FormulaUpsertPayload {
  formula_name: string
  source?: string
  category?: string
  functions?: string
  indications?: string
  composition_text?: string
  usage_text?: string
}

export function createHerb(p: HerbUpsertPayload) {
  return postJSON<unknown>("/api/dict/herbs", p)
}
export function updateHerb(id: string, p: HerbUpsertPayload) {
  return putJSON<unknown>(`/api/dict/herbs/${id}`, p)
}
export function deleteHerb(id: string) {
  return delJSON(`/api/dict/herbs/${id}`)
}
export function fetchHerbDetail(id: string): Promise<HerbUpsertPayload> {
  return getJSON<HerbUpsertPayload>(`/api/dict/herbs/${id}`)
}
export function fetchSyndromeDetail(id: string): Promise<SyndromeUpsertPayload> {
  return getJSON<SyndromeUpsertPayload>(`/api/dict/syndromes/${id}`)
}
export function fetchTermDetail(id: number): Promise<Record<string, unknown>> {
  return getJSON<Record<string, unknown>>(`/api/dict/terms/${id}`)
}
export function fetchFormulaDetail(id: string): Promise<FormulaUpsertPayload> {
  return getJSON<FormulaUpsertPayload>(`/api/dict/formulas/${id}`)
}

export function createSyndrome(p: SyndromeUpsertPayload) {
  return postJSON<unknown>("/api/dict/syndromes", p)
}
export function updateSyndrome(id: string, p: SyndromeUpsertPayload) {
  return putJSON<unknown>(`/api/dict/syndromes/${id}`, p)
}
export function deleteSyndrome(id: string) {
  return delJSON(`/api/dict/syndromes/${id}`)
}

export function createTerm(p: TermUpsertPayload) {
  return postJSON<unknown>("/api/dict/terms", p)
}
export function updateTerm(id: number, p: TermUpsertPayload) {
  return putJSON<unknown>(`/api/dict/terms/${id}`, p)
}
export function deleteTerm(id: number) {
  return delJSON(`/api/dict/terms/${id}`)
}

export function createFormula(p: FormulaUpsertPayload) {
  return postJSON<unknown>("/api/dict/formulas", p)
}
export function updateFormula(id: string, p: FormulaUpsertPayload) {
  return putJSON<unknown>(`/api/dict/formulas/${id}`, p)
}
export function deleteFormula(id: string) {
  return delJSON(`/api/dict/formulas/${id}`)
}

// ---------------------------------------------------------------------------
// 数据管理
// ---------------------------------------------------------------------------

export interface TableStat {
  table: string
  rows: number
}
export interface AdminStats {
  tables: TableStat[]
  database_size: number
}
export interface BackupInfo {
  name: string
  size: number
  created_at: string
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
export interface AuditPage {
  total: number
  items: AuditEntry[]
}
export interface CheckResult {
  ok: boolean
  foreign_key_violations: number
  tables: TableStat[]
  messages: string[]
}

export function fetchStats(): Promise<AdminStats> {
  return getJSON<AdminStats>("/api/admin/stats")
}
export function fetchAudit(page = 1, pageSize = 50, table = ""): Promise<AuditPage> {
  const s = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (table) s.set("table_name", table)
  return getJSON<AuditPage>(`/api/admin/audit?${s.toString()}`)
}
export function createBackup(): Promise<{ path: string; size: number }> {
  return postJSON<{ path: string; size: number }>("/api/admin/backup", {})
}
export function fetchBackups(): Promise<BackupInfo[]> {
  return getJSON<BackupInfo[]>("/api/admin/backups")
}
export function runCheck(): Promise<CheckResult> {
  return getJSON<CheckResult>("/api/admin/check")
}
