import { getJSON, postJSON } from "@/lib/api"

export interface QualityReport {
  width: number
  height: number
  sharpness: number
  blurry: boolean
}

export interface AttachmentCreated {
  attach_id: string
  quality: QualityReport
}

export interface OcrLine {
  text: string
  confidence: number
  bbox: number[] // 归一化 [x, y, w, h]，原点左上角
}

export interface OcrJobOut {
  job_id: string
  attach_id: string
  status: number
  degraded_mode: number
  vision_text: string
  lines: OcrLine[]
}

export interface OcrCommitPayload {
  patient_name: string
  patient_id?: string | null
  gender: boolean
  birthday: string
  clinic_date: string
  complaint: string
  present_illness: string
}

export async function uploadImage(file: File): Promise<AttachmentCreated> {
  const form = new FormData()
  form.append("file", file)
  const res = await fetch("/api/attachments", { method: "POST", body: form })
  if (!res.ok) {
    throw new Error(`上传失败 (${res.status})`)
  }
  return res.json() as Promise<AttachmentCreated>
}

export function createOcrJob(attach_id: string): Promise<OcrJobOut> {
  return postJSON<OcrJobOut>("/api/ocr/jobs", { attach_id, doc_type: 0 })
}

export function fetchOcrJob(jobId: string): Promise<OcrJobOut> {
  return getJSON<OcrJobOut>(`/api/ocr/jobs/${jobId}`)
}

export function commitOcrJob(
  jobId: string,
  payload: OcrCommitPayload,
): Promise<{ record_id: number }> {
  return postJSON<{ record_id: number }>(`/api/ocr/jobs/${jobId}/commit`, payload)
}
