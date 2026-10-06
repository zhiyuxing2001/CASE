import { getJSON } from "@/lib/api"

export interface AnalyticsOverview {
  total_courses: number
  total_visits: number
  total_patients: number
  total_herbs: number
  distinct_herbs: number
  distinct_syndromes: number
}

export interface FreqItem {
  label: string
  count: number
}

export interface HerbFreq {
  label: string
  count: number
  avg_dose: number | null
}

export interface TongueDist {
  body: FreqItem[]
  coating: FreqItem[]
  pulse: FreqItem[]
}

export function fetchOverview(): Promise<AnalyticsOverview> {
  return getJSON<AnalyticsOverview>("/api/analytics/overview")
}
export function fetchSyndromes(): Promise<FreqItem[]> {
  return getJSON<FreqItem[]>("/api/analytics/syndromes")
}
export function fetchHerbs(): Promise<HerbFreq[]> {
  return getJSON<HerbFreq[]>("/api/analytics/herbs")
}
export function fetchTongue(): Promise<TongueDist> {
  return getJSON<TongueDist>("/api/analytics/tongue")
}
export function fetchDiseases(): Promise<FreqItem[]> {
  return getJSON<FreqItem[]>("/api/analytics/diseases")
}
