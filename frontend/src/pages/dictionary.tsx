import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Pencil, Plus, Trash2 } from "lucide-react"
import { useEffect, useState } from "react"
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
import type { FormulaOption, HerbOption, SyndromeOption, TermOption } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"

type TabKey = "herb" | "syndrome" | "term" | "formula"

const TABS: { key: TabKey; label: string }[] = [
  { key: "herb", label: "药名" },
  { key: "syndrome", label: "证型" },
  { key: "term", label: "术语" },
  { key: "formula", label: "方剂" },
]

const TERM_TYPE: Record<number, string> = { 1: "舌质", 2: "舌苔", 3: "脉象" }

export function Dictionary() {
  const [tab, setTab] = useState<TabKey>("herb")
  const [q, setQ] = useState("")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<{ id: string } | null>(null)
  const queryClient = useQueryClient()

  const herbs = useQuery({ queryKey: ["dict-herbs", q], queryFn: () => fetchHerbs(q), enabled: tab === "herb" })
  const syndromes = useQuery({ queryKey: ["dict-syndromes", q], queryFn: () => fetchSyndromes(q), enabled: tab === "syndrome" })
  const terms = useQuery({ queryKey: ["dict-terms", q], queryFn: () => fetchAllTerms(q), enabled: tab === "term" })
  const formulas = useQuery({ queryKey: ["dict-formulas", q], queryFn: () => fetchFormulas(q), enabled: tab === "formula" })

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["dict-herbs"] })
    void queryClient.invalidateQueries({ queryKey: ["dict-syndromes"] })
    void queryClient.invalidateQueries({ queryKey: ["dict-terms"] })
    void queryClient.invalidateQueries({ queryKey: ["dict-formulas"] })
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">字典维护</h2>
          <p className="text-sm text-muted-foreground">维护药名、证型、术语与方剂，影响录入联想与统计口径。</p>
        </div>
        <Button onClick={() => { setEditing(null); setDialogOpen(true) }}>
          <Plus className="h-4 w-4" /> 添加
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`rounded-full border px-3 py-1 text-sm transition-colors ${tab === t.key ? "border-primary bg-primary text-primary-foreground" : "hover:bg-muted"}`}>
            {t.label}
          </button>
        ))}
        <div className="ml-auto">
          <Input className="w-52" placeholder="搜索…" value={q}
            onChange={(e) => setQ(e.target.value)} />
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                {tab === "herb" && <><TableHead>药名</TableHead><TableHead>拼音</TableHead><TableHead>类别</TableHead><TableHead>炮制</TableHead><TableHead className="w-28">操作</TableHead></>}
                {tab === "syndrome" && <><TableHead>证型</TableHead><TableHead>辨证体系</TableHead><TableHead className="w-28">操作</TableHead></>}
                {tab === "term" && <><TableHead>术语</TableHead><TableHead>类型</TableHead><TableHead>说明</TableHead><TableHead className="w-28">操作</TableHead></>}
                {tab === "formula" && <><TableHead>方剂</TableHead><TableHead>出处</TableHead><TableHead className="w-28">操作</TableHead></>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {tab === "herb" && herbs.data?.map((h: HerbOption) => (
                <TableRow key={h.herb_id}>
                  <TableCell className="font-medium">{h.herb_name}</TableCell>
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
                  <TableCell className="font-medium">{s.syndrome_name}</TableCell>
                  <TableCell>{s.category || "—"}</TableCell>
                  <TableCell>
                    <RowActions onEdit={() => openEdit("syndrome", s.syndrome_id)} onDelete={() => delSyndrome(s.syndrome_id)} />
                  </TableCell>
                </TableRow>
              ))}
              {tab === "term" && terms.data?.map((t: TermOption) => (
                <TableRow key={t.term_id}>
                  <TableCell className="font-medium">{t.term}</TableCell>
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
            </TableBody>
          </Table>
        </CardContent>
      </Card>

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
    setTab(key)
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

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}{required && <span className="ml-0.5 text-destructive">*</span>}</Label>
      {children}
    </div>
  )
}
