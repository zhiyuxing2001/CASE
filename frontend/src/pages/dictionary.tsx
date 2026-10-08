import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Pencil, Plus, Trash2 } from "lucide-react"
import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { toast } from "sonner"

import {
  createFormula,
  createHerb,
  createSyndrome,
  createTerm,
  deleteFormula,
  deleteHerb,
  deleteSyndrome,
  deleteTerm,
  fetchFormulaDetail,
  fetchHerbDetail,
  fetchSyndromeDetail,
  fetchTermDetail,
  updateFormula,
  updateHerb,
  updateSyndrome,
  updateTerm,
  type FormulaUpsertPayload,
  type HerbUpsertPayload,
  type SyndromeUpsertPayload,
  type TermUpsertPayload,
} from "@/api/admin"
import { fetchFormulas, fetchHerbs, fetchSyndromes } from "@/api/cases"
import {
  fetchPrompts,
  resetPrompt,
  updatePrompt,
  type Prompt,
} from "@/api/prompts"
import {
  createTemplate,
  deleteTemplate,
  updateTemplate,
  fetchTemplates,
  fetchTemplateDetail,
  FIELD_CATALOG,
  TABLE_FIELDS,
  DOC_TYPES,
  type Template,
  type TemplateAnchor,
} from "@/api/templates"
import type { FormulaOption, HerbOption, SyndromeOption, TermOption } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"

type TabKey = "herb" | "syndrome" | "term" | "formula" | "template" | "prompt"

const TABS: { key: TabKey; label: string }[] = [
  { key: "herb", label: "药名" },
  { key: "syndrome", label: "证型" },
  { key: "term", label: "术语" },
  { key: "formula", label: "方剂" },
  { key: "template", label: "界面模板" },
  { key: "prompt", label: "提示词" },
]

const TERM_TYPE: Record<number, string> = { 1: "舌质", 2: "舌苔", 3: "脉象", 6: "煎服法", 11: "特殊煎煮法" }

