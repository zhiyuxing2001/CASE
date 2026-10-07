import { getJSON, postJSON, putJSON } from "@/lib/api"

export const NOTE_TYPES: Record<number, string> = {
  0: "跟诊日志",
  1: "学习心得",
  2: "读书笔记",
  3: "病例讨论",
  4: "阶段总结",
}

export const NOTE_STATUS: Record<number, string> = {
  0: "草稿",
  1: "已发布",
  2: "已归档",
}

export interface NoteSummary {
  note_id: string
  note_type: number
  title: string
  status: number
  record_id: number | null
  mentor_name: string
  word_count: number
  is_ai_assisted: boolean
  updated_at: string
}

export interface NoteList {
  total: number
  items: NoteSummary[]
}

export interface CommentOut {
  comment_id: number
  mentor_id: string | null
  mentor_name: string
  content: string
  comment_type: number
  is_ai_generated: boolean
  commented_at: string
}

export interface NoteRecord {
  record_id: number
  clinic_date: string
  patient_name: string
  complaint: string
  syndrome: string
}

export interface NoteDetail {
  note_id: string
  note_type: number
  title: string
  content_md: string
  status: number
  record_id: number | null
  mentor_id: string | null
  mentor_name: string
  word_count: number
  is_ai_assisted: boolean
  created_at: string
  updated_at: string
  comments: CommentOut[]
  record: NoteRecord | null
}

export interface ProgressOut {
  note_counts: Record<string, number>
  total_records: number
  total_patients: number
  total_syndromes: number
  top_syndromes: { syndrome: string; count: number }[]
}

export interface NoteCreatePayload {
  note_type: number
  title: string
  content_md: string
  record_id?: number | null
  mentor_id?: string | null
}

export interface NoteUpdatePayload {
  note_type?: number
  title?: string
  content_md?: string
  status?: number
  record_id?: number | null
  mentor_id?: string | null
}

export function fetchNotes(params: {
  note_type?: number
  status?: number
  q?: string
} = {}): Promise<NoteList> {
  const search = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") search.set(k, String(v))
  }
  const s = search.toString()
  return getJSON<NoteList>(`/api/learning/notes${s ? `?${s}` : ""}`)
}

export function fetchNote(id: string): Promise<NoteDetail> {
  return getJSON<NoteDetail>(`/api/learning/notes/${id}`)
}

export function createNote(payload: NoteCreatePayload): Promise<NoteDetail> {
  return postJSON<NoteDetail>("/api/learning/notes", payload)
}

export function updateNote(id: string, payload: NoteUpdatePayload): Promise<NoteDetail> {
  return putJSON<NoteDetail>(`/api/learning/notes/${id}`, payload)
}

export function addComment(
  id: string,
  payload: { content: string; mentor_id?: string | null; is_ai_generated?: boolean },
): Promise<CommentOut> {
  return postJSON<CommentOut>(`/api/learning/notes/${id}/comments`, payload)
}

export function fetchProgress(): Promise<ProgressOut> {
  return getJSON<ProgressOut>("/api/learning/progress")
}

export function deleteNotes(noteIds: string[]): Promise<{ deleted: number }> {
  return postJSON<{ deleted: number }>("/api/learning/notes/delete", { note_ids: noteIds })
}

export async function exportNotes(noteIds: string[]): Promise<void> {
  const res = await fetch("/api/learning/notes/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ note_ids: noteIds }),
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
  a.download = match?.[1] ?? "notes.docx"
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
