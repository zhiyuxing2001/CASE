import { delJSON, getJSON, putJSON } from "@/lib/api"

export interface Prompt {
  key: string
  name: string
  description: string
  current: string
  default: string
  is_modified: boolean
}

export function fetchPrompts(): Promise<Prompt[]> {
  return getJSON<Prompt[]>("/api/prompts")
}

export function updatePrompt(key: string, value: string): Promise<Prompt> {
  return putJSON<Prompt>(`/api/prompts/${key}`, { value })
}

export function resetPrompt(key: string): Promise<void> {
  return delJSON(`/api/prompts/${key}`)
}