export function Dictionary() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTab = searchParams.get("tab")
  const [tab, setTab] = useState<TabKey>(
    TABS.some((t) => t.key === initialTab) ? (initialTab as TabKey) : "herb",
  )

  // 当 URL 的 tab 参数变化时同步（支持快捷操作直达某个标签页）
  useEffect(() => {
    const p = searchParams.get("tab")
    if (p && TABS.some((t) => t.key === p)) {
      setTab(p as TabKey)
    }
  }, [searchParams])

  function selectTab(key: TabKey) {
    setTab(key)
    setSearchParams(key === "herb" ? {} : { tab: key }, { replace: true })
  }
  const [q, setQ] = useState("")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<{ id: string } | null>(null)
  const queryClient = useQueryClient()

  const herbs = useQuery({ queryKey: ["dict-herbs", q], queryFn: () => fetchHerbs(q), enabled: tab === "herb" })
  const syndromes = useQuery({ queryKey: ["dict-syndromes", q], queryFn: () => fetchSyndromes(q), enabled: tab === "syndrome" })
  const terms = useQuery({ queryKey: ["dict-terms", q], queryFn: () => fetchAllTerms(q), enabled: tab === "term" })
  const formulas = useQuery({ queryKey: ["dict-formulas", q], queryFn: () => fetchFormulas(q), enabled: tab === "formula" })
  const templates = useQuery({ queryKey: ["dict-templates"], queryFn: fetchTemplates, enabled: tab === "template" })
  const prompts = useQuery({ queryKey: ["prompts"], queryFn: fetchPrompts, enabled: tab === "prompt" })

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["dict-herbs"] })
    void queryClient.invalidateQueries({ queryKey: ["dict-syndromes"] })
    void queryClient.invalidateQueries({ queryKey: ["dict-terms"] })
    void queryClient.invalidateQueries({ queryKey: ["dict-formulas"] })
    void queryClient.invalidateQueries({ queryKey: ["dict-templates"] })
    void queryClient.invalidateQueries({ queryKey: ["prompts"] })
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">字典维护</h2>
          <p className="text-sm text-muted-foreground">维护药名、证型、术语、方剂、界面模板与提示词，影响录入联想与识别统计。</p>
        </div>
        {tab !== "prompt" && (
          <Button onClick={() => { setEditing(null); setDialogOpen(true) }}>
            <Plus className="h-4 w-4" /> 添加
          </Button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => selectTab(t.key)}
            className={`rounded-full border px-3 py-1 text-sm transition-colors ${tab === t.key ? "border-primary bg-primary text-primary-foreground" : "hover:bg-muted"}`}>
            {t.label}
          </button>
        ))}
        {tab !== "template" && tab !== "prompt" && (
          <div className="ml-auto">
            <Input className="w-52" placeholder="搜索…" value={q}
              onChange={(e) => setQ(e.target.value)} />
          </div>
        )}
      </div>

      {tab === "prompt" ? (
        <PromptPanel prompts={prompts.data ?? []} onChanged={invalidate} />
      ) : (
        <Card>
          <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                {tab === "herb" && <><TableHead>药名</TableHead><TableHead>拼音</TableHead><TableHead>类别</TableHead><TableHead>炮制</TableHead><TableHead className="w-28">操作</TableHead></>}
                {tab === "syndrome" && <><TableHead>证型</TableHead><TableHead>辨证体系</TableHead><TableHead className="w-28">操作</TableHead></>}
                {tab === "term" && <><TableHead>术语</TableHead><TableHead>类型</TableHead><TableHead>说明</TableHead><TableHead className="w-28">操作</TableHead></>}
                {tab === "formula" && <><TableHead>方剂</TableHead><TableHead>出处</TableHead><TableHead className="w-28">操作</TableHead></>}
                {tab === "template" && <><TableHead>模板名</TableHead><TableHead>单据类型</TableHead><TableHead>文字结构</TableHead><TableHead>表格列</TableHead><TableHead className="w-28">操作</TableHead></>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {tab === "herb" && herbs.data?.map((h: HerbOption) => (
                <TableRow key={h.herb_id}>
                  <TableCell className="font-medium">{h.herb_name}{h.is_auto && <Badge variant="outline" className="ml-1.5">自动</Badge>}</TableCell>
                  <TableCell className="text-muted-foreground">{h.pinyin || "—"}</TableCell>
                  <TableCell>{h.category || "—"}</TableCell>
                  <TableCell>{h.is_processed ? <Badge variant="secondary">炮制</Badge> : "—"}</TableCell>
                  <TableCell>
                    <RowActions onEdit={() => openEdit("herb", h.herb_id)} onDelete={() => delHerb(h.herb_id)} />
                  </TableCell>
                </TableRow>
              ))}
              {tab === "syndrome" && syndromes.data?.map((s: SyndromeOption) => (
                <TableRow key={s.syndrome_id}>
                  <TableCell className="font-medium">{s.syndrome_name}{s.is_auto && <Badge variant="outline" className="ml-1.5">自动</Badge>}</TableCell>
                  <TableCell>{s.category || "—"}</TableCell>
                  <TableCell>
                    <RowActions onEdit={() => openEdit("syndrome", s.syndrome_id)} onDelete={() => delSyndrome(s.syndrome_id)} />
                  </TableCell>
                </TableRow>
              ))}
              {tab === "term" && terms.data?.map((t: TermOption) => (
                <TableRow key={t.term_id}>
                  <TableCell className="font-medium">{t.term}{t.is_auto && <Badge variant="outline" className="ml-1.5">自动</Badge>}</TableCell>
                  <TableCell>{TERM_TYPE[t.term_type] ?? t.term_type}</TableCell>
                  <TableCell className="text-muted-foreground">{t.description || "—"}</TableCell>
                  <TableCell>
                    <RowActions onEdit={() => openEditTerm(t.term_id)} onDelete={() => delTerm(t.term_id)} />
                  </TableCell>
                </TableRow>
              ))}
              {tab === "formula" && formulas.data?.map((f: FormulaOption) => (
                <TableRow key={f.formula_id}>
                  <TableCell className="font-medium">{f.formula_name}</TableCell>
                  <TableCell className="text-muted-foreground">{f.source || "—"}</TableCell>
                  <TableCell>
                    <RowActions onEdit={() => openEdit("formula", f.formula_id)} onDelete={() => delFormula(f.formula_id)} />
                  </TableCell>
                </TableRow>
              ))}
              {tab === "template" && templates.data?.map((t: Template) => (
                <TableRow key={t.template_id}>
                  <TableCell className="font-medium">{t.name}</TableCell>
                  <TableCell><Badge variant="secondary">{DOC_TYPES[t.doc_type] ?? t.doc_type}</Badge></TableCell>
                  <TableCell className="text-muted-foreground">{t.field_anchors.length} 项</TableCell>
                  <TableCell className="text-muted-foreground">{t.table_columns.length} 项</TableCell>
                  <TableCell>
                    <RowActions onEdit={() => openEdit("template", t.template_id)} onDelete={() => delTemplate(t.template_id)} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
        </Card>
      )}

      <DictDialog
        tab={tab}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editingId={editing?.id ?? null}
        onSaved={invalidate}
      />
    </div>
  )

  function openEdit(key: TabKey, id: string) {
    selectTab(key)
    setEditing({ id })
    setDialogOpen(true)
  }
  function openEditTerm(termId: number) {
    setEditing({ id: String(termId) })
    setDialogOpen(true)
  }

  function delHerb(id: string) { void deleteHerb(id).then(invalidate) }
  function delSyndrome(id: string) { void deleteSyndrome(id).then(invalidate) }
  function delTerm(id: number) { void deleteTerm(id).then(invalidate) }
  function delFormula(id: string) { void deleteFormula(id).then(invalidate) }
  function delTemplate(id: string) { void deleteTemplate(id).then(invalidate) }
}

function RowActions({ onEdit, onDelete }: { onEdit: () => void; onDelete: () => void }) {
  return (
    <div className="flex gap-1">
      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onEdit}>
        <Pencil className="h-4 w-4" />
      </Button>
      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onDelete}>
        <Trash2 className="h-4 w-4 text-destructive" />
      </Button>
    </div>
  )
}

