import { useMutation, useQuery } from "@tanstack/react-query"
import { ArrowLeft, Copy, Info, Loader2 } from "lucide-react"
import { useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { toast } from "sonner"

import { commitOcrJob, fetchOcrJob, type OcrCommitPayload } from "@/api/ocr"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

const CONFIDENT = 0.6

export function OcrReview() {
  const { jobId = "" } = useParams()
  const navigate = useNavigate()
  const [selected, setSelected] = useState<number | null>(null)

  const [patientName, setPatientName] = useState("")
  const [gender, setGender] = useState("0")
  const [birthday, setBirthday] = useState("")
  const [clinicDate, setClinicDate] = useState(new Date().toISOString().slice(0, 10))
  const [complaint, setComplaint] = useState("")
  const [presentIllness, setPresentIllness] = useState("")

  const { data: job, isLoading, isError } = useQuery({
    queryKey: ["ocr-job", jobId],
    queryFn: () => fetchOcrJob(jobId),
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

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-8">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/intake"><ArrowLeft className="h-4 w-4" /> 重新上传</Link>
        </Button>
        <div className="flex gap-2">
          {job.degraded_mode === 1 && (
            <Badge variant="warning">仅本地识别（AI 未配置）</Badge>
          )}
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
                      left: `${x * 100}%`,
                      top: `${y * 100}%`,
                      width: `${w * 100}%`,
                      height: `${h * 100}%`,
                    }}
                  />
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* 右：识别文本 + 校对 */}
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
              <div className="space-y-1.5">
                <Label>主诉</Label>
                <Input value={complaint} onChange={(e) => setComplaint(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label>现病史</Label>
                <Textarea rows={3} value={presentIllness} onChange={(e) => setPresentIllness(e.target.value)} />
              </div>
              <Button
                className="w-full"
                disabled={commit.isPending}
                onClick={() => commit.mutate({
                  patient_name: patientName, gender: gender === "1",
                  birthday, clinic_date: clinicDate, complaint, present_illness: presentIllness,
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
