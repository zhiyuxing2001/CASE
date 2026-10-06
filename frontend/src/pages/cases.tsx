import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { CalendarDays, ChevronLeft, ChevronRight, Download, Plus, Search, Trash2, X } from "lucide-react"
import { useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { toast } from "sonner"

import { deleteCourses, exportCourses, fetchCourses, fetchMentors, type RecordQuery } from "@/api/cases"
import type { MentorOption } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export function Cases() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<RecordQuery>({ page: 1, page_size: 20 })
  const [query, setQuery] = useState<RecordQuery>({ page: 1, page_size: 20 })
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const { data: mentors = [] } = useQuery({
    queryKey: ["mentors"],
    queryFn: fetchMentors,
  })

  const { data, isLoading, isError } = useQuery({
    queryKey: ["courses", query],
    queryFn: () => fetchCourses(query),
  })

  const totalPages = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1),
    [data],
  )

  const deleteMutation = useMutation({
    mutationFn: () => deleteCourses([...selected]),
    onSuccess: (res) => {
      toast.success(`已删除 ${res.deleted} 条就诊记录`)
      setSelected(new Set())
      void queryClient.invalidateQueries({ queryKey: ["courses"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const exportMutation = useMutation({
    mutationFn: () => exportCourses([...selected]),
    onSuccess: () => toast.success("已导出 Excel"),
    onError: (e: Error) => toast.error(e.message),
  })

  function toggleSelect(courseId: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(courseId)) next.delete(courseId)
      else next.add(courseId)
      return next
    })
  }

  function toggleAll() {
    if (!data) return
    const allIds = data.items.map((i) => i.course_id)
    const allSelected = allIds.every((id) => selected.has(id))
    setSelected(allSelected ? new Set() : new Set(allIds))
  }

  function handleDelete() {
    if (window.confirm(`确定删除选中的 ${selected.size} 个病案？其下所有就诊记录将被软删除。`)) {
      deleteMutation.mutate()
    }
  }

  function applySearch() {
    setQuery({ ...draft, page: 1 })
  }

  function reset() {
    const next = { page: 1, page_size: 20 }
    setDraft(next)
    setQuery(next)
  }

  function setPage(page: number) {
    const next = { ...query, page }
    setDraft(next)
    setQuery(next)
  }

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-8">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">病案列表</h2>
          <p className="text-sm text-muted-foreground">
            每份病案是一段病程（初诊 + 随诊），进入后可添加新的随诊资料。
          </p>
        </div>
        <Button asChild>
          <Link to="/cases/new">
            <Plus className="h-4 w-4" /> 录入新病案
          </Link>
        </Button>
      </div>

      {/* 筛选区 */}
      <Card>
        <CardContent className="space-y-4 p-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[260px] flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="pl-9"
                  placeholder="搜索患者、主诉、证型…（支持 2 字词）"
                  value={draft.q ?? ""}
                  onChange={(e) => setDraft({ ...draft, q: e.target.value })}
                  onKeyDown={(e) => e.key === "Enter" && applySearch()}
                />
              </div>
            </div>
            <Button onClick={applySearch}>搜索</Button>
            <Button variant="ghost" onClick={reset}>
              <X className="h-4 w-4" /> 重置
            </Button>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Input
              className="w-40"
              placeholder="证型"
              value={draft.syndrome ?? ""}
              onChange={(e) => setDraft({ ...draft, syndrome: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && applySearch()}
            />
            <MentorFilter
              mentors={mentors}
              value={draft.mentor_id ?? ""}
              onChange={(mentor_id) => setDraft({ ...draft, mentor_id })}
            />
          </div>
        </CardContent>
      </Card>

      {/* 批量操作栏 */}
      {selected.size > 0 && (
        <div className="flex items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2">
          <span className="text-sm">已选 {selected.size} 个病案</span>
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

      {/* 结果区 */}
      <Card>
        <CardContent className="p-0">
          {isError ? (
            <div className="p-10 text-center text-sm text-destructive">
              加载失败，请确认后端服务已启动（127.0.0.1:8765）。
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-primary"
                      checked={data?.items.length ? data.items.every((i) => selected.has(i.course_id)) : false}
                      onChange={toggleAll}
                    />
                  </TableHead>
                  <TableHead>患者</TableHead>
                  <TableHead>主诉（初诊）</TableHead>
                  <TableHead>证型</TableHead>
                  <TableHead className="w-24">就诊次数</TableHead>
                  <TableHead className="w-44">病程</TableHead>
                  <TableHead className="w-20">状态</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading && (
                  <TableRow>
                    <TableCell colSpan={7} className="py-10 text-center text-muted-foreground">
                      加载中…
                    </TableCell>
                  </TableRow>
                )}
                {!isLoading && data && data.items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="py-10 text-center text-muted-foreground">
                      暂无匹配病案
                    </TableCell>
                  </TableRow>
                )}
                {data?.items.map((row) => (
                  <TableRow
                    key={row.course_id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/cases/${row.first_record_id}`)}
                  >
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        className="h-4 w-4 accent-primary"
                        checked={selected.has(row.course_id)}
                        onChange={() => toggleSelect(row.course_id)}
                      />
                    </TableCell>
                    <TableCell className="font-medium">{row.patient_name}</TableCell>
                    <TableCell className="max-w-[260px] truncate">{row.complaint || "—"}</TableCell>
                    <TableCell>{row.syndrome || "—"}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{row.visit_count} 次</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      <span className="inline-flex items-center gap-1 tabular-nums">
                        <CalendarDays className="h-3.5 w-3.5" />
                        {row.first_date} ~ {row.last_date}
                      </span>
                    </TableCell>
                    <TableCell>
                      {row.needs_review ? (
                        <Badge variant="warning">待校对</Badge>
                      ) : (
                        <Badge variant="outline">已确认</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* 分页 */}
      {data && data.total > 0 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>共 {data.total} 份病程 · 第 {query.page ?? 1} / {totalPages} 页</span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              disabled={(query.page ?? 1) <= 1}
              onClick={() => setPage((query.page ?? 1) - 1)}
            >
              <ChevronLeft className="h-4 w-4" /> 上一页
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={(query.page ?? 1) >= totalPages}
              onClick={() => setPage((query.page ?? 1) + 1)}
            >
              下一页 <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function MentorFilter({
  mentors,
  value,
  onChange,
}: {
  mentors: MentorOption[]
  value: string
  onChange: (v: string) => void
}) {
  return (
    <Select value={value || "all"} onValueChange={(v) => onChange(v === "all" ? "" : v)}>
      <SelectTrigger className="w-40">
        <SelectValue placeholder="带教老师" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">全部老师</SelectItem>
        {mentors.map((m) => (
          <SelectItem key={m.mentor_id} value={m.mentor_id}>
            {m.mentor_name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
