import { Construction } from "lucide-react"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export function Placeholder({ title }: { title: string }) {
  return (
    <div className="mx-auto max-w-6xl p-8">
      <Card className="border-dashed">
        <CardHeader className="items-center text-center">
          <Construction className="h-8 w-8 text-muted-foreground" />
          <CardTitle>{title}</CardTitle>
          <CardDescription>
            该模块界面正在设计中，随后实现。
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center text-sm text-muted-foreground">
          参见界面设计方案中关于「{title}」的规格说明。
        </CardContent>
      </Card>
    </div>
  )
}
