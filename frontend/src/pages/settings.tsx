import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Eye, EyeOff, KeyRound, Loader2, ShieldAlert, Trash2 } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { clearAiKey, fetchAiSettings, saveAiSettings } from "@/api/settings"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export function Settings() {
  const queryClient = useQueryClient()
  const [apiKey, setApiKey] = useState("")
  const [baseUrl, setBaseUrl] = useState("https://api.deepseek.com")
  const [model, setModel] = useState("deepseek-flash")
  const [showKey, setShowKey] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ["ai-settings"],
    queryFn: fetchAiSettings,
  })

  const save = useMutation({
    mutationFn: () => saveAiSettings({
      api_key: apiKey.trim() || undefined,
      base_url: baseUrl.trim() || undefined,
      model: model.trim() || undefined,
    }),
    onSuccess: (res) => {
      toast.success(res.configured ? "已保存并生效" : "已保存（未填 Key，AI 保持降级）")
      setApiKey("")
      void queryClient.invalidateQueries({ queryKey: ["ai-settings"] })
      void queryClient.invalidateQueries({ queryKey: ["ai-status"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const clear = useMutation({
    mutationFn: clearAiKey,
    onSuccess: () => {
      toast.success("已清除 API Key")
      void queryClient.invalidateQueries({ queryKey: ["ai-settings"] })
      void queryClient.invalidateQueries({ queryKey: ["ai-status"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-8">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">设置</h2>
        <p className="text-sm text-muted-foreground">配置 DeepSeek API，启用 AI 问答、写作辅助与 OCR 结构化。</p>
      </div>

      {/* 当前状态 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <KeyRound className="h-4 w-4" /> 当前状态
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">加载中…</p>
          ) : (
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <Badge variant={data?.configured ? "success" : "warning"}>
                  {data?.configured ? "已配置" : "未配置"}
                </Badge>
                {data?.configured && (
                  <span className="text-muted-foreground">Key：{data.api_key_masked}</span>
                )}
              </div>
              <p>模型：<span className="font-mono">{data?.model || "—"}</span></p>
              <p>接口地址：<span className="font-mono">{data?.base_url || "—"}</span></p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 配置表单 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">API Key</CardTitle>
          <CardDescription>保存后立即生效，无需重启；Key 仅存于本机数据库，永不回显明文。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>DeepSeek API Key</Label>
            <div className="relative">
              <Input
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-…"
                className="pr-10 font-mono"
              />
              <button
                type="button"
                onClick={() => setShowKey((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>接口地址</Label>
              <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} className="font-mono" />
            </div>
            <div className="space-y-1.5">
              <Label>模型</Label>
              <Input value={model} onChange={(e) => setModel(e.target.value)} className="font-mono" />
            </div>
          </div>

          <div className="flex gap-2">
            <Button onClick={() => save.mutate()} disabled={save.isPending}>
              {save.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              保存
            </Button>
            {data?.configured && (
              <Button variant="outline" onClick={() => clear.mutate()} disabled={clear.isPending}>
                <Trash2 className="h-4 w-4" /> 清除 Key
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 隐私提示 */}
      <Card className="border-warning/50 bg-warning/5">
        <CardContent className="flex items-start gap-3 p-4">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
          <div className="text-sm">
            <p className="font-medium">隐私提示</p>
            <p className="mt-1 text-muted-foreground">
              Key 只保存在本机数据库（<code className="rounded bg-muted px-1">data/case.db</code>，已排除出版本控制）。
              使用 AI 问答或 OCR 结构化时，相关病案片段/图片会发送至 DeepSeek API；纯本地功能（录入、检索、本地 OCR、备份）不涉及任何联网。
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
