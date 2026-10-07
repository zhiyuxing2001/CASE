import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, CheckCheck, Loader2 } from "lucide-react"
import { useEffect, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { toast } from "sonner"

import { fetchRecord, reviewRecord } from "@/api/cases"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { cn } from "@/lib/utils"

interface ReviewHerb {
  herb_name: string
  dose: number | null
  unit: string
  processing: string
  decoction_note: string
  role: string
  sequence: number
  needs_review: boolean
}
interface ReviewLab {
  item_name: string
  result_value: string
  unit: string
  reference_range: string
  abnormal_flag: number
  needs_review: boolean
}
interface ReviewExam {
  item_name: string
  finding: string
  conclusion: string
  needs_review: boolean
}

export function CaseReview() {
  const { recordId } = useParams<{ recordId: string }>()
  const id = Number(recordId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [herbs, setHerbs] = useState<ReviewHerb[]>([])
  const [labs, setLabs] = useState<ReviewLab[]>([])
  const [exams, setExams] = useState<ReviewExam[]>([])
  // 进入页面时待校对项的索引，保持稳定以便勾选后仍可回看
  const [flaggedHerbIdx, setFlaggedHerbIdx] = useState<number[]>([])
  const [flaggedLabIdx, setFlaggedLabIdx] = useState<number[]>([])
  const [flaggedExamIdx, setFlaggedExamIdx] = useState<number[]>([])

  const { data, isLoading, isError } = useQuery({
    queryKey: ["record", id],
    queryFn: () => fetchRecord(id),
    enabled: Number.isFinite(id),
  })

  useEffect(() => {
    if (!data) return
    setHerbs(data.herbs.map((h) => ({
      herb_name: h.herb_name, dose: h.dose, unit: h.unit,
      processing: h.processing, decoction_note: h.decoction_note,
      role: h.role, sequence: h.sequence, needs_review: h.needs_review,
    })))
    setLabs(data.lab_results.map((l) => ({
      item_name: l.item_name, result_value: l.result_value, unit: l.unit,
      reference_range: l.reference_range, abnormal_flag: l.abnormal_flag,
      needs_review: l.needs_review,
    })))
    setExams(data.exams.map((e) => ({
      item_name: e.item_name, finding: e.finding, conclusion: e.conclusion,
      needs_review: e.needs_review,
    })))
    setFlaggedHerbIdx(data.herbs.map((h, i) => (h.needs_review ? i : -1)).filter((i) => i >= 0))
    setFlaggedLabIdx(data.lab_results.map((l, i) => (l.needs_review ? i : -1)).filter((i) => i >= 0))
    setFlaggedExamIdx(data.exams.map((e, i) => (e.needs_review ? i : -1)).filter((i) => i >= 0))
  }, [data])

  const totalFlagged =
    herbs.filter((h) => h.needs_review).length +
    labs.filter((l) => l.needs_review).length +
    exams.filter((e) => e.needs_review).length

  const save = useMutation({
    mutationFn: () => reviewRecord(id, {
      herbs: herbs.map(({ sequence, herb_name, dose, unit, processing, decoction_note, role, needs_review }) => ({
        herb_name, dose, unit, processing, decoction_note, role, sequence, needs_review,
      })),
      lab_results: labs.map((l) => ({ ...l })),
      exams: exams.map((e) => ({ ...e })),
    }),
    onSuccess: () => {
      toast.success("校对已保存")
      void queryClient.invalidateQueries({ queryKey: ["record", id] })
      void queryClient.invalidateQueries({ queryKey: ["courses"] })
      navigate(`/cases/${id}`)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  function setHerb(i: number, patch: Partial<ReviewHerb>) {
    setHerbs((rows) => rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))
  }
  function setLab(i: number, patch: Partial<ReviewLab>) {
    setLabs((rows) => rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))
  }
  function setExam(i: number, patch: Partial<ReviewExam>) {
    setExams((rows) => rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))
  }

  function markAllReviewed() {
    setHerbs((rows) => rows.map((r) => ({ ...r, needs_review: false })))
    setLabs((rows) => rows.map((r) => ({ ...r, needs_review: false })))
    setExams((rows) => rows.map((r) => ({ ...r, needs_review: false })))
  }

  if (isLoading) return <div className="p-8 text-sm text-muted-foreground">加载中…</div>
  if (isError || !data) return <div className="p-8 text-sm text-destructive">病案不存在或加载失败。</div>

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-8">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" asChild>
          <Link to={`/cases/${id}`}><ArrowLeft className="h-4 w-4" /> 返回病案</Link>
        </Button>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={markAllReviewed} disabled={totalFlagged === 0}>
            <CheckCheck className="h-4 w-4" /> 全部标记已校对
          </Button>
          <Button size="sm" onClick={() => save.mutate()} disabled={save.isPending}>
            {save.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCheck className="h-4 w-4" />}
            保存校对
          </Button>
        </div>
      </div>

      <div>
        <h2 className="text-xl font-semibold tracking-tight">校对病案</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {data.patient.patient_name} · {String(data.record.clinic_date ?? "")} · 第 {String(data.record.visit_no ?? 1)} 诊
          {totalFlagged === 0 ? " · 已无待校对项" : ` · 待校对 ${totalFlagged} 项`}
        </p>
      </div>

      {totalFlagged === 0 ? (
        <Card><CardContent className="py-10 text-center text-sm text-muted-foreground">
          该诊次已无待校对项，可返回查看病案。
        </CardContent></Card>
      ) : (
        <>
          {flaggedHerbIdx.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">待校对药味</CardTitle>
                <CardDescription>修正误识别的药名、剂量与煎服法</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {flaggedHerbIdx.map((i) => {
                  const h = herbs[i]
                  return (
                    <ReviewRow key={i} checked={!h.needs_review} onCheck={(v) => setHerb(i, { needs_review: !v })}>
                      <div className="grid grid-cols-[1fr_4.5rem_3.5rem_1fr_1fr] gap-2">
                        <Input value={h.herb_name} onChange={(e) => setHerb(i, { herb_name: e.target.value })} />
                        <Input type="number" value={h.dose == null ? "" : String(h.dose)} onChange={(e) => setHerb(i, { dose: e.target.value ? Number(e.target.value) : null })} className="tabular-nums" />
                        <Input value={h.unit} onChange={(e) => setHerb(i, { unit: e.target.value })} />
                        <Input value={h.processing} onChange={(e) => setHerb(i, { processing: e.target.value })} placeholder="炮制" />
                        <Input value={h.decoction_note} onChange={(e) => setHerb(i, { decoction_note: e.target.value })} placeholder="如 先煎" />
                      </div>
                    </ReviewRow>
                  )
                })}
              </CardContent>
            </Card>
          )}

          {flaggedLabIdx.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">待校对检验</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {flaggedLabIdx.map((i) => {
                  const l = labs[i]
                  return (
                    <ReviewRow key={i} checked={!l.needs_review} onCheck={(v) => setLab(i, { needs_review: !v })}>
                      <div className="grid grid-cols-[1fr_5rem_4rem_6rem_5.5rem] gap-2">
                        <Input value={l.item_name} onChange={(e) => setLab(i, { item_name: e.target.value })} />
                        <Input value={l.result_value} onChange={(e) => setLab(i, { result_value: e.target.value })} />
                        <Input value={l.unit} onChange={(e) => setLab(i, { unit: e.target.value })} />
                        <Input value={l.reference_range} onChange={(e) => setLab(i, { reference_range: e.target.value })} />
                        <Select value={String(l.abnormal_flag)} onValueChange={(v) => setLab(i, { abnormal_flag: Number(v) })}>
                          <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="0">正常</SelectItem>
                            <SelectItem value="1">↑ 偏高</SelectItem>
                            <SelectItem value="2">↓ 偏低</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </ReviewRow>
                  )
                })}
              </CardContent>
            </Card>
          )}

          {flaggedExamIdx.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">待校对检查</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {flaggedExamIdx.map((i) => {
                  const e = exams[i]
                  return (
                    <ReviewRow key={i} checked={!e.needs_review} onCheck={(v) => setExam(i, { needs_review: !v })}>
                      <div className="space-y-1.5">
                        <Input value={e.item_name} onChange={(ev) => setExam(i, { item_name: ev.target.value })} placeholder="检查名称" />
                        <Input value={e.finding} onChange={(ev) => setExam(i, { finding: ev.target.value })} placeholder="检查所见" />
                        <Input value={e.conclusion} onChange={(ev) => setExam(i, { conclusion: ev.target.value })} placeholder="结论" />
                      </div>
                    </ReviewRow>
                  )
                })}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}

function ReviewRow({
  checked,
  onCheck,
  children,
}: {
  checked: boolean
  onCheck: (v: boolean) => void
  children: React.ReactNode
}) {
  return (
    <div className={cn("rounded-lg border p-3", checked ? "opacity-60" : "bg-amber-500/5")}>
      <div className="mb-2 flex items-center gap-2">
        <Badge variant="warning">待校对</Badge>
        <label className="ml-auto flex cursor-pointer items-center gap-1.5 text-sm">
          <input type="checkbox" className="h-4 w-4 accent-primary" checked={checked} onChange={(e) => onCheck(e.target.checked)} />
          已校对
        </label>
      </div>
      {children}
    </div>
  )
}
