import { useQuery } from "@tanstack/react-query"
import { BarChart3, BookOpen, FileText, Leaf, User } from "lucide-react"

import {
  fetchDiseases,
  fetchHerbs,
  fetchOverview,
  fetchSyndromes,
  fetchTongue,
  type FreqItem,
  type HerbFreq,
} from "@/api/analytics"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function Analytics() {
  const overview = useQuery({ queryKey: ["analytics-overview"], queryFn: fetchOverview })
  const syndromes = useQuery({ queryKey: ["analytics-syndromes"], queryFn: fetchSyndromes })
  const herbs = useQuery({ queryKey: ["analytics-herbs"], queryFn: fetchHerbs })
  const tongue = useQuery({ queryKey: ["analytics-tongue"], queryFn: fetchTongue })
  const diseases = useQuery({ queryKey: ["analytics-diseases"], queryFn: fetchDiseases })

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-8">
      <div>
        <h2 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
          <BarChart3 className="h-5 w-5 text-primary" /> 病案分析
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          基于结构化字段的频次与剂量统计——舌脉、证型、病名与药味明细。
        </p>
      </div>

      {/* 概览 */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
        <Stat icon={<BookOpen className="h-4 w-4" />} label="病案" value={overview.data?.total_courses ?? 0} />
        <Stat icon={<FileText className="h-4 w-4" />} label="就诊" value={overview.data?.total_visits ?? 0} />
        <Stat icon={<User className="h-4 w-4" />} label="患者" value={overview.data?.total_patients ?? 0} />
        <Stat icon={<Leaf className="h-4 w-4" />} label="药味条目" value={overview.data?.total_herbs ?? 0} />
        <Stat icon={<Leaf className="h-4 w-4" />} label="不同药味" value={overview.data?.distinct_herbs ?? 0} />
        <Stat icon={<BarChart3 className="h-4 w-4" />} label="不同证型" value={overview.data?.distinct_syndromes ?? 0} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <BarList title="证型分布" items={syndromes.data ?? []} />
        <BarList title="中医病名分布" items={diseases.data ?? []} />
        <HerbList title="高频药味" items={herbs.data ?? []} />
        <div className="grid gap-4 sm:grid-cols-3 lg:col-span-2">
          <BarList title="舌质" items={tongue.data?.body ?? []} />
          <BarList title="舌苔" items={tongue.data?.coating ?? []} />
          <BarList title="脉象" items={tongue.data?.pulse ?? []} />
        </div>
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

function BarList({ title, items }: { title: string; items: FreqItem[] }) {
  const max = Math.max(1, ...items.map((i) => i.count))
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{items.length} 类</CardDescription>
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

function HerbList({ title, items }: { title: string; items: HerbFreq[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>按使用次数排序，附平均单剂剂量</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="divide-y">
          <div className="grid grid-cols-[2rem_1fr_4rem_5rem] gap-2 pb-1.5 text-xs text-muted-foreground">
            <span>#</span><span>药味</span><span className="text-right">次数</span>
            <span className="text-right">平均剂量</span>
          </div>
          {items.length === 0 ? (
            <p className="py-3 text-sm text-muted-foreground">暂无数据</p>
          ) : (
            items.map((h, i) => (
              <div key={h.label} className="grid grid-cols-[2rem_1fr_4rem_5rem] items-center gap-2 py-1.5 text-sm">
                <span className="text-muted-foreground">{i + 1}</span>
                <span className="font-medium">{h.label}</span>
                <span className="text-right tabular-nums">{h.count}</span>
                <span className="text-right font-mono tabular-nums text-muted-foreground">
                  {h.avg_dose != null ? `${h.avg_dose}g` : "—"}
                </span>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}
