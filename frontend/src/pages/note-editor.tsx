import { useMutation, useQuery } from "@tanstack/react-query"
import { ArrowLeft, Eye, MessageSquare, PencilLine, Save, Send, Sparkles } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import ReactMarkdown from "react-markdown"
import { Link, useNavigate, useParams } from "react-router-dom"
import remarkGfm from "remark-gfm"
import { toast } from "sonner"

import { askQuestion, draftNote, type AiSource } from "@/api/ai"
import { fetchMentors, fetchRecords } from "@/api/cases"
import {
  addComment,
  createNote,
  fetchNote,
  updateNote,
  NOTE_STATUS,
  NOTE_TYPES,
} from "@/api/learning"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { FreeTextCombobox, type ComboboxOption } from "@/components/free-text-combobox"

export function NoteEditor() {
  const { noteId } = useParams<{ noteId: string }>()
  const isEdit = Boolean(noteId)
  const navigate = useNavigate()

  const [title, setTitle] = useState("")
  const [noteType, setNoteType] = useState("1")
  const [content, setContent] = useState("")
  const [status, setStatus] = useState("0")
  const [mentorId, setMentorId] = useState("")
  const [recordId, setRecordId] = useState<number | null>(null)
  const [recordLabel, setRecordLabel] = useState("")
  const [mode, setMode] = useState<"edit" | "preview">("edit")
  const [comment, setComment] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const { data: mentors = [] } = useQuery({ queryKey: ["mentors"], queryFn: fetchMentors })
  const { data: detail } = useQuery({
    queryKey: ["note", noteId],
    queryFn: () => fetchNote(noteId!),
    enabled: isEdit,
  })

  // 载入已有笔记
  useEffect(() => {
    if (detail) {
      setTitle(detail.title)
      setNoteType(String(detail.note_type))
      setContent(detail.content_md)
      setStatus(String(detail.status))
      setMentorId(detail.mentor_id ?? "")
      setRecordId(detail.record_id)
      setRecordLabel(detail.record ? `${detail.record.patient_name} · ${detail.record.clinic_date}` : "")
    }
  }, [detail])

  const save = useMutation({
    mutationFn: async () => {
      if (!title.trim()) throw new Error("请填写标题")
      const payload = {
        note_type: Number(noteType),
        title: title.trim(),
        content_md: content,
        record_id: recordId,
        mentor_id: mentorId || null,
      }
      if (isEdit) {
        return updateNote(noteId!, { ...payload, status: Number(status) })
      }
      return createNote(payload)
    },
    onSuccess: (note) => {
      toast.success("已保存")
      if (!isEdit) navigate(`/learning/${note.note_id}`)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const submitComment = useMutation({
    mutationFn: () => addComment(noteId!, { content: comment, mentor_id: mentorId || null }),
    onSuccess: () => {
      setComment("")
      toast.success("点评已提交")
      window.location.reload()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const recordLoad = (q: string) =>
    fetchRecords({ q, page_size: 10 }).then((r) =>
      r.items.map((i) => ({
        value: String(i.record_id),
        label: `${i.patient_name} · ${i.clinic_date}`,
        hint: i.complaint,
      })),
    )

  function onRecordPick(_v: string, o?: ComboboxOption) {
    if (o) {
      setRecordId(Number(o.value))
      setRecordLabel(o.label)
    }
  }

  // 把 AI 回复插入正文：优先插入到光标处，否则追加
  function insertText(text: string) {
    const el = textareaRef.current
    if (el) {
      const start = el.selectionStart ?? content.length
      const end = el.selectionEnd ?? content.length
      const next = content.slice(0, start) + text + content.slice(end)
      setContent(next)
      requestAnimationFrame(() => {
        el.focus()
        const pos = start + text.length
        el.selectionStart = el.selectionEnd = pos
      })
    } else {
      setContent((c) => (c ? `${c}\n\n${text}` : text))
    }
  }

  const wordCount = content.replace(/\s/g, "").length

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-8">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/learning"><ArrowLeft className="h-4 w-4" /> 返回</Link>
        </Button>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">{wordCount} 字</span>
          <Button onClick={() => save.mutate()} disabled={save.isPending}>
            <Save className="h-4 w-4" /> 保存
          </Button>
        </div>
      </div>

      {/* 元信息 */}
      <Card>
        <CardContent className="space-y-4 p-4">
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="笔记标题"
            className="text-lg font-medium"
          />
          <div className="grid gap-4 sm:grid-cols-4">
            <div className="space-y-1.5">
              <Label>类型</Label>
              <Select value={noteType} onValueChange={setNoteType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(NOTE_TYPES).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>带教老师</Label>
              <Select value={mentorId} onValueChange={setMentorId}>
                <SelectTrigger><SelectValue placeholder="选择老师" /></SelectTrigger>
                <SelectContent>
                  {mentors.map((m) => (
                    <SelectItem key={m.mentor_id} value={m.mentor_id}>{m.mentor_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>关联病案</Label>
              <FreeTextCombobox
                value={recordLabel}
                onValueChange={onRecordPick}
                load={recordLoad}
                placeholder="搜索患者/主诉…"
              />
            </div>
            {isEdit && (
              <div className="space-y-1.5">
                <Label>状态</Label>
                <Select value={status} onValueChange={setStatus}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(NOTE_STATUS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 编辑器 + AI 助手 */}
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base">正文（Markdown）</CardTitle>
          <div className="flex gap-1">
            <Button variant={mode === "edit" ? "secondary" : "ghost"} size="sm"
              onClick={() => setMode("edit")}>
              <PencilLine className="h-4 w-4" /> 编辑
            </Button>
            <Button variant={mode === "preview" ? "secondary" : "ghost"} size="sm"
              onClick={() => setMode("preview")}>
              <Eye className="h-4 w-4" /> 预览
            </Button>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
          {mode === "edit" ? (
            <Textarea
              ref={textareaRef}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={18}
              placeholder="支持 Markdown：**加粗**、- 列表、# 标题、> 引用…"
              className="font-mono text-sm leading-relaxed"
            />
          ) : (
            <div className="prose-sm min-h-[18rem] max-w-none">
              {content.trim() ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
              ) : (
                <p className="text-sm text-muted-foreground">暂无内容</p>
              )}
            </div>
          )}
          <AiChatPanel onInsert={insertText} topic={title} recordId={recordId} />
        </CardContent>
      </Card>

      {/* 导师点评（仅已有笔记） */}
      {isEdit && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <MessageSquare className="h-4 w-4" /> 导师点评
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {detail?.comments && detail.comments.length > 0 ? (
              detail.comments.map((c) => (
                <div key={c.comment_id} className="rounded-lg border p-3">
                  <div className="mb-1 flex items-center gap-2 text-sm">
                    <span className="font-medium">{c.mentor_name || "导师"}</span>
                    <span className="text-xs text-muted-foreground">{c.commented_at}</span>
                    {c.is_ai_generated && <Badge variant="ai">AI</Badge>}
                  </div>
                  <p className="text-sm whitespace-pre-wrap">{c.content}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">暂无点评。</p>
            )}
            <div className="flex gap-2">
              <Input
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="记录导师的点评意见…"
              />
              <Button
                variant="outline"
                disabled={!comment.trim() || submitComment.isPending}
                onClick={() => submitComment.mutate()}
              >
                提交
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

interface ChatMsg {
  role: "user" | "assistant"
  content: string
  sources?: AiSource[]
  degraded?: boolean
}

function AiChatPanel({
  onInsert,
  topic,
  recordId,
}: {
  onInsert: (text: string) => void
  topic: string
  recordId: number | null
}) {
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [input, setInput] = useState("")
  const [busy, setBusy] = useState(false)

  async function ask() {
    const q = input.trim()
    if (!q || busy) return
    setInput("")
    setMessages((m) => [...m, { role: "user", content: q }])
    setBusy(true)
    try {
      const res = await askQuestion(q)
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

  async function draft() {
    if (busy) return
    setBusy(true)
    try {
      const res = await draftNote(topic || "学习心得", recordId)
      setMessages((m) => [...m, { role: "assistant", content: res.text, degraded: res.degraded }])
    } catch {
      setMessages((m) => [...m, { role: "assistant", content: "", degraded: true }])
    } finally {
      setBusy(false)
    }
  }

  function insertSelected() {
    const sel = window.getSelection()?.toString()
    if (sel && sel.trim()) onInsert(sel)
    else toast.info("请先在 AI 回复中选中要插入的文字")
  }

  return (
    <div className="flex h-[26rem] flex-col rounded-lg border">
      <div className="flex items-center justify-between border-b px-3 py-2">
        <span className="flex items-center gap-1.5 text-sm font-medium">
          <Sparkles className="h-4 w-4 text-ai" /> AI 助手
        </span>
        <Button size="sm" variant="outline" onClick={draft} disabled={busy}>
          撰写草稿
        </Button>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto p-3">
        {messages.length === 0 && (
          <p className="text-xs text-muted-foreground">
            向 AI 提问查阅资料，或点「撰写草稿」生成一段初稿，再把回复插入正文。
          </p>
        )}
        {messages.map((m, i) => (
          <ChatBubble key={i} m={m} onInsert={onInsert} onInsertSelected={insertSelected} />
        ))}
        {busy && <p className="text-xs text-muted-foreground">思考中…</p>}
      </div>
      <div className="flex gap-2 border-t p-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void ask()
          }}
          placeholder="提问，如：湿热瘀阻证常用哪些药？"
        />
        <Button size="sm" onClick={() => void ask()} disabled={busy || !input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

function ChatBubble({
  m,
  onInsert,
  onInsertSelected,
}: {
  m: ChatMsg
  onInsert: (text: string) => void
  onInsertSelected: () => void
}) {
  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground">
          {m.content}
        </div>
      </div>
    )
  }
  if (!m.content) {
    return (
      <div className="rounded-lg border bg-muted/40 p-3 text-sm">
        <p className="text-muted-foreground">AI 未配置（缺少 API Key），无法生成回复。</p>
        {m.sources && m.sources.length > 0 && <SourcesList sources={m.sources} />}
      </div>
    )
  }
  return (
    <div className="rounded-lg border bg-muted/40 p-3">
      <div className="prose-sm max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
      </div>
      <div className="mt-2 flex gap-2">
        <Button size="sm" variant="outline" onClick={() => onInsert(m.content)}>
          插入全文
        </Button>
        <Button size="sm" variant="outline" onClick={onInsertSelected}>
          插入所选
        </Button>
      </div>
      {m.sources && m.sources.length > 0 && <SourcesList sources={m.sources} />}
    </div>
  )
}

function SourcesList({ sources }: { sources: AiSource[] }) {
  return (
    <div className="mt-2 space-y-1">
      <p className="text-xs text-muted-foreground">相关病案：</p>
      {sources.map((s) => (
        <Link
          key={s.record_id}
          to={`/cases/${s.record_id}`}
          className="block truncate text-xs text-primary underline underline-offset-2"
        >
          {s.patient_name} · {s.clinic_date} · {s.syndrome || s.complaint}
        </Link>
      ))}
    </div>
  )
}
