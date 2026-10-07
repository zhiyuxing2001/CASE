import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Download, Plus, Trash2 } from "lucide-react"
import { useState } from "react"
import { Link } from "react-router-dom"
import { toast } from "sonner"

import {
  deleteNotes,
  exportNotes,
  fetchNotes,
  NOTE_STATUS,
  NOTE_TYPES,
} from "@/api/learning"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

const STATUS_VARIANT: Record<number, "default" | "secondary" | "outline"> = {
  0: "outline",
  1: "default",
  2: "secondary",
}

export function Learning() {
  const [noteType, setNoteType] = useState<number | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const queryClient = useQueryClient()

  const { data: notes, isLoading } = useQuery({
    queryKey: ["learning-notes", noteType],
    queryFn: () => fetchNotes(noteType != null ? { note_type: noteType } : {}),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteNotes([...selected]),
    onSuccess: (res) => {
      toast.success(`已删除 ${res.deleted} 篇心得`)
      setSelected(new Set())
      void queryClient.invalidateQueries({ queryKey: ["learning-notes"] })
      void queryClient.invalidateQueries({ queryKey: ["learning-progress"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const exportMutation = useMutation({
    mutationFn: () => exportNotes([...selected]),
    onSuccess: () => toast.success("已导出 Word 汇编"),
    onError: (e: Error) => toast.error(e.message),
  })

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleAll() {
    if (!notes) return
    const allIds = notes.items.map((n) => n.note_id)
    const allSelected = allIds.every((id) => selected.has(id))
    setSelected(allSelected ? new Set() : new Set(allIds))
  }

  function handleDelete() {
    if (window.confirm(`确定删除选中的 ${selected.size} 篇心得？`)) {
      deleteMutation.mutate()
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">跟师学习</h2>
          <p className="text-sm text-muted-foreground">心得、跟诊日志与导师点评。</p>
        </div>
        <Button asChild>
          <Link to="/learning/new"><Plus className="h-4 w-4" /> 新建笔记</Link>
        </Button>
      </div>

      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <FilterChip active={noteType === null} onClick={() => setNoteType(null)}>全部</FilterChip>
          {Object.entries(NOTE_TYPES).map(([key, label]) => (
            <FilterChip
              key={key}
              active={noteType === Number(key)}
              onClick={() => setNoteType(Number(key))}
            >
              {label}
            </FilterChip>
          ))}
          {notes && notes.items.length > 0 && (
            <label className="ml-auto flex cursor-pointer items-center gap-1.5 text-sm text-muted-foreground">
              <input
                type="checkbox"
                className="h-4 w-4 accent-primary"
                checked={notes.items.every((n) => selected.has(n.note_id))}
                onChange={toggleAll}
              />
              全选
            </label>
          )}
        </div>

        {/* 批量操作栏 */}
        {selected.size > 0 && (
          <div className="flex items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2">
            <span className="text-sm">已选 {selected.size} 篇</span>
            <div className="ml-auto flex gap-2">
              <Button size="sm" variant="outline" onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
                <Download className="h-4 w-4" /> 导出
              </Button>
              <Button size="sm" variant="destructive" onClick={handleDelete} disabled={deleteMutation.isPending}>
                <Trash2 className="h-4 w-4" /> 删除
              </Button>
            </div>
          </div>
        )}

        {isLoading ? (
          <p className="text-sm text-muted-foreground">加载中…</p>
        ) : !notes || notes.items.length === 0 ? (
          <Card><CardContent className="py-10 text-center text-sm text-muted-foreground">
            暂无笔记，点击「新建笔记」开始记录。
          </CardContent></Card>
        ) : (
          <div className="space-y-2">
            {notes.items.map((note) => (
              <div key={note.note_id} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  className="h-4 w-4 shrink-0 accent-primary"
                  checked={selected.has(note.note_id)}
                  onChange={() => toggleSelect(note.note_id)}
                />
                <Link to={`/learning/${note.note_id}`} className="block min-w-0 flex-1">
                  <Card className="transition-colors hover:bg-muted/50">
                    <CardContent className="flex items-center justify-between gap-4 p-4">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary">{NOTE_TYPES[note.note_type] ?? note.note_type}</Badge>
                          <Badge variant={STATUS_VARIANT[note.status] ?? "outline"}>
                            {NOTE_STATUS[note.status] ?? note.status}
                          </Badge>
                          {note.is_ai_assisted && <Badge variant="ai">AI 辅助</Badge>}
                        </div>
                        <p className="mt-1.5 truncate font-medium">{note.title}</p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {note.word_count} 字 · {note.mentor_name || "未关联老师"} · 更新于 {note.updated_at}
                        </p>
                      </div>
                      {note.record_id != null && (
                        <Badge variant="outline" className="shrink-0">关联病案 #{note.record_id}</Badge>
                      )}
                    </CardContent>
                  </Card>
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1 text-sm transition-colors",
        active ? "border-primary bg-primary text-primary-foreground" : "hover:bg-muted",
      )}
    >
      {children}
    </button>
  )
}
