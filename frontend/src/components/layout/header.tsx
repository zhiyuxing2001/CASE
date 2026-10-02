import { useLocation } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { NAV_TITLES } from "./nav-config"

export function Header() {
  const { pathname } = useLocation()
  const title = NAV_TITLES[pathname] ?? "CASE"

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b bg-white px-8">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
      </div>
      <div className="flex items-center gap-3">
        <Badge variant="success" className="gap-1">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-current" />
          数据正常
        </Badge>
        <Badge variant="outline">仅供学习参考</Badge>
      </div>
    </header>
  )
}
