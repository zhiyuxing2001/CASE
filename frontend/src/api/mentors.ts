import { delJSON, getJSON, postJSON, putJSON } from "@/lib/api"

export interface MentorSummary {
  mentor_id: string
  mentor_name: string
  title: string
  department: string
  expertise: string
  is_primary: boolean
  visit_count: number
  note_count: number
}

export interface MentorSyndrome {
  syndrome: string
  count: number
}

export interface MentorRecordBrief {
  record_id: number
  patient_name: string
  clinic_date: string
  complaint: string
  syndrome: string
}

export interface MentorDetail {
  mentor_id: string
  mentor_name: string
  title: string
  affiliation: string
  department: string
  expertise: string
  clinic_time: string
  clinic_location: string
  bio: string
  is_primary: boolean
  notes: string
  visit_count: number
  note_count: number
  top_syndromes: MentorSyndrome[]
  recent_records: MentorRecordBrief[]
}

export interface MentorUpsert {
  mentor_name: string
  title: string
  affiliation: string
  department: string
  expertise: string
  clinic_time: string
  clinic_location: string
  bio: string
  is_primary: boolean
  notes: string
}

export function fetchMentorList(): Promise<MentorSummary[]> {
  return getJSON<MentorSummary[]>("/api/mentors/list")
}

export function fetchMentorDetail(mentorId: string): Promise<MentorDetail> {
  return getJSON<MentorDetail>(`/api/mentors/${mentorId}`)
}

export function createMentor(payload: MentorUpsert): Promise<MentorDetail> {
  return postJSON<MentorDetail>("/api/mentors", payload)
}

export function updateMentor(mentorId: string, payload: MentorUpsert): Promise<MentorDetail> {
  return putJSON<MentorDetail>(`/api/mentors/${mentorId}`, payload)
}

export function deleteMentor(mentorId: string): Promise<void> {
  return delJSON(`/api/mentors/${mentorId}`)
}
