import { NavLink } from "react-router-dom"

import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { NAV_GROUPS } from "./nav-config"

export function Sidebar() {
  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r bg-white">
      {/* 品牌区 */}
      <div className="flex h-16 items-center gap-3 border-b px-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <span className="font-serif text-base font-bold">案</span>
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold leading-tight tracking-wide">
            CASE
          </span>
          <span className="text-xs text-muted-foreground">
            中医跟诊病案
          </span>
        </div>
      </div>

      {/* 导航 */}
      <ScrollArea className="flex-1">
        <nav className="flex flex-col gap-5 px-3 py-4">
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <div className="px-3 pb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {group.label}
              </div>
              <div className="flex flex-col gap-0.5">
                {group.items.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      cn(
                        "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                        isActive
                          ? "bg-primary/10 text-primary"
                          : "text-foreground/80 hover:bg-muted hover:text-foreground",
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <item.icon
                          className={cn(
                            "h-4 w-4 shrink-0",
                            isActive
                              ? "text-primary"
                              : "text-muted-foreground group-hover:text-foreground",
                          )}
                        />
                        {item.title}
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>
      </ScrollArea>

      {/* 底部状态 */}
      <div className="border-t px-5 py-4">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="inline-block h-2 w-2 rounded-full bg-success" />
          本地数据 · SQLite
        </div>
        <div className="mt-1.5 flex items-center gap-2 text-xs text-muted-foreground">
          <span className="inline-block h-2 w-2 rounded-full bg-warning" />
          AI 未配置 API Key
        </div>
      </div>
    </aside>
  )
}
