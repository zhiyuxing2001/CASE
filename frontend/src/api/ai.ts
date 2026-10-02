import { getJSON, postJSON } from "@/lib/api"

export interface AiStatus {
  configured: boolean
  provider: string
  model: string
}

export interface AiSource {
  record_id: number
  patient_name: string
  clinic_date: string
  complaint: string
  syndrome: string
  snippet: string
}

export interface AiChatResponse {
  answer: string
  sources: AiSource[]
  degraded: boolean
  ai_configured: boolean
}

export interface AiDraftResponse {
  text: string
  degraded: boolean
  ai_configured: boolean
}

export function fetchAiStatus(): Promise<AiStatus> {
  return getJSON<AiStatus>("/api/ai/status")
}

export function askQuestion(question: string): Promise<AiChatResponse> {
  return postJSON<AiChatResponse>("/api/ai/chat", { question })
}

export function draftNote(topic: string, caseId?: number | null): Promise<AiDraftResponse> {
  return postJSON<AiDraftResponse>("/api/ai/draft", { topic, case_id: caseId ?? null })
}

export function polishText(text: string): Promise<AiDraftResponse> {
  return postJSON<AiDraftResponse>("/api/ai/polish", { text })
}
