import { Outlet } from "react-router-dom"

import { Header } from "./header"
import { Sidebar } from "./sidebar"

export function AppShell() {
  return (
    <div className="flex h-full w-full">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
