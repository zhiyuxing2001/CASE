import { useQuery } from "@tanstack/react-query"
import { BookMarked, FolderOpen, Loader2, Send, Sparkles, X } from "lucide-react"
import { useState } from "react"
import ReactMarkdown from "react-markdown"
import { Link } from "react-router-dom"
import remarkGfm from "remark-gfm"

import { askQuestion, type AiSource } from "@/api/ai"
import { fetchCourses } from "@/api/cases"
import { fetchNotes } from "@/api/learning"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

interface Msg {
  role: "user" | "assistant"
  content: string
  sources?: AiSource[]
  degraded?: boolean
}

interface Ref {
  type: "case" | "note"
  id: string
  label: string
}

export function FloatingAssistant() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState("")
  const [busy, setBusy] = useState(false)
  const [ref, setRef] = useState<Ref | null>(null)
  const [refOpen, setRefOpen] = useState(false)
  const [refQuery, setRefQuery] = useState("")

  const { data: cases } = useQuery({
    queryKey: ["ref-cases", refQuery],
    queryFn: () => fetchCourses({ q: refQuery, page_size: 6 }),
    enabled: refOpen,
  })
  const { data: notes } = useQuery({
    queryKey: ["ref-notes", refQuery],
    queryFn: () => fetchNotes({ q: refQuery }),
    enabled: refOpen,
  })

  async function ask() {
    const q = input.trim()
    if (!q || busy) return
    setInput("")
    setMessages((m) => [...m, { role: "user", content: q }])
    setBusy(true)
    try {
      const res = await askQuestion(q, {
        case_id: ref?.type === "case" ? Number(ref.id) : null,
        note_id: ref?.type === "note" ? ref.id : null,
      })
      setMessages((m) => [...m, {
        role: "assistant", content: res.answer,
        sources: res.sources, degraded: res.degraded,
      }])
    } catch {
      setMessages((m) => [...m, { role: "assistant", content: "", degraded: true }])
    } finally {
      setBusy(false)
    }
  }

  function pickReference(r: Ref) {
    setRef(r)
    setRefOpen(false)
  }

  return (
    <>
      {/* 浮窗按钮 */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-5 right-5 z-50 flex items-center gap-2 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 px-4 py-3 text-sm font-medium text-white shadow-lg transition-transform hover:scale-105"
      >
        <Sparkles className="h-4 w-4" />
        AI 助手
      </button>

      {/* 聊天面板 */}
      {open && (
        <div className="fixed bottom-20 right-5 z-50 flex h-[30rem] w-[calc(100vw-2rem)] max-w-[24rem] flex-col overflow-hidden rounded-xl border bg-white shadow-2xl">
          {/* 头部 */}
          <div className="flex items-center justify-between border-b px-3 py-2">
            <div className="flex items-center gap-1.5 text-sm font-medium">
              <Sparkles className="h-4 w-4 text-ai" /> AI 助手
            </div>
            <div className="flex items-center gap-1">
              <div className="relative">
                <Button size="sm" variant="outline" onClick={() => { setRefOpen((v) => !v); setRefQuery("") }}>
                  <BookMarked className="h-4 w-4" /> 引用
                </Button>
                {refOpen && (
                  <div className="absolute right-0 top-9 z-10 w-64 rounded-lg border bg-white p-2 shadow-lg">
                    <Input
                      autoFocus
                      value={refQuery}
                      onChange={(e) => setRefQuery(e.target.value)}
                      placeholder="搜索病案 / 笔记…"
                      className="mb-2 h-8 text-sm"
                    />
                    <div className="max-h-56 overflow-y-auto">
                      {cases && cases.items.length > 0 && (
                        <p className="px-1 py-1 text-xs text-muted-foreground">病案</p>
                      )}
                      {cases?.items.map((c) => (
                        <button
                          key={c.course_id}
                          className="flex w-full items-start gap-1.5 rounded px-1.5 py-1.5 text-left text-sm hover:bg-muted"
                          onClick={() => pickReference({
                            type: "case", id: String(c.first_record_id),
                            label: `${c.patient_name} · ${c.complaint || c.syndrome || ""}`,
                          })}
                        >
                          <FolderOpen className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                          <span className="truncate">{c.patient_name} · {c.complaint || c.syndrome || ""}</span>
                        </button>
                      ))}
                      {notes && notes.items.length > 0 && (
                        <p className="px-1 py-1 text-xs text-muted-foreground">笔记</p>
                      )}
                      {notes?.items.map((n) => (
                        <button
                          key={n.note_id}
                          className="flex w-full items-start gap-1.5 rounded px-1.5 py-1.5 text-left text-sm hover:bg-muted"
                          onClick={() => pickReference({
                            type: "note", id: n.note_id, label: `笔记：${n.title}`,
                          })}
                        >
                          <BookMarked className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                          <span className="truncate">{n.title}</span>
                        </button>
                      ))}
                      {(!cases || cases.items.length === 0) && (!notes || notes.items.length === 0) && (
                        <p className="px-1 py-2 text-sm text-muted-foreground">无匹配结果</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
              <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => setOpen(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* 引用 chip */}
          {ref && (
            <div className="flex items-center gap-2 border-b bg-muted/40 px-3 py-1.5">
              <Badge variant="secondary">{ref.type === "case" ? "病案" : "笔记"}</Badge>
              <span className="truncate text-xs text-muted-foreground">{ref.label}</span>
              <button className="ml-auto text-muted-foreground hover:text-foreground" onClick={() => setRef(null)}>
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          {/* 消息 */}
          <div className="flex-1 space-y-3 overflow-y-auto p-3">
            {messages.length === 0 && (
              <p className="text-xs text-muted-foreground">
                随时提问学习，可「引用」某份病案或笔记作为上下文。
              </p>
            )}
            {messages.map((m, i) => (
              <Bubble key={i} m={m} />
            ))}
            {busy && (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> 思考中…
              </div>
            )}
          </div>

          {/* 输入 */}
          <div className="flex gap-2 border-t p-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void ask()
              }}
              placeholder="提问，如：湿热瘀阻证怎么治？"
            />
            <Button size="sm" onClick={() => void ask()} disabled={busy || !input.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </>
  )
}

function Bubble({ m }: { m: Msg }) {
  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground">{m.content}</div>
      </div>
    )
  }
  return (
    <div className="rounded-lg border bg-muted/40 p-3">
      {m.content ? (
        <div className="prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">AI 未配置（缺少 API Key），无法生成回复。</p>
      )}
      {m.sources && m.sources.length > 0 && (
        <div className="mt-2 space-y-1 border-t pt-2">
          <p className="text-xs text-muted-foreground">相关病案：</p>
          {m.sources.map((s) => (
            <Link
              key={s.record_id}
              to={`/cases/${s.record_id}`}
              className={cn("block truncate text-xs text-primary underline underline-offset-2")}
            >
              {s.patient_name} · {s.clinic_date} · {s.syndrome || s.complaint}
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