async function fetchAllTerms(q = ""): Promise<TermOption[]> {
  const res = await fetch(`/api/dict/terms${q ? `?q=${encodeURIComponent(q)}` : ""}`)
  if (!res.ok) throw new Error("加载术语失败")
  return res.json()
}

function DictDialog({
  tab,
  open,
  onOpenChange,
  editingId,
  onSaved,
}: {
  tab: TabKey
  open: boolean
  onOpenChange: (v: boolean) => void
  editingId: string | null
  onSaved: () => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {tab === "herb" && <HerbForm editingId={editingId} onSaved={onSaved} onClose={() => onOpenChange(false)} />}
        {tab === "syndrome" && <SyndromeForm editingId={editingId} onSaved={onSaved} onClose={() => onOpenChange(false)} />}
        {tab === "term" && <TermForm editingId={editingId} onSaved={onSaved} onClose={() => onOpenChange(false)} />}
        {tab === "formula" && <FormulaForm editingId={editingId} onSaved={onSaved} onClose={() => onOpenChange(false)} />}
        {tab === "template" && <TemplateForm editingId={editingId} onSaved={onSaved} onClose={() => onOpenChange(false)} />}
      </DialogContent>
    </Dialog>
  )
}

function HerbForm({ editingId, onSaved, onClose }: { editingId: string | null; onSaved: () => void; onClose: () => void }) {
  const [form, setForm] = useState<HerbUpsertPayload>({ herb_name: "" })
  const { data: detail } = useQuery({
    queryKey: ["herb-detail", editingId],
    queryFn: () => fetchHerbDetail(editingId!),
    enabled: Boolean(editingId),
  })
  useEffect(() => {
    if (detail && editingId) setForm(detail as HerbUpsertPayload)
  }, [detail, editingId])
  const save = useMutation({
    mutationFn: () => editingId ? updateHerb(editingId, form) : createHerb(form),
    onSuccess: () => { toast.success("已保存"); onSaved(); onClose() },
    onError: (e: Error) => toast.error(e.message),
  })
  return (
    <div>
      <DialogHeader><DialogTitle>{editingId ? "编辑药名" : "添加药名"}</DialogTitle></DialogHeader>
      <div className="grid grid-cols-2 gap-3 py-4">
        <Field label="药名" required><Input value={form.herb_name} onChange={(e) => setForm({ ...form, herb_name: e.target.value })} /></Field>
        <Field label="拼音"><Input value={form.pinyin ?? ""} onChange={(e) => setForm({ ...form, pinyin: e.target.value })} /></Field>
        <Field label="类别"><Input value={form.category ?? ""} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="如 清热药" /></Field>
        <Field label="四气"><Input value={form.nature ?? ""} onChange={(e) => setForm({ ...form, nature: e.target.value })} /></Field>
        <Field label="五味"><Input value={form.flavor ?? ""} onChange={(e) => setForm({ ...form, flavor: e.target.value })} /></Field>
        <Field label="归经"><Input value={form.meridians ?? ""} onChange={(e) => setForm({ ...form, meridians: e.target.value })} /></Field>
        <div className="col-span-2">
          <Field label="功效"><Input value={form.functions ?? ""} onChange={(e) => setForm({ ...form, functions: e.target.value })} /></Field>
        </div>
        <Field label="炮制方法"><Input value={form.processing ?? ""} onChange={(e) => setForm({ ...form, processing: e.target.value })} /></Field>
        <Field label="是否炮制品">
          <Select value={form.is_processed ? "1" : "0"} onValueChange={(v) => setForm({ ...form, is_processed: v === "1" })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="0">否</SelectItem><SelectItem value="1">是</SelectItem></SelectContent>
          </Select>
        </Field>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>取消</Button>
        <Button disabled={!form.herb_name.trim() || save.isPending} onClick={() => save.mutate()}>保存</Button>
      </DialogFooter>
    </div>
  )
}

function SyndromeForm({ editingId, onSaved, onClose }: { editingId: string | null; onSaved: () => void; onClose: () => void }) {
  const [form, setForm] = useState<SyndromeUpsertPayload>({ syndrome_name: "" })
  const { data: detail } = useQuery({
    queryKey: ["syndrome-detail", editingId],
    queryFn: () => fetchSyndromeDetail(editingId!),
    enabled: Boolean(editingId),
  })
  useEffect(() => {
    if (detail && editingId) setForm(detail as SyndromeUpsertPayload)
  }, [detail, editingId])
  const save = useMutation({
    mutationFn: () => editingId ? updateSyndrome(editingId, form) : createSyndrome(form),
    onSuccess: () => { toast.success("已保存"); onSaved(); onClose() },
    onError: (e: Error) => toast.error(e.message),
  })
  return (
    <div>
      <DialogHeader><DialogTitle>{editingId ? "编辑证型" : "添加证型"}</DialogTitle></DialogHeader>
      <div className="grid gap-3 py-4">
        <Field label="证型名称" required><Input value={form.syndrome_name} onChange={(e) => setForm({ ...form, syndrome_name: e.target.value })} /></Field>
        <Field label="辨证体系"><Input value={form.category ?? ""} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="如 脏腑辨证" /></Field>
        <Field label="主症要点"><Input value={form.key_symptoms ?? ""} onChange={(e) => setForm({ ...form, key_symptoms: e.target.value })} /></Field>
        <Field label="常用治法"><Input value={form.treatment ?? ""} onChange={(e) => setForm({ ...form, treatment: e.target.value })} /></Field>
        <Field label="代表方"><Input value={form.common_formula ?? ""} onChange={(e) => setForm({ ...form, common_formula: e.target.value })} /></Field>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>取消</Button>
        <Button disabled={!form.syndrome_name.trim() || save.isPending} onClick={() => save.mutate()}>保存</Button>
      </DialogFooter>
    </div>
  )
}

function TermForm({ editingId, onSaved, onClose }: { editingId: string | null; onSaved: () => void; onClose: () => void }) {
  const [form, setForm] = useState<TermUpsertPayload>({ term: "", term_type: 1 })
  const { data: detail } = useQuery({
    queryKey: ["term-detail", editingId],
    queryFn: () => fetchTermDetail(Number(editingId)) as Promise<Record<string, unknown>>,
    enabled: Boolean(editingId),
  })
  useEffect(() => {
    if (detail && editingId) {
      setForm({
        term: String(detail.term ?? ""),
        term_type: Number(detail.term_type ?? 1),
        description: String(detail.description ?? ""),
      })
    }
  }, [detail, editingId])
  const save = useMutation({
    mutationFn: () => editingId ? updateTerm(Number(editingId), form) : createTerm(form),
    onSuccess: () => { toast.success("已保存"); onSaved(); onClose() },
    onError: (e: Error) => toast.error(e.message),
  })
  return (
    <div>
      <DialogHeader><DialogTitle>{editingId ? "编辑术语" : "添加术语"}</DialogTitle></DialogHeader>
      <div className="grid gap-3 py-4">
        <Field label="术语" required><Input value={form.term} onChange={(e) => setForm({ ...form, term: e.target.value })} /></Field>
        <Field label="类型">
          <Select value={String(form.term_type)} onValueChange={(v) => setForm({ ...form, term_type: Number(v) })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="1">舌质</SelectItem>
              <SelectItem value="2">舌苔</SelectItem>
              <SelectItem value="3">脉象</SelectItem>
              <SelectItem value="6">煎服法</SelectItem>
              <SelectItem value="11">特殊煎煮法</SelectItem>
            </SelectContent>
          </Select>
        </Field>
        <Field label="说明"><Textarea value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>取消</Button>
        <Button disabled={!form.term.trim() || save.isPending} onClick={() => save.mutate()}>保存</Button>
      </DialogFooter>
    </div>
  )
}

function FormulaForm({ editingId, onSaved, onClose }: { editingId: string | null; onSaved: () => void; onClose: () => void }) {
  const [form, setForm] = useState<FormulaUpsertPayload>({ formula_name: "" })
  const { data: detail } = useQuery({
    queryKey: ["formula-detail", editingId],
    queryFn: () => fetchFormulaDetail(editingId!),
    enabled: Boolean(editingId),
  })
  useEffect(() => {
    if (detail && editingId) setForm(detail as FormulaUpsertPayload)
  }, [detail, editingId])
  const save = useMutation({
    mutationFn: () => editingId ? updateFormula(editingId, form) : createFormula(form),
    onSuccess: () => { toast.success("已保存"); onSaved(); onClose() },
    onError: (e: Error) => toast.error(e.message),
  })
  return (
    <div>
      <DialogHeader><DialogTitle>{editingId ? "编辑方剂" : "添加方剂"}</DialogTitle></DialogHeader>
      <div className="grid gap-3 py-4">
        <Field label="方剂名称" required><Input value={form.formula_name} onChange={(e) => setForm({ ...form, formula_name: e.target.value })} /></Field>
        <Field label="出处"><Input value={form.source ?? ""} onChange={(e) => setForm({ ...form, source: e.target.value })} placeholder="如 景岳全书" /></Field>
        <Field label="类别"><Input value={form.category ?? ""} onChange={(e) => setForm({ ...form, category: e.target.value })} /></Field>
        <Field label="功用"><Input value={form.functions ?? ""} onChange={(e) => setForm({ ...form, functions: e.target.value })} /></Field>
        <Field label="主治"><Input value={form.indications ?? ""} onChange={(e) => setForm({ ...form, indications: e.target.value })} /></Field>
        <Field label="组成"><Textarea value={form.composition_text ?? ""} onChange={(e) => setForm({ ...form, composition_text: e.target.value })} /></Field>
        <Field label="用法"><Input value={form.usage_text ?? ""} onChange={(e) => setForm({ ...form, usage_text: e.target.value })} /></Field>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>取消</Button>
        <Button disabled={!form.formula_name.trim() || save.isPending} onClick={() => save.mutate()}>保存</Button>
      </DialogFooter>
    </div>
  )
}

function Field({ label, required, hint, children }: { label: string; required?: boolean; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}{required && <span className="ml-0.5 text-destructive">*</span>}</Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

function AnchorEditor({
  anchors,
  onChange,
  options,
  placeholder,
}: {
  anchors: TemplateAnchor[]
  onChange: (anchors: TemplateAnchor[]) => void
  options: { field: string; label: string }[]
  placeholder: string
}) {
  function patch(i: number, p: Partial<TemplateAnchor>) {
    onChange(anchors.map((a, idx) => (idx === i ? { ...a, ...p } : a)))
  }
  function remove(i: number) {
    onChange(anchors.filter((_, idx) => idx !== i))
  }
  return (
    <div className="space-y-2">
      {anchors.map((a, i) => (
        <div key={i} className="flex gap-2">
          <Input
            className="flex-1"
            placeholder={placeholder}
            value={a.label}
            onChange={(e) => patch(i, { label: e.target.value })}
          />
          <Select value={a.field || "__none__"} onValueChange={(v) => patch(i, { field: v === "__none__" ? "" : v })}>
            <SelectTrigger className="w-44"><SelectValue placeholder="映射字段" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">选择字段…</SelectItem>
              {options.map((o) => (
                <SelectItem key={o.field} value={o.field}>{o.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0" onClick={() => remove(i)}>
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={() => onChange([...anchors, { label: "", field: "" }])}>
        <Plus className="h-4 w-4" /> 添加一项
      </Button>
    </div>
  )
}

function TemplateForm({ editingId, onSaved, onClose }: { editingId: string | null; onSaved: () => void; onClose: () => void }) {
  const [form, setForm] = useState({ name: "", doc_type: 0, field_anchors: [] as TemplateAnchor[], table_columns: [] as TemplateAnchor[] })
  const { data: detail } = useQuery({
    queryKey: ["template-detail", editingId],
    queryFn: () => fetchTemplateDetail(editingId!),
    enabled: Boolean(editingId),
  })
  useEffect(() => {
    if (detail && editingId) {
      setForm({
        name: detail.name,
        doc_type: detail.doc_type,
        field_anchors: detail.field_anchors,
        table_columns: detail.table_columns,
      })
    }
  }, [detail, editingId])
  const save = useMutation({
    mutationFn: () => editingId ? updateTemplate(editingId, form) : createTemplate(form),
    onSuccess: () => { toast.success("已保存"); onSaved(); onClose() },
    onError: (e: Error) => toast.error(e.message),
  })
  return (
    <div>
      <DialogHeader>
        <DialogTitle>{editingId ? "编辑界面模板" : "添加界面模板"}</DialogTitle>
      </DialogHeader>
      <div className="grid gap-3 py-4">
        <Field label="模板名" required>
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="如 HIS 病历界面" />
        </Field>
        <Field label="单据类型">
          <Select value={String(form.doc_type)} onValueChange={(v) => setForm({ ...form, doc_type: Number(v) })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="0">病历</SelectItem>
              <SelectItem value="1">医嘱/处方</SelectItem>
              <SelectItem value="2">其他</SelectItem>
            </SelectContent>
          </Select>
        </Field>
        <Field label="文字结构（标签 → 字段）" hint="如“主诉”映射到“主诉”；用于从 OCR 文本中按标签提取字段。">
          <AnchorEditor anchors={form.field_anchors} onChange={(a) => setForm({ ...form, field_anchors: a })} options={FIELD_CATALOG} placeholder="界面标签，如“主诉”" />
        </Field>
        <Field label="表格列（表头 → 字段）" hint="医嘱/处方表格的列名与字段映射，如“药名”映射到“药名”。">
          <AnchorEditor anchors={form.table_columns} onChange={(a) => setForm({ ...form, table_columns: a })} options={TABLE_FIELDS} placeholder="表头，如“药名”" />
        </Field>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>取消</Button>
        <Button disabled={!form.name.trim() || save.isPending} onClick={() => save.mutate()}>保存</Button>
      </DialogFooter>
    </div>
  )
}

function PromptPanel({ prompts, onChanged }: { prompts: Prompt[]; onChanged: () => void }) {
  if (prompts.length === 0) {
    return <p className="text-sm text-muted-foreground">加载中…</p>
  }
  return (
    <div className="space-y-4">
      {prompts.map((p) => (
        <PromptCard key={p.key} prompt={p} onChanged={onChanged} />
      ))}
    </div>
  )
}

function PromptCard({ prompt, onChanged }: { prompt: Prompt; onChanged: () => void }) {
  const [value, setValue] = useState(prompt.current)
  const dirty = value !== prompt.current

  const save = useMutation({
    mutationFn: () => updatePrompt(prompt.key, value),
    onSuccess: () => { toast.success("已保存"); onChanged() },
    onError: (e: Error) => toast.error(e.message),
  })
  const reset = useMutation({
    mutationFn: () => resetPrompt(prompt.key),
    onSuccess: () => { setValue(prompt.default); toast.success("已恢复默认"); onChanged() },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="text-base">{prompt.name}</CardTitle>
          <CardDescription>{prompt.description}</CardDescription>
        </div>
        {prompt.is_modified && <Badge variant="warning">已修改</Badge>}
      </CardHeader>
      <CardContent className="space-y-3">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          rows={10}
          className="font-mono text-sm leading-relaxed"
        />
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={() => reset.mutate()} disabled={!prompt.is_modified || reset.isPending}>
            恢复默认
          </Button>
          <Button size="sm" onClick={() => save.mutate()} disabled={!dirty || save.isPending}>
            保存
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
