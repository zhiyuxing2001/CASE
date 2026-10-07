import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { GraduationCap, Plus, Trash2 } from "lucide-react"
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { toast } from "sonner"

import {
  createMentor,
  deleteMentor,
  fetchMentorDetail,
  fetchMentorList,
  updateMentor,
  type MentorSummary,
  type MentorUpsert,
} from "@/api/mentors"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"

const EMPTY_FORM: MentorUpsert = {
  mentor_name: "", title: "", affiliation: "", department: "", expertise: "",
  clinic_time: "", clinic_location: "", bio: "", is_primary: false, notes: "",
}

export function Mentors() {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<MentorSummary | null>(null)

  const { data: mentors = [], isLoading } = useQuery({
    queryKey: ["mentor-list"],
    queryFn: fetchMentorList,
  })

  const del = useMutation({
    mutationFn: (id: string) => deleteMentor(id),
    onSuccess: () => {
      toast.success("已删除导师")
      void queryClient.invalidateQueries({ queryKey: ["mentor-list"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  function handleDelete(m: MentorSummary) {
    if (window.confirm(`确定删除导师「${m.mentor_name}」？其病案与笔记不会受影响。`)) {
      del.mutate(m.mentor_id)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">导师列表</h2>
          <p className="text-sm text-muted-foreground">带教老师一览，含跟诊与笔记统计。</p>
        </div>
        <Button onClick={() => { setEditing(null); setDialogOpen(true) }}>
          <Plus className="h-4 w-4" /> 添加导师
        </Button>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">加载中…</p>
      ) : mentors.length === 0 ? (
        <Card><CardContent className="py-10 text-center text-sm text-muted-foreground">
          暂无导师，点击「添加导师」录入第一位带教老师。
        </CardContent></Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {mentors.map((m) => (
            <Link key={m.mentor_id} to={`/mentors/${m.mentor_id}`} className="block">
              <Card className="h-full transition-colors hover:bg-muted/50">
                <CardContent className="space-y-3 p-5">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                        <GraduationCap className="h-5 w-5" />
                      </div>
                      <div>
                        <p className="font-semibold leading-tight">{m.mentor_name}</p>
                        {m.title && <p className="text-xs text-muted-foreground">{m.title}</p>}
                      </div>
                    </div>
                    {m.is_primary && <Badge>主带教</Badge>}
                  </div>
                  <div className="space-y-1 text-sm">
                    {m.department && <p className="text-muted-foreground">科室：{m.department}</p>}
                    {m.expertise && <p className="truncate text-muted-foreground">擅长：{m.expertise}</p>}
                  </div>
                  <div className="flex items-center gap-4 border-t pt-3 text-sm">
                    <span className="tabular-nums"><span className="font-semibold">{m.visit_count}</span> 次跟诊</span>
                    <span className="tabular-nums"><span className="font-semibold">{m.note_count}</span> 篇笔记</span>
                    <Button
                      variant="ghost" size="icon" className="ml-auto h-8 w-8"
                      onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleDelete(m) }}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <MentorFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editingId={editing?.mentor_id ?? null}
        onSaved={() => {
          setDialogOpen(false)
          void queryClient.invalidateQueries({ queryKey: ["mentor-list"] })
        }}
      />
    </div>
  )
}

export function MentorFormDialog({
  open,
  onOpenChange,
  editingId,
  onSaved,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  editingId: string | null
  onSaved: () => void
}) {
  const [form, setForm] = useState<MentorUpsert>({ ...EMPTY_FORM })
  const { data: detail } = useQuery({
    queryKey: ["mentor-detail", editingId],
    queryFn: () => fetchMentorDetail(editingId!),
    enabled: Boolean(editingId),
  })
  useEffect(() => {
    if (detail && editingId) {
      const { mentor_id: _omit, ...rest } = detail
      setForm({ ...EMPTY_FORM, ...rest })
    } else if (!editingId) {
      setForm({ ...EMPTY_FORM })
    }
  }, [detail, editingId])

  const save = useMutation({
    mutationFn: () => editingId ? updateMentor(editingId, form) : createMentor(form),
    onSuccess: () => { toast.success("已保存"); onSaved() },
    onError: (e: Error) => toast.error(e.message),
  })

  function set<K extends keyof MentorUpsert>(key: K, value: MentorUpsert[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader><DialogTitle>{editingId ? "编辑导师" : "添加导师"}</DialogTitle></DialogHeader>
        <div className="grid grid-cols-2 gap-3 py-4">
          <Field label="姓名" required><Input value={form.mentor_name} onChange={(e) => set("mentor_name", e.target.value)} /></Field>
          <Field label="职称"><Input value={form.title} onChange={(e) => set("title", e.target.value)} placeholder="主任医师" /></Field>
          <Field label="所属机构"><Input value={form.affiliation} onChange={(e) => set("affiliation", e.target.value)} placeholder="医院名称" /></Field>
          <Field label="科室"><Input value={form.department} onChange={(e) => set("department", e.target.value)} placeholder="消化科" /></Field>
          <div className="col-span-2">
            <Field label="擅长领域"><Input value={form.expertise} onChange={(e) => set("expertise", e.target.value)} placeholder="慢性胃炎、功能性胃肠病" /></Field>
          </div>
          <Field label="出诊时间"><Input value={form.clinic_time} onChange={(e) => set("clinic_time", e.target.value)} placeholder="周二、四上午" /></Field>
          <Field label="出诊地点"><Input value={form.clinic_location} onChange={(e) => set("clinic_location", e.target.value)} placeholder="门诊楼3层303室" /></Field>
          <div className="col-span-2">
            <Field label="简介"><Textarea value={form.bio} onChange={(e) => set("bio", e.target.value)} rows={3} placeholder="导师的简要介绍…" /></Field>
          </div>
          <Field label="备注"><Input value={form.notes} onChange={(e) => set("notes", e.target.value)} /></Field>
          <Field label="主带教">
            <Select value={form.is_primary ? "1" : "0"} onValueChange={(v) => set("is_primary", v === "1")}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="0">否</SelectItem><SelectItem value="1">是</SelectItem></SelectContent>
            </Select>
          </Field>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button disabled={!form.mentor_name.trim() || save.isPending} onClick={() => save.mutate()}>保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}{required && <span className="ml-0.5 text-destructive">*</span>}</Label>
      {children}
    </div>
  )
}
