import { getJSON } from "@/lib/api"
import type {
  HerbOption,
  HerbResolution,
  HerbSuggestion,
  MentorOption,
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
