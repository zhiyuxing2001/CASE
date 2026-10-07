import { useQuery } from "@tanstack/react-query"
import { BarChart3, BookOpen, FileText, Users, Zap } from "lucide-react"

import { fetchProgress, NOTE_TYPES } from "@/api/learning"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function LearningStats() {
  const { data: progress } = useQuery({ queryKey: ["learning-progress"], queryFn: fetchProgress })

  const noteTotal = progress
    ? Object.values(progress.note_counts).reduce((a, b) => a + b, 0)
    : 0

  const noteTypeItems = progress
    ? Object.entries(progress.note_counts)
        .map(([key, count]) => ({ label: NOTE_TYPES[Number(key)] ?? `类型${key}`, count }))
        .sort((a, b) => b.count - a.count)
    : []

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-8">
      <div>
        <h2 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
          <BarChart3 className="h-5 w-5 text-primary" /> 跟师统计
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          跟诊病案、证型与笔记的累计统计。
        </p>
      </div>

      {/* 概览 */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat icon={<FileText className="h-4 w-4" />} label="跟诊病案" value={progress?.total_records ?? 0} />
        <Stat icon={<Users className="h-4 w-4" />} label="患者" value={progress?.total_patients ?? 0} />
        <Stat icon={<BookOpen className="h-4 w-4" />} label="笔记" value={noteTotal} />
        <Stat icon={<Zap className="h-4 w-4" />} label="证型覆盖" value={progress?.total_syndromes ?? 0} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <BarList
          title="高频证型"
          description={`共覆盖 ${progress?.total_syndromes ?? 0} 种证型`}
          items={progress?.top_syndromes.map((s) => ({ label: s.syndrome, count: s.count })) ?? []}
        />
        <BarList
          title="笔记类型分布"
          description={`共 ${noteTotal} 篇笔记`}
          items={noteTypeItems}
        />
      </div>
    </div>
  )
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary">{icon}</div>
        <div>
          <p className="text-xl font-semibold tabular-nums">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  )
}

function BarList({
  title,
  description,
  items,
}: {
  title: string
  description?: string
  items: { label: string; count: number }[]
}) {
  const max = Math.max(1, ...items.map((i) => i.count))
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-2.5">
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无数据</p>
        ) : (
          items.map((item) => (
            <div key={item.label} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="truncate">{item.label}</span>
                <span className="ml-2 shrink-0 tabular-nums text-muted-foreground">{item.count}</span>
              </div>
              <div className="h-1.5 rounded-full bg-muted">
                <div
                  className="h-1.5 rounded-full bg-primary"
                  style={{ width: `${(item.count / max) * 100}%` }}
                />
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  )
}
