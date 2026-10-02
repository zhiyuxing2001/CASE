import {
  ArrowRight,
  FileText,
  GraduationCap,
  ScanLine,
  Sparkles,
} from "lucide-react"
import { Link } from "react-router-dom"

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

// 临时 mock 数据，用于界面评审。接入后端后替换为真实查询。
const STATS = [
  { label: "待校对病案", value: 3, hint: "OCR 已识别，待人工确认", icon: ScanLine },
  { label: "病案总数", value: 128, hint: "本机累计收录", icon: FileText },
  { label: "学习心得", value: 24, hint: "已发布与草稿", icon: GraduationCap },
  { label: "跟诊次数", value: 37, hint: "本学期", icon: Sparkles },
]

const RECENT_CASES = [
  { date: "2026-06-09", complaint: "带状疱疹后遗神经痛3月", syndrome: "湿热瘀阻证", status: "confirmed" as const },
  { date: "2026-05-19", complaint: "服药后复诊", syndrome: "湿热瘀阻证", status: "confirmed" as const },
  { date: "2026-04-28", complaint: "服药后复诊", syndrome: "湿热瘀阻证", status: "draft" as const },
  { date: "2026-03-31", complaint: "带状疱疹后遗神经痛3月", syndrome: "湿热瘀阻证", status: "confirmed" as const },
]

const QUICK_ACTIONS = [
  { title: "录入新病案", desc: "手工录入或从图片识别", to: "/intake" },
  { title: "校对识别结果", desc: "有 3 份待确认", to: "/intake" },
  { title: "撰写学习心得", desc: "基于最近的病案", to: "/learning" },
  { title: "向 AI 提问", desc: "查阅经典与个人病案库", to: "/assistant" },
]

export function Dashboard() {
  return (
    <div className="mx-auto max-w-6xl space-y-6 p-8">
      {/* 欢迎区 */}
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">
          早上好，欢迎回来
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          最近有 3 份病案等待校对，4 份新增记录待回顾。
        </p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {STATS.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">
                  {stat.label}
                </span>
                <stat.icon className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="mt-2 text-3xl font-semibold tabular-nums">
                {stat.value}
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                {stat.hint}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* 最近病案 */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle>最近病案</CardTitle>
              <CardDescription>按就诊日期倒序</CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/cases">
                查看全部 <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {RECENT_CASES.map((c, i) => (
                <div key={i}>
                  <div className="flex items-center justify-between rounded-md px-2 py-2.5 hover:bg-muted">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">
                        {c.complaint}
                      </div>
                      <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="tabular-nums">{c.date}</span>
                        <span>·</span>
                        <span>{c.syndrome}</span>
                      </div>
                    </div>
                    <Badge
                      variant={c.status === "confirmed" ? "success" : "outline"}
                    >
                      {c.status === "confirmed" ? "已确认" : "草稿"}
                    </Badge>
                  </div>
                  {i < RECENT_CASES.length - 1 && <Separator />}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 快捷操作 */}
        <Card>
          <CardHeader>
            <CardTitle>快捷操作</CardTitle>
            <CardDescription>从这里开始</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {QUICK_ACTIONS.map((action) => (
              <Button
                key={action.title}
                variant="outline"
                className="h-auto w-full justify-start gap-3 px-3 py-3"
                asChild
              >
                <Link to={action.to}>
                  <div className="flex flex-col items-start text-left">
                    <span className="text-sm font-medium">{action.title}</span>
                    <span className="text-xs text-muted-foreground">
                      {action.desc}
                    </span>
                  </div>
                </Link>
              </Button>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
