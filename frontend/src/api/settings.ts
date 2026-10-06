import { getJSON, putJSON } from "@/lib/api"

export interface AiSettings {
  configured: boolean
  api_key_masked: string
  base_url: string
  model: string
}

export interface AiSettingsUpdate {
  api_key?: string
  base_url?: string
  model?: string
}

export function fetchAiSettings(): Promise<AiSettings> {
  return getJSON<AiSettings>("/api/settings/ai")
}

export function saveAiSettings(payload: AiSettingsUpdate): Promise<AiSettings> {
  return putJSON<AiSettings>("/api/settings/ai", payload)
}

export async function clearAiKey(): Promise<AiSettings> {
  const res = await fetch("/api/settings/ai", { method: "DELETE" })
  if (!res.ok) {
    throw new Error(`请求失败 (${res.status})`)
  }
  return res.json() as Promise<AiSettings>
}
