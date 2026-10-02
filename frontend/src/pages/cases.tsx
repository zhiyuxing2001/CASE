import { useQuery } from "@tanstack/react-query"
import { CalendarDays, ChevronLeft, ChevronRight, Plus, Search, X } from "lucide-react"
import { useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"

import { fetchMentors, fetchRecords, type RecordQuery } from "@/api/cases"
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

const VISIT_TYPE: Record<number, { label: string; variant: "default" | "secondary" | "outline" }> = {
  0: { label: "初诊", variant: "default" },
  1: { label: "复诊", variant: "secondary" },
  2: { label: "随访", variant: "outline" },
}

export function Cases() {
  const navigate = useNavigate()
  const [draft, setDraft] = useState<RecordQuery>({ page: 1, page_size: 20 })
  const [query, setQuery] = useState<RecordQuery>({ page: 1, page_size: 20 })

  const { data: mentors = [] } = useQuery({
    queryKey: ["mentors"],
    queryFn: fetchMentors,
  })

  const { data, isLoading, isError } = useQuery({
    queryKey: ["records", query],
    queryFn: () => fetchRecords(query),
  })

  const totalPages = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1),
    [data],
  )

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
        <p className="text-sm text-muted-foreground">
          共收录病案，支持按证型、药味、老师与日期组合筛选。
        </p>
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
                  placeholder="搜索主诉、证型、病名、药味…（支持 2 字词）"
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
            <Input
              className="w-32"
              placeholder="药味"
              value={draft.herb ?? ""}
              onChange={(e) => setDraft({ ...draft, herb: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && applySearch()}
            />
            <MentorFilter
              mentors={mentors}
              value={draft.mentor_id ?? ""}
              onChange={(mentor_id) => setDraft({ ...draft, mentor_id })}
            />
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <CalendarDays className="h-4 w-4" />
              <Input
                className="w-36"
                type="date"
                value={draft.date_from ?? ""}
                onChange={(e) => setDraft({ ...draft, date_from: e.target.value })}
              />
              <span>至</span>
              <Input
                className="w-36"
                type="date"
                value={draft.date_to ?? ""}
                onChange={(e) => setDraft({ ...draft, date_to: e.target.value })}
              />
            </div>
          </div>
        </CardContent>
      </Card>

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
                  <TableHead className="w-28">就诊日期</TableHead>
                  <TableHead className="w-20">诊次</TableHead>
                  <TableHead>患者</TableHead>
                  <TableHead>主诉</TableHead>
                  <TableHead>中医病名</TableHead>
                  <TableHead>证型</TableHead>
                  <TableHead className="w-16">药味</TableHead>
                  <TableHead className="w-24">带教老师</TableHead>
                  <TableHead className="w-20">状态</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading && (
                  <TableRow>
                    <TableCell colSpan={9} className="py-10 text-center text-muted-foreground">
                      加载中…
                    </TableCell>
                  </TableRow>
                )}
                {!isLoading && data && data.items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={9} className="py-10 text-center text-muted-foreground">
                      暂无匹配病案
                    </TableCell>
                  </TableRow>
                )}
                {data?.items.map((row) => {
                  const visit = VISIT_TYPE[row.visit_type] ?? VISIT_TYPE[0]
                  return (
                    <TableRow
                      key={row.record_id}
                      className="cursor-pointer"
                      onClick={() => navigate(`/cases/${row.record_id}`)}
                    >
                      <TableCell className="tabular-nums text-muted-foreground">
                        {row.clinic_date}
                      </TableCell>
                      <TableCell>
                        <Badge variant={visit.variant}>{visit.label}</Badge>
                      </TableCell>
                      <TableCell className="font-medium">{row.patient_name}</TableCell>
                      <TableCell className="max-w-[260px] truncate">{row.complaint}</TableCell>
                      <TableCell>{row.tcm_disease || "—"}</TableCell>
                      <TableCell>{row.syndrome || "—"}</TableCell>
                      <TableCell className="tabular-nums">{row.herb_count}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {row.mentor_name || "—"}
                      </TableCell>
                      <TableCell>
                        {row.needs_review ? (
                          <Badge variant="warning">待校对</Badge>
                        ) : (
                          <Badge variant="outline">已确认</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* 分页 */}
      {data && data.total > 0 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>共 {data.total} 份 · 第 {query.page ?? 1} / {totalPages} 页</span>
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
