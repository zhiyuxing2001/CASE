import { useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, Calendar, GraduationCap, MapPin, Pencil, Star } from "lucide-react"
import { useState } from "react"
import { Link, useParams } from "react-router-dom"
import { toast } from "sonner"

import { fetchMentorDetail } from "@/api/mentors"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { MentorFormDialog } from "@/pages/mentors"

export function MentorDetail() {
  const { mentorId = "" } = useParams()
  const queryClient = useQueryClient()
  const [editOpen, setEditOpen] = useState(false)

  const { data: mentor, isLoading, isError } = useQuery({
    queryKey: ["mentor-detail", mentorId],
    queryFn: () => fetchMentorDetail(mentorId),
    enabled: Boolean(mentorId),
  })

  if (isLoading) return <div className="p-8 text-sm text-muted-foreground">加载中…</div>
  if (isError || !mentor) return <div className="p-8 text-sm text-destructive">导师不存在或加载失败。</div>

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-8">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/mentors"><ArrowLeft className="h-4 w-4" /> 返回导师列表</Link>
        </Button>
        <Button size="sm" variant="outline" onClick={() => setEditOpen(true)}>
          <Pencil className="h-4 w-4" /> 编辑
        </Button>
      </div>

      {/* 导师简介 */}
      <Card>
        <CardContent className="space-y-4 p-6">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
              <GraduationCap className="h-7 w-7" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-semibold">{mentor.mentor_name}</h2>
                {mentor.title && <Badge variant="secondary">{mentor.title}</Badge>}
                {mentor.is_primary && <Badge>主带教</Badge>}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {[mentor.affiliation, mentor.department].filter(Boolean).join(" · ")}
              </p>
            </div>
          </div>

          <div className="grid gap-2 text-sm sm:grid-cols-2">
            {mentor.expertise && (
              <div className="flex gap-2"><Star className="mt-0.5 h-4 w-4 shrink-0 text-primary" /><span>擅长：{mentor.expertise}</span></div>
            )}
            {mentor.clinic_time && (
              <div className="flex gap-2"><Calendar className="mt-0.5 h-4 w-4 shrink-0 text-primary" /><span>出诊时间：{mentor.clinic_time}</span></div>
            )}
            {mentor.clinic_location && (
              <div className="flex gap-2"><MapPin className="mt-0.5 h-4 w-4 shrink-0 text-primary" /><span>出诊地点：{mentor.clinic_location}</span></div>
            )}
          </div>

          {mentor.bio && (
            <div className="rounded-lg border bg-muted/30 p-3">
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{mentor.bio}</p>
            </div>
          )}
          {mentor.notes && (
            <p className="text-xs text-muted-foreground">备注：{mentor.notes}</p>
          )}
        </CardContent>
      </Card>

      {/* 统计 */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <span className="text-2xl font-semibold tabular-nums">{mentor.visit_count}</span>
            <span className="text-sm text-muted-foreground">次跟诊</span>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <span className="text-2xl font-semibold tabular-nums">{mentor.note_count}</span>
            <span className="text-sm text-muted-foreground">篇笔记</span>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* 高频证型 */}
        <Card>
          <CardHeader><CardTitle className="text-base">高频证型</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {mentor.top_syndromes.length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无数据</p>
            ) : (
              mentor.top_syndromes.map((s) => {
                const max = mentor.top_syndromes[0]?.count || 1
                return (
                  <div key={s.syndrome} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="truncate">{s.syndrome}</span>
                      <span className="tabular-nums text-muted-foreground">{s.count}</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted">
                      <div className="h-1.5 rounded-full bg-primary" style={{ width: `${(s.count / max) * 100}%` }} />
                    </div>
                  </div>
                )
              })
            )}
          </CardContent>
        </Card>

        {/* 最近病案 */}
        <Card>
          <CardHeader><CardTitle className="text-base">最近病案</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {mentor.recent_records.length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无病案</p>
            ) : (
              mentor.recent_records.map((r) => (
                <Link
                  key={r.record_id}
                  to={`/cases/${r.record_id}`}
                  className="flex items-center justify-between rounded-md px-2 py-1.5 text-sm hover:bg-muted"
                >
                  <span className="truncate">
                    {r.patient_name}
                    {r.syndrome && <span className="text-muted-foreground"> · {r.syndrome}</span>}
                  </span>
                  <span className="shrink-0 text-xs text-muted-foreground tabular-nums">{r.clinic_date}</span>
                </Link>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <MentorFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        editingId={mentorId}
        onSaved={() => {
          setEditOpen(false)
          toast.success("已保存")
          void queryClient.invalidateQueries({ queryKey: ["mentor-detail", mentorId] })
          void queryClient.invalidateQueries({ queryKey: ["mentor-list"] })
        }}
      />
    </div>
  )
}
