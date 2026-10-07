import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, ChevronLeft, ChevronRight, FileDown, History, Plus } from "lucide-react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"

import { downloadCaseReport, fetchRecord, fetchRecordHistory } from "@/api/cases"
import type { AuditEntry } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"

const VISIT_TYPE: Record<number, string> = { 0: "初诊", 1: "复诊", 2: "随访" }
const TABLE_CN: Record<string, string> = {
  info_record: "就诊信息",
  case_narrative: "病案",
  diagnosis: "诊断",
  treatment: "治疗",
  prescription_item: "药味",
}
const ACTION_CN: Record<number, string> = { 0: "新增", 1: "修改", 2: "删除", 3: "恢复", 4: "脱敏" }

function KV({ label, value, mono }: { label: string; value?: string | null; mono?: boolean }) {
  if (!value) return null
  return (
    <div className="flex gap-3 py-1.5">
      <span className="w-24 shrink-0 text-sm text-muted-foreground">{label}</span>
      <span className={cn("text-sm", mono && "font-mono tabular-nums")}>{value}</span>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="divide-y">{children}</CardContent>
    </Card>
  )
}

export function CaseDetail() {
  const { recordId } = useParams<{ recordId: string }>()
  const id = Number(recordId)

  const { data, isLoading, isError } = useQuery({
    queryKey: ["record", id],
    queryFn: () => fetchRecord(id),
    enabled: Number.isFinite(id),
  })

  const { data: history = [] } = useQuery({
    queryKey: ["record-history", id],
    queryFn: () => fetchRecordHistory(id),
    enabled: Number.isFinite(id),
  })

  if (isLoading) {
    return <div className="p-8 text-sm text-muted-foreground">加载中…</div>
  }
  if (isError || !data) {
    return <div className="p-8 text-sm text-destructive">病案不存在或加载失败。</div>
  }

  const record = data.record as Record<string, unknown>
  const herbs = data.herbs
  const course = data.course
  const currentIndex = course.findIndex((v) => v.record_id === id)
  const prevVisit = currentIndex > 0 ? course[currentIndex - 1] : null
  const nextVisit = currentIndex >= 0 && currentIndex < course.length - 1 ? course[currentIndex + 1] : null

  async function handleReport() {
    const courseId = String(record.course_id ?? "")
    if (!courseId) {
      toast.error("病案缺少 course_id，无法导出")
      return
    }
    try {
      await downloadCaseReport(courseId)
      toast.success("已导出 Word 报告")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "导出失败")
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-8">
      {/* 顶部 */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/cases">
            <ArrowLeft className="h-4 w-4" /> 返回列表
          </Link>
        </Button>
        <div className="flex gap-2">
          <Badge variant={record.visit_type === 0 ? "default" : "secondary"}>
            {VISIT_TYPE[(record.visit_type as number) ?? 0] ?? "初诊"}
            {record.visit_no ? ` · 第${record.visit_no}诊` : ""}
          </Badge>
          {herbs.some((h) => h.needs_review) && (
            <Badge variant="warning">有待校对药味</Badge>
          )}
          <Button size="sm" variant="outline" onClick={handleReport}>
            <FileDown className="h-4 w-4" /> 病案导出
          </Button>
          <Button size="sm" asChild>
            <Link
              to={`/cases/new?patient_id=${encodeURIComponent(String(record.patient_id ?? ""))}&parent_record_id=${record.father_id}`}
            >
              <Plus className="h-4 w-4" /> 添加随诊
            </Link>
          </Button>
        </div>
      </div>

      {/* 患者与就诊 */}
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg">
              {data.patient.patient_name}
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                {data.patient.gender ? "男" : "女"} · {(record.age as number | null) ?? "—"} 岁
              </span>
            </CardTitle>
            <CardDescription>
              就诊日期 {String(record.clinic_date ?? "")}
              {record.department ? ` · ${record.department}` : ""}
            </CardDescription>
          </div>
        </CardHeader>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[15rem_1fr]">
        {/* 病程目录（时间线） */}
        <aside className="lg:sticky lg:top-8 lg:self-start">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">病程目录</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-0.5">
                {course.map((visit, i) => {
                  const active = visit.record_id === id
                  return (
                    <Link
                      key={visit.record_id}
                      to={`/cases/${visit.record_id}`}
                      className="flex gap-3"
                    >
                      <div className="flex flex-col items-center">
                        <span
                          className={cn(
                            "mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full border-2",
                            active
                              ? "border-primary bg-primary"
                              : "border-muted-foreground/30 bg-background",
                          )}
                        />
                        {i < course.length - 1 && (
                          <span className="w-px flex-1 bg-border" />
                        )}
                      </div>
                      <div
                        className={cn(
                          "mb-1 flex-1 rounded-md px-2 py-1.5 transition-colors",
                          active ? "bg-primary/5" : "hover:bg-muted",
                        )}
                      >
                        <div className="flex items-center gap-2 text-sm">
                          <span className={cn("font-medium", active && "text-primary")}>
                            {visit.clinic_date}
                          </span>
                          <Badge variant={visit.visit_type === 0 ? "default" : "secondary"}>
                            {VISIT_TYPE[visit.visit_type] ?? "初诊"}
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          第 {visit.visit_no} 诊
                          {visit.syndrome ? ` · ${visit.syndrome}` : ""}
                        </div>
                        {visit.complaint && (
                          <div className="truncate text-xs text-muted-foreground">
                            {visit.complaint}
                          </div>
                        )}
                      </div>
                    </Link>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </aside>

        {/* 当前就诊详情 + 分页 */}
        <div className="space-y-4">
          {/* 分页 */}
          <div className="flex items-center justify-between">
            {prevVisit ? (
              <Button variant="outline" size="sm" asChild>
                <Link to={`/cases/${prevVisit.record_id}`}>
                  <ChevronLeft className="h-4 w-4" /> 上一诊
                </Link>
              </Button>
            ) : (
              <Button variant="outline" size="sm" disabled>
                <ChevronLeft className="h-4 w-4" /> 上一诊
              </Button>
            )}
            <span className="text-sm text-muted-foreground">
              第 {String(record.visit_no ?? 1)} 诊 / 共 {course.length} 诊
            </span>
            {nextVisit ? (
              <Button variant="outline" size="sm" asChild>
                <Link to={`/cases/${nextVisit.record_id}`}>
                  下一诊 <ChevronRight className="h-4 w-4" />
                </Link>
              </Button>
            ) : (
              <Button variant="outline" size="sm" disabled>
                下一诊 <ChevronRight className="h-4 w-4" />
              </Button>
            )}
          </div>

          {/* 病史 */}
          <Section title="病史">
            <KV label="主诉" value={data.narrative.complaint} />
            <KV label="现病史" value={data.narrative.present_illness} />
            <KV
              label="既往史"
              value={data.narrative.past_history || data.first_narrative?.past_history}
            />
            <KV
              label="个人史及婚育史"
              value={data.narrative.personal_history || data.first_narrative?.personal_history}
            />
            <KV
              label="过敏史"
              value={data.narrative.allergy_history || data.first_narrative?.allergy_history}
            />
            <div className="flex flex-wrap gap-x-8 py-2">
              <span className="text-sm">
                <span className="mr-2 text-muted-foreground">舌质</span>
                {data.narrative.body_of_tongue || "—"}
              </span>
              <span className="text-sm">
                <span className="mr-2 text-muted-foreground">舌苔</span>
                {data.narrative.fur_of_tongue || "—"}
              </span>
              <span className="text-sm">
                <span className="mr-2 text-muted-foreground">脉象</span>
                {data.narrative.pulse || "—"}
              </span>
            </div>
            <KV label="其他四诊" value={data.narrative.other_cond} />
            <KV label="体格检查" value={data.narrative.physical_exam} />
            <KV label="辅助检查" value={data.narrative.auxiliary_exam} />
          </Section>

          {/* 诊断 */}
          <Section title="诊断">
            <KV label="中医病名" value={data.diagnosis.tcm_disease ?? ""} />
            <KV label="证型" value={data.diagnosis.syndrome ?? ""} />
            <KV label="西医诊断" value={data.diagnosis.wm_diagnosis ?? ""} />
            <KV label="辨证分析" value={data.diagnosis.patterns_analysis ?? ""} />
            <KV label="鉴别诊断" value={data.diagnosis.differential_diagnosis ?? ""} />
          </Section>

          {/* 治疗 */}
          <Section title="治疗">
            <KV label="治法" value={data.treatment.treatment_principle as string} />
            <KV label="方剂名" value={data.treatment.formula_name as string} />
            <div className="flex flex-wrap gap-x-8 py-2">
              <span className="text-sm">
                <span className="mr-2 text-muted-foreground">付数</span>
                {(data.treatment.dose_count as number) || "—"}
              </span>
              <span className="text-sm">
                <span className="mr-2 text-muted-foreground">煎煮法</span>
                {(data.treatment.decoction as string) || "—"}
              </span>
              <span className="text-sm">
                <span className="mr-2 text-muted-foreground">用法</span>
                {(data.treatment.usage as string) || "—"}
              </span>
            </div>
            {herbs.length > 0 && (
              <div className="py-2">
                <div className="mb-2 text-sm text-muted-foreground">
                  处方（每行四味，特殊煎服法为上角标）
                </div>
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
                  {herbs.map((h) => (
                    <div
                      key={h.sequence}
                      className="font-mono text-sm leading-relaxed"
                      title={h.needs_review ? "待校对" : undefined}
                    >
                      <span className={h.needs_review ? "text-amber-600" : undefined}>
                        {h.herb_name_norm || h.herb_name}
                        {h.dose != null ? `${h.dose}${h.unit}` : ""}
                      </span>
                      {h.decoction_note && (
                        <sup className="ml-0.5 text-[10px] text-muted-foreground">
                          {h.decoction_note}
                        </sup>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
            <KV label="西药" value={data.treatment.western_medicine as string} />
            <KV label="医嘱与调护" value={data.treatment.advice as string} />
            <KV label="其他治疗" value={data.treatment.other_treatment as string} />
          </Section>
        </div>
      </div>

      {/* 修改历史 */}
      {history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <History className="h-4 w-4" /> 修改历史
            </CardTitle>
          </CardHeader>
          <CardContent>
            <HistoryTable entries={history} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function HistoryTable({ entries }: { entries: AuditEntry[] }) {
  return (
    <div className="space-y-1">
      {entries.map((e, i) => (
        <div key={i}>
          <div className="flex items-center gap-3 px-2 py-1.5 text-sm">
            <span className="text-xs text-muted-foreground tabular-nums">
              {e.changed_at}
            </span>
            <Badge variant="outline">{TABLE_CN[e.table_name] ?? e.table_name}</Badge>
            <Badge variant="secondary">{ACTION_CN[e.action] ?? e.action}</Badge>
            {e.field_name && (
              <span className="font-mono text-xs text-muted-foreground">
                {e.field_name}
              </span>
            )}
            <span className="truncate">
              {e.old_value && <span className="text-muted-foreground line-through">{e.old_value}</span>}
              {e.old_value && e.new_value && " → "}
              {e.new_value && <span>{e.new_value}</span>}
            </span>
          </div>
          {i < entries.length - 1 && <Separator />}
        </div>
      ))}
    </div>
  )
}
