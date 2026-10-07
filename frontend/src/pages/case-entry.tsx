import { useMutation, useQuery } from "@tanstack/react-query"
import { Plus, Trash2 } from "lucide-react"
import { useEffect, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { toast } from "sonner"

import {
  createPatient,
  createRecord,
  fetchHerbs,
  fetchMentors,
  fetchPatient,
  fetchPatients,
  fetchRecord,
  fetchSyndromes,
  fetchTerms,
  updateRecord,
} from "@/api/cases"
import type { MentorOption, PatientOption } from "@/api/types"
import { FreeTextCombobox, type ComboboxOption } from "@/components/free-text-combobox"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"

interface HerbRow {
  herb_name: string
  dose: string
  unit: string
  processing: string
  decoction_note: string
  role: string
}

interface LabRow {
  item_name: string
  result_value: string
  unit: string
  reference_range: string
  abnormal_flag: string
}

interface ExamRow {
  item_name: string
  finding: string
  conclusion: string
}

const EMPTY_LAB: LabRow = {
  item_name: "", result_value: "", unit: "",
  reference_range: "", abnormal_flag: "0",
}
const EMPTY_EXAM: ExamRow = { item_name: "", finding: "", conclusion: "" }

const EMPTY_HERB: HerbRow = {
  herb_name: "", dose: "", unit: "g", processing: "", decoction_note: "", role: "",
}

function Field({
  label,
  required,
  hint,
  children,
}: {
  label: string
  required?: boolean
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <Label>
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

export function CaseEntry() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const parentRecordId = searchParams.get("parent_record_id")
  const fixedPatientId = searchParams.get("patient_id")
  const isFollowUp = Boolean(parentRecordId && fixedPatientId)
  const editRecordId = searchParams.get("record_id")
  const isEdit = Boolean(editRecordId)

  // 患者
  const [patientMode, setPatientMode] = useState<"existing" | "new">("new")
  const [selectedPatient, setSelectedPatient] = useState<PatientOption | null>(null)
  const [newPatient, setNewPatient] = useState({ name: "", gender: false, birthday: "" })

  // 就诊
  const [visit, setVisit] = useState({
    clinic_date: new Date().toISOString().slice(0, 10),
    visit_type: isFollowUp ? "1" : "0",
    mentor_id: "",
    department: "",
    age: "",
    addr: "",
  })

  // 病案文本
  const [narrative, setNarrative] = useState({
    complaint: "", present_illness: "", past_history: "", personal_history: "",
    allergy_history: "", body_of_tongue: "", fur_of_tongue: "", pulse: "",
    other_cond: "", physical_exam: "", auxiliary_exam: "",
  })

  // 诊断
  const [diagnosis, setDiagnosis] = useState({
    tcm_disease: "", syndrome: "", syndrome_id: null as string | null,
    wm_diagnosis: "", patterns_analysis: "", differential_diagnosis: "",
  })

  // 治疗
  const [treatment, setTreatment] = useState({
    treatment_principle: "", formula_name: "", dose_count: "",
    decoction: "", usage: "", advice: "", western_medicine: "", other_treatment: "",
  })

  const [herbs, setHerbs] = useState<HerbRow[]>([{ ...EMPTY_HERB }])
  const [labResults, setLabResults] = useState<LabRow[]>([])
  const [exams, setExams] = useState<ExamRow[]>([])

  const { data: mentors = [] } = useQuery({ queryKey: ["mentors"], queryFn: fetchMentors })
  const { data: followUpPatient } = useQuery({
    queryKey: ["patient", fixedPatientId],
    queryFn: () => fetchPatient(fixedPatientId!),
    enabled: isFollowUp,
  })
  const { data: editRecord } = useQuery({
    queryKey: ["record", editRecordId],
    queryFn: () => fetchRecord(Number(editRecordId)),
    enabled: isEdit,
  })

  // 编辑模式：载入已有病案并回填表单
  useEffect(() => {
    if (!editRecord) return
    const rec = editRecord.record as Record<string, unknown>
    setVisit({
      clinic_date: String(rec.clinic_date ?? ""),
      visit_type: String(rec.visit_type ?? 0),
      mentor_id: String(rec.mentor_id ?? ""),
      department: String(rec.department ?? ""),
      age: rec.age != null ? String(rec.age) : "",
      addr: String(rec.addr ?? ""),
    })
    setNarrative({
      complaint: editRecord.narrative.complaint ?? "",
      present_illness: editRecord.narrative.present_illness ?? "",
      past_history: editRecord.narrative.past_history ?? "",
      personal_history: editRecord.narrative.personal_history ?? "",
      allergy_history: editRecord.narrative.allergy_history ?? "",
      body_of_tongue: editRecord.narrative.body_of_tongue ?? "",
      fur_of_tongue: editRecord.narrative.fur_of_tongue ?? "",
      pulse: editRecord.narrative.pulse ?? "",
      other_cond: editRecord.narrative.other_cond ?? "",
      physical_exam: editRecord.narrative.physical_exam ?? "",
      auxiliary_exam: editRecord.narrative.auxiliary_exam ?? "",
    })
    setDiagnosis({
      tcm_disease: editRecord.diagnosis.tcm_disease ?? "",
      syndrome: editRecord.diagnosis.syndrome ?? "",
      syndrome_id: editRecord.diagnosis.syndrome_id ?? null,
      wm_diagnosis: editRecord.diagnosis.wm_diagnosis ?? "",
      patterns_analysis: editRecord.diagnosis.patterns_analysis ?? "",
      differential_diagnosis: editRecord.diagnosis.differential_diagnosis ?? "",
    })
    setTreatment({
      treatment_principle: (editRecord.treatment.treatment_principle as string) ?? "",
      formula_name: (editRecord.treatment.formula_name as string) ?? "",
      dose_count: editRecord.treatment.dose_count != null ? String(editRecord.treatment.dose_count) : "",
      decoction: (editRecord.treatment.decoction as string) ?? "",
      usage: (editRecord.treatment.usage as string) ?? "",
      advice: (editRecord.treatment.advice as string) ?? "",
      western_medicine: (editRecord.treatment.western_medicine as string) ?? "",
      other_treatment: (editRecord.treatment.other_treatment as string) ?? "",
    })
    const herbRows = editRecord.herbs.map((h) => ({
      herb_name: h.herb_name_norm || h.herb_name,
      dose: h.dose != null ? String(h.dose) : "",
      unit: h.unit || "g",
      processing: h.processing || "",
      decoction_note: h.decoction_note || "",
      role: h.role || "",
    }))
    setHerbs(herbRows.length ? herbRows : [{ ...EMPTY_HERB }])
    setLabResults(editRecord.lab_results.map((l) => ({
      item_name: l.item_name,
      result_value: l.result_value,
      unit: l.unit,
      reference_range: l.reference_range,
      abnormal_flag: String(l.abnormal_flag),
    })))
    setExams(editRecord.exams.map((e) => ({
      item_name: e.item_name,
      finding: e.finding,
      conclusion: e.conclusion,
    })))
  }, [editRecord])

  const mutation = useMutation({
    mutationFn: async () => {
      let patientId = isEdit
        ? String(editRecord?.record.patient_id ?? "")
        : isFollowUp
          ? fixedPatientId
          : selectedPatient?.patient_id
      if (patientMode === "new" && !isFollowUp && !isEdit) {
        if (!newPatient.name.trim() || !newPatient.birthday) {
          throw new Error("请填写患者姓名与出生日期")
        }
        const created = await createPatient({
          patient_name: newPatient.name.trim(),
          gender: newPatient.gender,
          birthday: newPatient.birthday,
        })
        patientId = created.patient_id
      }
      if (!patientId) throw new Error("请选择或新建患者")
      if (!visit.clinic_date) throw new Error("请填写就诊日期")
      if (narrative.complaint.length > 20) throw new Error("主诉不能超过 20 字")

      const payload = {
        patient_id: patientId,
        clinic_date: visit.clinic_date,
        visit_type: Number(visit.visit_type),
        age: visit.age ? Number(visit.age) : null,
        mentor_id: visit.mentor_id || null,
        department: visit.department,
        addr: visit.addr,
        parent_record_id: isFollowUp ? Number(parentRecordId) : null,
        narrative,
        diagnosis,
        treatment: {
          treatment_principle: treatment.treatment_principle,
          formula_name: treatment.formula_name,
          dose_count: treatment.dose_count ? Number(treatment.dose_count) : null,
          decoction: treatment.decoction,
          usage: treatment.usage,
          advice: treatment.advice,
          other_treatment: treatment.other_treatment,
          western_medicine: treatment.western_medicine,
        },
        herbs: herbs
          .filter((h) => h.herb_name.trim())
          .map((h, i) => ({
            herb_name: h.herb_name.trim(),
            dose: h.dose ? Number(h.dose) : null,
            unit: h.unit || "g",
            processing: h.processing,
            decoction_note: h.decoction_note,
            role: h.role,
            sequence: i,
          })),
        lab_results: labResults
          .filter((l) => l.item_name.trim())
          .map((l) => ({
            item_name: l.item_name.trim(),
            result_value: l.result_value,
            unit: l.unit,
            reference_range: l.reference_range,
            abnormal_flag: Number(l.abnormal_flag),
          })),
        exams: exams
          .filter((e) => e.item_name.trim())
          .map((e) => ({
            item_name: e.item_name.trim(),
            finding: e.finding,
            conclusion: e.conclusion,
          })),
      }
      if (isEdit) return updateRecord(Number(editRecordId), payload)
      return createRecord(payload)
    },
    onSuccess: (res) => {
      toast.success(isEdit ? "病案已更新" : `病案已保存（编号 ${res.record_id}）`)
      navigate(isEdit ? `/cases/${editRecordId}` : `/cases`)
    },
    onError: (e: Error) => {
      toast.error(e.message)
    },
  })

  const herbLoad = (q: string) =>
    fetchHerbs(q).then((hs) =>
      hs.map((h) => ({ value: h.herb_id, label: h.herb_name, hint: h.category })),
    )
  const syndromeLoad = (q: string) =>
    fetchSyndromes(q).then((ss) =>
      ss.map((s) => ({ value: s.syndrome_id, label: s.syndrome_name, hint: s.category })),
    )
  const termLoad = (termType: number) => (q: string) =>
    fetchTerms(termType, q).then((ts) =>
      ts.map((t) => ({ value: String(t.term_id), label: t.term, hint: t.description })),
    )
  const patientLoad = (q: string) =>
    fetchPatients(q).then((ps) =>
      ps.map((p) => ({ value: p.patient_id, label: p.patient_name })),
    )

  function onPatientPick(_value: string, option?: ComboboxOption) {
    if (option?.value) {
      setSelectedPatient({ patient_id: option.value, patient_name: option.label, gender: false })
    }
  }

  function updateHerb(index: number, patch: Partial<HerbRow>) {
    setHerbs((rows) => rows.map((r, i) => (i === index ? { ...r, ...patch } : r)))
  }

  function updateLab(index: number, patch: Partial<LabRow>) {
    setLabResults((rows) => rows.map((r, i) => (i === index ? { ...r, ...patch } : r)))
  }

  function updateExam(index: number, patch: Partial<ExamRow>) {
    setExams((rows) => rows.map((r, i) => (i === index ? { ...r, ...patch } : r)))
  }

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-8 pb-24">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">
            {isEdit ? "编辑病案" : isFollowUp ? "添加随诊" : "录入新病案"}
          </h2>
          <p className="text-sm text-muted-foreground">自由书写，结构化字段仅用于检索与统计。</p>
        </div>
      </div>

      {/* 患者 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">患者</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          {isFollowUp || isEdit ? (
            <div className="flex items-center gap-2 rounded-md border bg-muted/50 px-3 py-2 text-sm">
              <span className="text-muted-foreground">
                {isEdit ? "患者" : "随诊对象"}
              </span>
              <span className="font-medium">
                {isEdit
                  ? editRecord?.patient.patient_name
                  : followUpPatient?.patient_name ?? "患者"}
              </span>
              <span className="text-muted-foreground">
                （{isEdit
                  ? (editRecord?.patient.gender ? "男" : "女")
                  : (followUpPatient?.gender ? "男" : "女")}）
              </span>
            </div>
          ) : (
            <>
              <div className="flex gap-2">
                <Button
                  variant={patientMode === "new" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setPatientMode("new")}
                >
                  新建患者
                </Button>
                <Button
                  variant={patientMode === "existing" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setPatientMode("existing")}
                >
                  已有患者
                </Button>
              </div>

              {patientMode === "new" ? (
                <div className="grid gap-4 sm:grid-cols-3">
                  <Field label="姓名" required>
                    <Input
                      value={newPatient.name}
                      onChange={(e) => setNewPatient({ ...newPatient, name: e.target.value })}
                    />
                  </Field>
                  <Field label="性别">
                    <Select
                      value={newPatient.gender ? "1" : "0"}
                      onValueChange={(v) => setNewPatient({ ...newPatient, gender: v === "1" })}
                    >
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="0">女</SelectItem>
                        <SelectItem value="1">男</SelectItem>
                      </SelectContent>
                    </Select>
                  </Field>
                  <Field label="出生日期" required>
                    <Input
                      type="date"
                      value={newPatient.birthday}
                      onChange={(e) => setNewPatient({ ...newPatient, birthday: e.target.value })}
                    />
                  </Field>
                </div>
              ) : (
                <Field label="选择患者">
                  <FreeTextCombobox
                    value={selectedPatient?.patient_name ?? ""}
                    onValueChange={onPatientPick}
                    load={patientLoad}
                    placeholder="输入姓名检索已有患者…"
                  />
                </Field>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* 就诊信息 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">就诊信息</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <Field label="就诊日期" required>
            <Input type="date" value={visit.clinic_date}
              onChange={(e) => setVisit({ ...visit, clinic_date: e.target.value })} />
          </Field>
          <Field label="就诊类型">
            <Select value={visit.visit_type}
              onValueChange={(v) => setVisit({ ...visit, visit_type: v })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="0">初诊</SelectItem>
                <SelectItem value="1">复诊</SelectItem>
                <SelectItem value="2">随访</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          <Field label="带教老师">
            <Select value={visit.mentor_id}
              onValueChange={(v) => setVisit({ ...visit, mentor_id: v })}>
              <SelectTrigger><SelectValue placeholder="选择老师" /></SelectTrigger>
              <SelectContent>
                {mentors.map((m: MentorOption) => (
                  <SelectItem key={m.mentor_id} value={m.mentor_id}>{m.mentor_name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field label="就诊科室">
            <Input value={visit.department}
              onChange={(e) => setVisit({ ...visit, department: e.target.value })} />
          </Field>
          <Field label="年龄">
            <Input type="number" value={visit.age}
              onChange={(e) => setVisit({ ...visit, age: e.target.value })} />
          </Field>
          <Field label="就诊地点">
            <Input value={visit.addr}
              onChange={(e) => setVisit({ ...visit, addr: e.target.value })} />
          </Field>
        </CardContent>
      </Card>

      {/* 病案文本 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">病案</CardTitle>
          <CardDescription>除舌质、舌苔、脉象外，均为自由文本，不必拆解。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Field label="主诉" required hint={`${narrative.complaint.length}/20 字`}>
            <Input value={narrative.complaint} maxLength={30}
              className={narrative.complaint.length > 20 ? "border-destructive" : ""}
              onChange={(e) => setNarrative({ ...narrative, complaint: e.target.value })} />
          </Field>
          <Field label="现病史">
            <Textarea value={narrative.present_illness} rows={3}
              onChange={(e) => setNarrative({ ...narrative, present_illness: e.target.value })} />
          </Field>
          <Field label="既往史">
            <Textarea value={narrative.past_history} rows={2}
              onChange={(e) => setNarrative({ ...narrative, past_history: e.target.value })} />
          </Field>
          <Field label="个人史及婚育史">
            <Textarea value={narrative.personal_history} rows={2}
              onChange={(e) => setNarrative({ ...narrative, personal_history: e.target.value })} />
          </Field>
          <Field label="过敏史">
            <Input value={narrative.allergy_history}
              onChange={(e) => setNarrative({ ...narrative, allergy_history: e.target.value })} />
          </Field>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="舌质">
              <FreeTextCombobox value={narrative.body_of_tongue}
                onValueChange={(v) => setNarrative({ ...narrative, body_of_tongue: v })}
                load={termLoad(1)} placeholder="如 淡红" />
            </Field>
            <Field label="舌苔">
              <FreeTextCombobox value={narrative.fur_of_tongue}
                onValueChange={(v) => setNarrative({ ...narrative, fur_of_tongue: v })}
                load={termLoad(2)} placeholder="如 薄白" />
            </Field>
            <Field label="脉象">
              <FreeTextCombobox value={narrative.pulse}
                onValueChange={(v) => setNarrative({ ...narrative, pulse: v })}
                load={termLoad(3)} placeholder="如 弦细" />
            </Field>
          </div>
          <Field label="其他望闻切诊">
            <Textarea value={narrative.other_cond} rows={2}
              onChange={(e) => setNarrative({ ...narrative, other_cond: e.target.value })} />
          </Field>
          <Field label="体格检查">
            <Textarea value={narrative.physical_exam} rows={2}
              onChange={(e) => setNarrative({ ...narrative, physical_exam: e.target.value })} />
          </Field>
          <Field label="辅助检查">
            <Textarea value={narrative.auxiliary_exam} rows={2}
              onChange={(e) => setNarrative({ ...narrative, auxiliary_exam: e.target.value })} />
          </Field>
        </CardContent>
      </Card>

      {/* 诊断 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">诊断</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <Field label="中医病名">
            <Input value={diagnosis.tcm_disease}
              onChange={(e) => setDiagnosis({ ...diagnosis, tcm_disease: e.target.value })} />
          </Field>
          <Field label="证型">
            <FreeTextCombobox value={diagnosis.syndrome}
              onValueChange={(v, o) => setDiagnosis({ ...diagnosis, syndrome: v, syndrome_id: (o?.value as string) ?? null })}
              load={syndromeLoad} placeholder="如 肝胃不和证" />
          </Field>
          <Field label="西医诊断" hint="多条以分号分隔">
            <Input value={diagnosis.wm_diagnosis}
              onChange={(e) => setDiagnosis({ ...diagnosis, wm_diagnosis: e.target.value })} />
          </Field>
          <Field label="辨证分析">
            <Textarea value={diagnosis.patterns_analysis} rows={3}
              onChange={(e) => setDiagnosis({ ...diagnosis, patterns_analysis: e.target.value })} />
          </Field>
          <Field label="鉴别诊断">
            <Textarea value={diagnosis.differential_diagnosis} rows={2}
              onChange={(e) => setDiagnosis({ ...diagnosis, differential_diagnosis: e.target.value })} />
          </Field>
        </CardContent>
      </Card>

      {/* 治疗与处方 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">治法与处方</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="治法">
              <Input value={treatment.treatment_principle}
                onChange={(e) => setTreatment({ ...treatment, treatment_principle: e.target.value })}
                placeholder="如 疏肝理气和胃" />
            </Field>
            <Field label="方剂名">
              <Input value={treatment.formula_name}
                onChange={(e) => setTreatment({ ...treatment, formula_name: e.target.value })}
                placeholder="如 柴胡疏肝散" />
            </Field>
          </div>

          {/* 处方编辑器 */}
          <div className="space-y-2">
            <Label>处方药味</Label>
            <div className="overflow-hidden rounded-lg border">
              <div className="grid grid-cols-[1fr_5.5rem_4.5rem_1fr_1fr_2rem] gap-2 border-b bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
                <span>药味</span><span>剂量</span><span>单位</span>
                <span>炮制</span><span>煎煮要求</span><span />
              </div>
              <div className="divide-y">
                {herbs.map((row, i) => (
                  <div key={i} className="grid grid-cols-[1fr_5.5rem_4.5rem_1fr_1fr_2rem] items-center gap-2 px-3 py-1.5">
                    <FreeTextCombobox
                      value={row.herb_name}
                      onValueChange={(v) => updateHerb(i, { herb_name: v })}
                      load={herbLoad}
                      placeholder="输入药名或拼音"
                    />
                    <Input type="number" value={row.dose}
                      onChange={(e) => updateHerb(i, { dose: e.target.value })}
                      placeholder="0" className="tabular-nums" />
                    <Input value={row.unit}
                      onChange={(e) => updateHerb(i, { unit: e.target.value })}
                      className="tabular-nums" />
                    <Input value={row.processing}
                      onChange={(e) => updateHerb(i, { processing: e.target.value })}
                      placeholder="如 醋炙" />
                    <Input value={row.decoction_note}
                      onChange={(e) => updateHerb(i, { decoction_note: e.target.value })}
                      placeholder="如 先煎" />
                    <Button variant="ghost" size="icon" className="h-8 w-8"
                      onClick={() => setHerbs((rows) => rows.filter((_, j) => j !== i))}>
                      <Trash2 className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
            <Button type="button" variant="outline" size="sm"
              onClick={() => setHerbs((rows) => [...rows, { ...EMPTY_HERB }])}>
              <Plus className="h-4 w-4" /> 添加药味
            </Button>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="付数">
              <Input type="number" value={treatment.dose_count}
                onChange={(e) => setTreatment({ ...treatment, dose_count: e.target.value })} />
            </Field>
            <Field label="煎煮法">
              <Input value={treatment.decoction}
                onChange={(e) => setTreatment({ ...treatment, decoction: e.target.value })}
                placeholder="如 水煎服" />
            </Field>
            <Field label="用法">
              <Input value={treatment.usage}
                onChange={(e) => setTreatment({ ...treatment, usage: e.target.value })}
                placeholder="如 日一剂，分早晚温服" />
            </Field>
          </div>
          <Field label="医嘱与调护">
            <Textarea value={treatment.advice} rows={2}
              onChange={(e) => setTreatment({ ...treatment, advice: e.target.value })} />
          </Field>
          <Field label="西药" hint="如 甲钴胺 0.5mg tid，与中药分开记录">
            <Textarea value={treatment.western_medicine} rows={2}
              onChange={(e) => setTreatment({ ...treatment, western_medicine: e.target.value })}
              placeholder="如 甲钴胺 0.5mg tid" />
          </Field>
          <Field label="其他治疗" hint="中成药、针灸、外治等">
            <Textarea value={treatment.other_treatment} rows={2}
              onChange={(e) => setTreatment({ ...treatment, other_treatment: e.target.value })} />
          </Field>
        </CardContent>
      </Card>

      {/* 检验 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">检验结果</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="overflow-hidden rounded-lg border">
            <div className="grid grid-cols-[1fr_1fr_5.5rem_6.5rem_5.5rem_2rem] gap-2 border-b bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
              <span>项目</span><span>结果</span><span>单位</span><span>参考范围</span><span>异常</span><span />
            </div>
            <div className="divide-y">
              {labResults.map((row, i) => (
                <div key={i} className="grid grid-cols-[1fr_1fr_5.5rem_6.5rem_5.5rem_2rem] items-center gap-2 px-3 py-1.5">
                  <Input value={row.item_name} onChange={(e) => updateLab(i, { item_name: e.target.value })} placeholder="如 白细胞计数" />
                  <Input value={row.result_value} onChange={(e) => updateLab(i, { result_value: e.target.value })} placeholder="如 12.5" />
                  <Input value={row.unit} onChange={(e) => updateLab(i, { unit: e.target.value })} placeholder="如 10^9/L" />
                  <Input value={row.reference_range} onChange={(e) => updateLab(i, { reference_range: e.target.value })} placeholder="如 3.5-9.5" />
                  <Select value={row.abnormal_flag} onValueChange={(v) => updateLab(i, { abnormal_flag: v })}>
                    <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">正常</SelectItem>
                      <SelectItem value="1">↑ 偏高</SelectItem>
                      <SelectItem value="2">↓ 偏低</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button variant="ghost" size="icon" className="h-8 w-8"
                    onClick={() => setLabResults((rows) => rows.filter((_, j) => j !== i))}>
                    <Trash2 className="h-4 w-4 text-muted-foreground" />
                  </Button>
                </div>
              ))}
              {labResults.length === 0 && (
                <div className="px-3 py-3 text-sm text-muted-foreground">暂无检验结果（可点击下方添加）</div>
              )}
            </div>
          </div>
          <Button type="button" variant="outline" size="sm"
            onClick={() => setLabResults((rows) => [...rows, { ...EMPTY_LAB }])}>
            <Plus className="h-4 w-4" /> 添加检验
          </Button>
        </CardContent>
      </Card>

      {/* 检查 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">检查报告</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="overflow-hidden rounded-lg border">
            <div className="grid grid-cols-[1fr_1.5fr_2rem] gap-2 border-b bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
              <span>检查名称</span><span>所见 / 结论</span><span />
            </div>
            <div className="divide-y">
              {exams.map((row, i) => (
                <div key={i} className="grid grid-cols-[1fr_1.5fr_2rem] items-center gap-2 px-3 py-1.5">
                  <Input value={row.item_name} onChange={(e) => updateExam(i, { item_name: e.target.value })} placeholder="如 胸部CT平扫" />
                  <div className="space-y-1">
                    <Input value={row.finding} onChange={(e) => updateExam(i, { finding: e.target.value })} placeholder="检查所见" />
                    <Input value={row.conclusion} onChange={(e) => updateExam(i, { conclusion: e.target.value })} placeholder="结论/诊断意见" />
                  </div>
                  <Button variant="ghost" size="icon" className="h-8 w-8"
                    onClick={() => setExams((rows) => rows.filter((_, j) => j !== i))}>
                    <Trash2 className="h-4 w-4 text-muted-foreground" />
                  </Button>
                </div>
              ))}
              {exams.length === 0 && (
                <div className="px-3 py-3 text-sm text-muted-foreground">暂无检查（可点击下方添加）</div>
              )}
            </div>
          </div>
          <Button type="button" variant="outline" size="sm"
            onClick={() => setExams((rows) => [...rows, { ...EMPTY_EXAM }])}>
            <Plus className="h-4 w-4" /> 添加检查
          </Button>
        </CardContent>
      </Card>

      {/* 保存栏 */}
      <div className="fixed inset-x-0 bottom-0 border-t bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-8 py-3">
          <p className="text-sm text-muted-foreground">
            已填写 {herbs.filter((h) => h.herb_name.trim()).length} 味药
          </p>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate(-1)}>取消</Button>
            <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
              {mutation.isPending ? "保存中…" : "保存病案"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
