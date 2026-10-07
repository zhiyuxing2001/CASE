import { useMutation, useQuery } from "@tanstack/react-query"
import { ArrowLeft, Copy, Info, Loader2, Plus, Sparkles, Trash2 } from "lucide-react"
import { useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { toast } from "sonner"

import {
  commitOcrJob,
  extractOcrJob,
  fetchOcrJob,
  structureOcrJob,
  type OcrCommitPayload,
  type OcrHerb,
  type OcrLabResult,
  type OcrStructured,
} from "@/api/ocr"
import { fetchTemplates } from "@/api/templates"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

const CONFIDENT = 0.6

function emptyStructured(): OcrStructured {
  return {
    narrative: {
      complaint: "", present_illness: "", past_history: "", allergy_history: "",
      body_of_tongue: "", fur_of_tongue: "", pulse: "", auxiliary_exam: "",
    },
    diagnosis: { tcm_disease: "", syndrome: "", wm_diagnosis: "", patterns_analysis: "" },
    treatment: {
      treatment_principle: "", formula_name: "", dose_count: null,
      decoction: "", usage: "",
    },
    herbs: [],
    lab_results: [],
  }
}

export function OcrReview() {
  const { jobId = "" } = useParams()
  const navigate = useNavigate()
  const [selected, setSelected] = useState<number | null>(null)

  const [patientName, setPatientName] = useState("")
  const [gender, setGender] = useState("0")
  const [birthday, setBirthday] = useState("")
  const [clinicDate, setClinicDate] = useState(new Date().toISOString().slice(0, 10))
  const [structured, setStructured] = useState<OcrStructured>(emptyStructured)
  const [templateId, setTemplateId] = useState("")

  const { data: job, isLoading, isError } = useQuery({
    queryKey: ["ocr-job", jobId],
    queryFn: () => fetchOcrJob(jobId),
  })
  const { data: templates = [] } = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  })

  const structure = useMutation({
    mutationFn: () => structureOcrJob(jobId, templateId || null),
    onSuccess: (res) => {
      if (res.degraded || !res.ai_configured) {
        toast.warning("AI 未配置（缺少 API Key），无法结构化")
        return
      }
      setStructured(res.structured)
      toast.success(`已结构化 · ${res.model} · prompt ${res.prompt_version}`)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const extract = useMutation({
    mutationFn: () => extractOcrJob(jobId, templateId),
    onSuccess: (res) => {
      setStructured(res.structured)
      toast.success("已按模板提取，请校对后入库")
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const commit = useMutation({
    mutationFn: (payload: OcrCommitPayload) => commitOcrJob(jobId, payload),
    onSuccess: (res) => {
      toast.success("已入库")
      navigate(`/cases/${res.record_id}`)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  if (isLoading) {
    return <div className="p-8 text-sm text-muted-foreground">加载识别结果…</div>
  }
  if (isError || !job) {
    return <div className="p-8 text-sm text-destructive">识别作业不存在或加载失败。</div>
  }

  function copyLine(text: string) {
    void navigator.clipboard.writeText(text)
    toast.success("已复制")
  }

  function setNarrative(key: string, value: string) {
    setStructured((s) => ({ ...s, narrative: { ...s.narrative, [key]: value } }))
  }
  function setDiagnosis(key: string, value: string) {
    setStructured((s) => ({ ...s, diagnosis: { ...s.diagnosis, [key]: value } }))
  }
  function setTreatment(key: string, value: string | number | null) {
    setStructured((s) => ({ ...s, treatment: { ...s.treatment, [key]: value } }))
  }
  function setHerb(i: number, patch: Partial<OcrHerb>) {
    setStructured((s) => ({
      ...s,
      herbs: s.herbs.map((h, idx) => (idx === i ? { ...h, ...patch } : h)),
    }))
  }
  function setLab(i: number, patch: Partial<OcrLabResult>) {
    setStructured((s) => ({
      ...s,
      lab_results: s.lab_results.map((l, idx) => (idx === i ? { ...l, ...patch } : l)),
    }))
  }

  const needReviewCount = structured.herbs.filter((h) => h.needs_review).length

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-8">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/intake"><ArrowLeft className="h-4 w-4" /> 重新上传</Link>
        </Button>
        <div className="flex gap-2">
          {job.degraded_mode === 1 && <Badge variant="warning">仅本地识别（AI 未配置）</Badge>}
          <Badge variant="outline">共 {job.lines.length} 行</Badge>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* 左：原图 + 识别框 */}
        <Card className="overflow-hidden">
          <CardContent className="p-0">
            <div className="relative">
              <img
                src={`/api/attachments/${job.attach_id}/file`}
                alt="原图"
                className="block w-full"
              />
              {job.lines.map((line, i) => {
                const [x, y, w, h] = line.bbox
                const low = line.confidence < CONFIDENT
                return (
                  <div
                    key={i}
                    onClick={() => setSelected(i)}
                    className={cn(
                      "absolute cursor-pointer border-2 transition-colors",
                      low ? "border-amber-500 bg-amber-500/15" : "border-blue-400/50 bg-blue-400/5",
                      selected === i && "border-primary bg-primary/20",
                    )}
                    style={{
                      left: `${x * 100}%`, top: `${y * 100}%`,
                      width: `${w * 100}%`, height: `${h * 100}%`,
                    }}
                  />
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* 右：识别文本 + 结构化 + 校对 */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base">识别文本</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => copyLine(job.vision_text)}>
                <Copy className="h-4 w-4" /> 复制全文
              </Button>
            </CardHeader>
            <CardContent className="space-y-1">
              {job.lines.map((line, i) => (
                <button
                  key={i}
                  onClick={() => setSelected(i)}
                  className={cn(
                    "flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted",
                    selected === i && "bg-accent",
                  )}
                >
                  <Badge variant={line.confidence >= CONFIDENT ? "success" : "warning"} className="mt-0.5 w-12 shrink-0 justify-center tabular-nums">
                    {line.confidence.toFixed(2)}
                  </Badge>
                  <span className="min-w-0 flex-1">{line.text}</span>
                  <Copy
                    className="h-3.5 w-3.5 shrink-0 cursor-pointer text-muted-foreground hover:text-foreground"
                    onClick={(e) => { e.stopPropagation(); copyLine(line.text) }}
                  />
                </button>
              ))}
            </CardContent>
          </Card>

          {/* AI 结构化 */}
          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2 text-base">
                <Sparkles className="h-4 w-4 text-ai" /> AI 结构化
              </CardTitle>
              {structure.data?.model && (
                <span className="text-xs text-muted-foreground">
                  {structure.data.model} · {structure.data.prompt_version}
                </span>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1.5">
                <Label>界面模板</Label>
                <Select value={templateId || "__none__"} onValueChange={(v) => setTemplateId(v === "__none__" ? "" : v)}>
                  <SelectTrigger><SelectValue placeholder="选择界面模板（可选）" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">不使用模板</SelectItem>
                    {templates.map((t) => (
                      <SelectItem key={t.template_id} value={t.template_id}>{t.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {templates.length === 0 && (
                  <p className="text-xs text-muted-foreground">
                    尚无模板，可到「字典维护 → 界面模板」新建。
                  </p>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  onClick={() => structure.mutate()}
                  disabled={structure.isPending || job.degraded_mode === 1}
                >
                  {structure.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  结构化识别（通道 B）
                </Button>
                <Button
                  variant="outline"
                  onClick={() => extract.mutate()}
                  disabled={extract.isPending || !templateId}
                >
                  {extract.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Info className="h-4 w-4" />}
                  按模板提取（本地）
                </Button>
              </div>
              {job.degraded_mode === 1 && (
                <p className="text-xs text-muted-foreground">
                  未配置 API Key，通道 B 不可用；可用「按模板提取」预填字段后人工校对。
                </p>
              )}
              {structured.herbs.length > 0 && (
                <p className="text-sm">
                  识别出 {structured.herbs.length} 味药
                  {needReviewCount > 0 && (
                    <Badge variant="warning" className="ml-2">待校对 {needReviewCount}</Badge>
                  )}
                </p>
              )}
            </CardContent>
          </Card>

          {/* 校对入库 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Info className="h-4 w-4" /> 校对入库
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label>患者姓名 <span className="text-destructive">*</span></Label>
                  <Input value={patientName} onChange={(e) => setPatientName(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label>性别</Label>
                  <Select value={gender} onValueChange={setGender}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">女</SelectItem>
                      <SelectItem value="1">男</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>出生日期 <span className="text-destructive">*</span></Label>
                  <Input type="date" value={birthday} onChange={(e) => setBirthday(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label>就诊日期</Label>
                  <Input type="date" value={clinicDate} onChange={(e) => setClinicDate(e.target.value)} />
                </div>
              </div>

              {/* 病案 */}
              <div className="space-y-1.5">
                <Label>主诉</Label>
                <Input value={structured.narrative.complaint ?? ""} onChange={(e) => setNarrative("complaint", e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label>现病史</Label>
                <Textarea rows={2} value={structured.narrative.present_illness ?? ""} onChange={(e) => setNarrative("present_illness", e.target.value)} />
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-1.5">
                  <Label>舌质</Label>
                  <Input value={structured.narrative.body_of_tongue ?? ""} onChange={(e) => setNarrative("body_of_tongue", e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label>舌苔</Label>
                  <Input value={structured.narrative.fur_of_tongue ?? ""} onChange={(e) => setNarrative("fur_of_tongue", e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label>脉象</Label>
                  <Input value={structured.narrative.pulse ?? ""} onChange={(e) => setNarrative("pulse", e.target.value)} />
                </div>
              </div>

              {/* 诊断 */}
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-1.5">
                  <Label>中医病名</Label>
                  <Input value={structured.diagnosis.tcm_disease ?? ""} onChange={(e) => setDiagnosis("tcm_disease", e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label>证型</Label>
                  <Input value={structured.diagnosis.syndrome ?? ""} onChange={(e) => setDiagnosis("syndrome", e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label>西医诊断</Label>
                  <Input value={structured.diagnosis.wm_diagnosis ?? ""} onChange={(e) => setDiagnosis("wm_diagnosis", e.target.value)} />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>辨证分析</Label>
                <Textarea rows={2} value={structured.diagnosis.patterns_analysis ?? ""} onChange={(e) => setDiagnosis("patterns_analysis", e.target.value)} />
              </div>

              {/* 治法 */}
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-1.5">
                  <Label>治法</Label>
                  <Input value={structured.treatment.treatment_principle as string ?? ""} onChange={(e) => setTreatment("treatment_principle", e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label>方剂名</Label>
                  <Input value={structured.treatment.formula_name as string ?? ""} onChange={(e) => setTreatment("formula_name", e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label>付数</Label>
                  <Input type="number" value={structured.treatment.dose_count == null ? "" : String(structured.treatment.dose_count)} onChange={(e) => setTreatment("dose_count", e.target.value ? Number(e.target.value) : null)} />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>煎煮法</Label>
                <Input value={structured.treatment.decoction as string ?? ""} onChange={(e) => setTreatment("decoction", e.target.value)} />
              </div>

              {/* 药味 */}
              <div className="space-y-2">
                <Label>处方药味</Label>
                <div className="overflow-hidden rounded-lg border">
                  <div className="grid grid-cols-[1fr_5rem_3.5rem_2rem] gap-2 border-b bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
                    <span>药味</span><span>剂量</span><span>单位</span><span />
                  </div>
                  <div className="divide-y">
                    {structured.herbs.map((h, i) => (
                      <div key={i} className={cn("grid grid-cols-[1fr_5rem_3.5rem_2rem] items-center gap-2 px-3 py-1.5", h.needs_review && "bg-amber-500/5")}>
                        <div className="flex items-center gap-2">
                          <Input value={h.herb_name} onChange={(e) => setHerb(i, { herb_name: e.target.value })} />
                          {h.needs_review && <Badge variant="warning" className="shrink-0">待校对</Badge>}
                        </div>
                        <Input type="number" value={h.dose == null ? "" : String(h.dose)} onChange={(e) => setHerb(i, { dose: e.target.value ? Number(e.target.value) : null })} className="tabular-nums" />
                        <Input value={h.unit} onChange={(e) => setHerb(i, { unit: e.target.value })} />
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setStructured((s) => ({ ...s, herbs: s.herbs.filter((_, j) => j !== i) }))}>
                          <Trash2 className="h-4 w-4 text-muted-foreground" />
                        </Button>
                      </div>
                    ))}
                    {structured.herbs.length === 0 && (
                      <div className="px-3 py-3 text-sm text-muted-foreground">暂无药味（可点击下方添加）</div>
                    )}
                  </div>
                </div>
                <Button type="button" variant="outline" size="sm" onClick={() => setStructured((s) => ({ ...s, herbs: [...s.herbs, { sequence: s.herbs.length, herb_name: "", dose: null, unit: "g", processing: "", decoction_note: "", role: "", needs_review: false, confidence: 1 }] }))}>
                  <Plus className="h-4 w-4" /> 添加药味
                </Button>
              </div>

              {/* 检验检查 */}
              <div className="space-y-2">
                <Label>检验检查</Label>
                <div className="overflow-hidden rounded-lg border">
                  <div className="grid grid-cols-[6rem_1fr_6rem_5rem_5rem_2rem] gap-2 border-b bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
                    <span>类别</span><span>项目</span><span>结果</span><span>单位</span><span>参考范围</span><span />
                  </div>
                  <div className="divide-y">
                    {structured.lab_results.map((l, i) => (
                      <div key={i} className={cn("grid grid-cols-[6rem_1fr_6rem_5rem_5rem_2rem] items-center gap-2 px-3 py-1.5", l.needs_review && "bg-amber-500/5")}>
                        <Select value={String(l.category)} onValueChange={(v) => setLab(i, { category: Number(v) })}>
                          <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="0">检验</SelectItem>
                            <SelectItem value="1">影像</SelectItem>
                            <SelectItem value="2">其他</SelectItem>
                          </SelectContent>
                        </Select>
                        <div className="flex items-center gap-1.5">
                          <Input value={l.item_name} onChange={(e) => setLab(i, { item_name: e.target.value })} />
                          {l.needs_review && <Badge variant="warning" className="shrink-0">待校对</Badge>}
                        </div>
                        <Input value={l.result_value} onChange={(e) => setLab(i, { result_value: e.target.value })} />
                        <Input value={l.unit} onChange={(e) => setLab(i, { unit: e.target.value })} />
                        <Input value={l.reference_range} onChange={(e) => setLab(i, { reference_range: e.target.value })} />
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setStructured((s) => ({ ...s, lab_results: s.lab_results.filter((_, j) => j !== i) }))}>
                          <Trash2 className="h-4 w-4 text-muted-foreground" />
                        </Button>
                      </div>
                    ))}
                    {structured.lab_results.length === 0 && (
                      <div className="px-3 py-3 text-sm text-muted-foreground">暂无检验检查（可点击下方添加）</div>
                    )}
                  </div>
                </div>
                <Button type="button" variant="outline" size="sm" onClick={() => setStructured((s) => ({ ...s, lab_results: [...s.lab_results, { category: 0, item_name: "", result_value: "", unit: "", reference_range: "", abnormal_flag: 0, needs_review: false, confidence: 1 }] }))}>
                  <Plus className="h-4 w-4" /> 添加检验检查
                </Button>
              </div>

              <Button
                className="w-full"
                disabled={commit.isPending}
                onClick={() => commit.mutate({
                  patient_name: patientName, gender: gender === "1",
                  birthday, clinic_date: clinicDate, structured,
                })}
              >
                {commit.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                确认并入库
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
