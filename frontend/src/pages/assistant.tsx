import { useMutation, useQuery } from "@tanstack/react-query"
import { Bot, Loader2, PenLine, Send, Sparkles } from "lucide-react"
import { useState } from "react"
import ReactMarkdown from "react-markdown"
import { Link } from "react-router-dom"
import remarkGfm from "remark-gfm"
import { toast } from "sonner"

import { askQuestion, draftNote, fetchAiStatus, polishText } from "@/api/ai"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"

type TabKey = "qa" | "write"

export function Assistant() {
  const [tab, setTab] = useState<TabKey>("qa")
  const { data: status } = useQuery({ queryKey: ["ai-status"], queryFn: fetchAiStatus })

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
            <Sparkles className="h-5 w-5 text-ai" /> AI 助手
          </h2>
          <p className="text-sm text-muted-foreground">带出处的病案问答与写作辅助。</p>
        </div>
        <Badge variant={status?.configured ? "success" : "warning"}>
          {status?.configured ? `已配置 · ${status.model}` : "未配置 API Key"}
        </Badge>
      </div>

      {!status?.configured && (
        <Card className="border-warning/50 bg-warning/5">
          <CardContent className="p-4 text-sm">
            尚未配置 DeepSeek API Key（见 <code className="rounded bg-muted px-1">.env</code> 的{" "}
            <code className="rounded bg-muted px-1">DEEPSEEK_API_KEY</code>）。
            病案问答将降级为<b>仅返回检索到的相关病案</b>，写作辅助暂不可用；其余功能完全不受影响。
          </CardContent>
        </Card>
      )}

      <div className="flex gap-2">
        <TabChip active={tab === "qa"} onClick={() => setTab("qa")} icon={<Bot className="h-4 w-4" />}>病案问答</TabChip>
        <TabChip active={tab === "write"} onClick={() => setTab("write")} icon={<PenLine className="h-4 w-4" />}>写作辅助</TabChip>
      </div>

      {tab === "qa" ? <QaPanel configured={status?.configured ?? false} /> : <WritePanel configured={status?.configured ?? false} />}
    </div>
  )
}

function QaPanel({ configured }: { configured: boolean }) {
  const [question, setQuestion] = useState("")
  const [result, setResult] = useState<{ answer: string; sources: Awaited<ReturnType<typeof askQuestion>>["sources"]; degraded: boolean } | null>(null)

  const ask = useMutation({
    mutationFn: () => askQuestion(question),
    onSuccess: (r) => setResult({ answer: r.answer, sources: r.sources, degraded: r.degraded }),
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-2">
            <Textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="例如：湿热瘀阻证在老师病案里常用哪些治法？"
              rows={2}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && question.trim()) ask.mutate()
              }}
            />
            <Button className="self-end" disabled={!question.trim() || ask.isPending} onClick={() => ask.mutate()}>
              {ask.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              提问
            </Button>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">⌘/Ctrl + Enter 发送</p>
        </CardContent>
      </Card>

      {result && (
        <div className="space-y-4">
          {result.answer && (
            <Card>
              <CardContent className="p-4">
                <div className="prose-sm max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.answer}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          )}
          {result.degraded && configured && result.answer === "" && (
            <p className="text-sm text-muted-foreground">调用模型失败，以下为检索结果。</p>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">引用病案（{result.sources.length}）</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {result.sources.length === 0 ? (
                <p className="text-sm text-muted-foreground">未检索到相关病案。</p>
              ) : (
                result.sources.map((s) => (
                  <Link key={s.record_id} to={`/cases/${s.record_id}`} className="block">
                    <div className="rounded-md border p-3 transition-colors hover:bg-muted/50">
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium">{s.patient_name}</span>
                        <span className="text-xs text-muted-foreground">{s.clinic_date}</span>
                        <Badge variant="outline">{s.syndrome || "无证型"}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {s.complaint ? `主诉：${s.complaint}　` : ""}
                      </p>
                      <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{s.snippet}</p>
                    </div>
                  </Link>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

function WritePanel({ configured }: { configured: boolean }) {
  const [topic, setTopic] = useState("")
  const [draft, setDraft] = useState("")
  const [polishInput, setPolishInput] = useState("")
  const [polishOut, setPolishOut] = useState("")

  const draftMutation = useMutation({
    mutationFn: () => draftNote(topic),
    onSuccess: (r) => { if (r.text) setDraft(r.text); else toast.warning("AI 未配置，无法生成初稿") },
    onError: (e: Error) => toast.error(e.message),
  })
  const polishMutation = useMutation({
    mutationFn: () => polishText(polishInput),
    onSuccess: (r) => { if (r.text) setPolishOut(r.text); else toast.warning("AI 未配置，无法润色") },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">心得初稿</CardTitle>
          <CardDescription>输入主题，生成 Markdown 初稿，可复制到「跟师学习」。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Textarea value={topic} onChange={(e) => setTopic(e.target.value)}
            placeholder="如：湿热瘀阻证的辨治要点" rows={3} />
          <Button disabled={!topic.trim() || !configured || draftMutation.isPending} onClick={() => draftMutation.mutate()}>
            {draftMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            生成初稿
          </Button>
          {draft && (
            <div className="prose-sm max-h-80 max-w-none overflow-auto rounded-md border p-3">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{draft}</ReactMarkdown>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">润色</CardTitle>
          <CardDescription>把心得润色得更专业、条理清晰。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Textarea value={polishInput} onChange={(e) => setPolishInput(e.target.value)}
            placeholder="粘贴需要润色的文字…" rows={6} />
          <Button disabled={!polishInput.trim() || !configured || polishMutation.isPending} onClick={() => polishMutation.mutate()}>
            {polishMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <PenLine className="h-4 w-4" />}
            润色
          </Button>
          {polishOut && (
            <div className="prose-sm max-h-80 max-w-none overflow-auto rounded-md border p-3">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{polishOut}</ReactMarkdown>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function TabChip({ active, onClick, icon, children }: { active: boolean; onClick: () => void; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <button onClick={onClick}
      className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm transition-colors ${active ? "border-primary bg-primary text-primary-foreground" : "hover:bg-muted"}`}>
      {icon}{children}
    </button>
  )
}
