import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { CheckCircle2, Database, Download, RefreshCw, ShieldCheck, XCircle } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import {
  createBackup,
  fetchAudit,
  fetchBackups,
  fetchStats,
  runCheck,
} from "@/api/admin"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

const ACTION_CN: Record<number, string> = { 0: "新增", 1: "修改", 2: "删除", 3: "恢复", 4: "脱敏" }

function fmtBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function Admin() {
  const queryClient = useQueryClient()
  const [auditPage, setAuditPage] = useState(1)

  const stats = useQuery({ queryKey: ["admin-stats"], queryFn: fetchStats })
  const backups = useQuery({ queryKey: ["admin-backups"], queryFn: fetchBackups })
  const audit = useQuery({ queryKey: ["admin-audit", auditPage], queryFn: () => fetchAudit(auditPage, 50) })

  const backup = useMutation({
    mutationFn: createBackup,
    onSuccess: (res) => {
      toast.success(`已备份（${fmtBytes(res.size)}）`)
      void queryClient.invalidateQueries({ queryKey: ["admin-backups"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const check = useMutation({
    mutationFn: runCheck,
    onSuccess: () => toast.success("完整性自检完成"),
    onError: (e: Error) => toast.error(e.message),
  })

  const totalRows = stats.data?.tables.reduce((sum, t) => sum + t.rows, 0) ?? 0

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-8">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">数据管理</h2>
        <p className="text-sm text-muted-foreground">数据库统计、备份、审计与完整性自检。</p>
      </div>

      {/* 概览 */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard icon={<Database className="h-4 w-4" />} label="数据表" value={stats.data?.tables.length ?? 0} />
        <StatCard icon={<RefreshCw className="h-4 w-4" />} label="总记录行" value={totalRows} />
        <StatCard icon={<Download className="h-4 w-4" />} label="备份文件" value={backups.data?.length ?? 0} />
        <StatCard icon={<ShieldCheck className="h-4 w-4" />} label="数据库大小" value={fmtBytes(stats.data?.database_size ?? 0)} />
      </div>

      {/* 备份 + 自检 */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">备份</CardTitle>
            <CardDescription>将当前数据库快照写入 data/backups/。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button onClick={() => backup.mutate()} disabled={backup.isPending}>
              <Download className="h-4 w-4" /> 立即备份
            </Button>
            {backups.data && backups.data.length > 0 && (
              <div className="space-y-1">
                {backups.data.slice(0, 6).map((b) => (
                  <div key={b.name} className="flex items-center justify-between text-sm">
                    <span className="font-mono">{b.name}</span>
                    <span className="text-muted-foreground">{fmtBytes(b.size)} · {b.created_at}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">完整性自检</CardTitle>
            <CardDescription>检查外键一致性。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button variant="outline" onClick={() => check.mutate()} disabled={check.isPending}>
              <ShieldCheck className="h-4 w-4" /> 运行自检
            </Button>
            {check.data && (
              <div className="space-y-1 text-sm">
                <div className="flex items-center gap-2">
                  {check.data.ok ? (
                    <CheckCircle2 className="h-4 w-4 text-success" />
                  ) : (
                    <XCircle className="h-4 w-4 text-destructive" />
                  )}
                  <span>外键不一致 {check.data.foreign_key_violations} 处</span>
                </div>
                {check.data.messages.slice(1).map((m, i) => (
                  <p key={i} className="text-xs text-muted-foreground">{m}</p>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 审计日志 */}
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base">审计日志</CardTitle>
          <div className="flex items-center gap-2">
            {audit.data && audit.data.total > 0 && (
              <span className="text-xs text-muted-foreground">共 {audit.data.total} 条</span>
            )}
            <Button variant="ghost" size="sm" disabled={auditPage <= 1}
              onClick={() => setAuditPage((p) => p - 1)}>上一页</Button>
            <Button variant="ghost" size="sm" onClick={() => setAuditPage((p) => p + 1)}>下一页</Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-44">时间</TableHead>
                <TableHead className="w-28">表</TableHead>
                <TableHead className="w-20">操作</TableHead>
                <TableHead className="w-32">字段</TableHead>
                <TableHead>变更</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {!audit.data || audit.data.items.length === 0 ? (
                <TableRow><TableCell colSpan={5} className="py-8 text-center text-muted-foreground">暂无审计记录</TableCell></TableRow>
              ) : (
                audit.data.items.map((e, i) => (
                  <TableRow key={i}>
                    <TableCell className="tabular-nums text-muted-foreground">{e.changed_at}</TableCell>
                    <TableCell><Badge variant="outline">{e.table_name}</Badge></TableCell>
                    <TableCell><Badge variant="secondary">{ACTION_CN[e.action] ?? e.action}</Badge></TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{e.field_name || "—"}</TableCell>
                    <TableCell className="max-w-[28rem] truncate">
                      {e.old_value && <span className="text-muted-foreground line-through">{e.old_value}</span>}
                      {e.old_value && e.new_value && " → "}
                      {e.new_value && <span>{e.new_value}</span>}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 表统计 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">数据表统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
            {stats.data?.tables.map((t) => (
              <div key={t.table} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                <span className="font-mono text-xs">{t.table}</span>
                <span className="tabular-nums text-muted-foreground">{t.rows}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
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
