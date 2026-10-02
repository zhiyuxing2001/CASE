import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { ImagePlus, Loader2, UploadCloud } from "lucide-react"

import { createOcrJob, uploadImage } from "@/api/ocr"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

export function Intake() {
  const navigate = useNavigate()
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState(false)

  async function handleFile(file: File | undefined | null) {
    if (!file) return
    if (!file.type.startsWith("image/")) {
      toast.error("请选择图片文件")
      return
    }
    setBusy(true)
    try {
      const upload = await uploadImage(file)
      if (upload.quality.blurry) {
        toast.warning("图片可能模糊，建议重拍；已继续识别")
      }
      const job = await createOcrJob(upload.attach_id)
      navigate(`/intake/${job.job_id}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "识别失败")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-8">
      <div className="mb-6">
        <h2 className="text-xl font-semibold tracking-tight">导入处方 / 病历</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          拍照或选择图片，本地 macOS Vision 识别文字，随后人工校对入库。
        </p>
      </div>

      <Card>
        <CardContent className="p-0">
          <label
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-16 text-center transition-colors",
              dragging ? "border-primary bg-primary/5" : "border-border hover:bg-muted/50",
            )}
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files?.[0]) }}
          >
            <input
              type="file"
              accept="image/*"
              className="hidden"
              disabled={busy}
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
            {busy ? (
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
            ) : (
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
                <UploadCloud className="h-7 w-7 text-primary" />
              </div>
            )}
            <div className="text-sm font-medium">
              {busy ? "正在识别…" : "拖拽图片到这里，或点击选择"}
            </div>
            <div className="text-xs text-muted-foreground">
              支持 JPEG / PNG / WebP，原始图片仅保存在本机
            </div>
          </label>
        </CardContent>
      </Card>

      <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
        <ImagePlus className="h-4 w-4" />
        识别由 macOS Vision 本地完成；AI 结构化识别需在设置中配置 API Key。
      </div>
    </div>
  )
}
