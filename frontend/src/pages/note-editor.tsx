import { useMutation, useQuery } from "@tanstack/react-query"
import { ArrowLeft, Eye, MessageSquare, PencilLine, Save } from "lucide-react"
import { useEffect, useState } from "react"
import ReactMarkdown from "react-markdown"
import { Link, useNavigate, useParams } from "react-router-dom"
import remarkGfm from "remark-gfm"
import { toast } from "sonner"

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

      {/* 编辑器 / 预览 */}
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
        <CardContent>
          {mode === "edit" ? (
            <Textarea
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
