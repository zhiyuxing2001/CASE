import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { Toaster } from "sonner"

import { AppShell } from "@/components/layout/app-shell"
import { TooltipProvider } from "@/components/ui/tooltip"
import { CaseEntry } from "@/pages/case-entry"
import { Cases } from "@/pages/cases"
import { Dashboard } from "@/pages/dashboard"
import { Placeholder } from "@/pages/placeholder"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={200}>
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/cases" element={<Cases />} />
              <Route path="/cases/new" element={<CaseEntry />} />
              <Route
                path="/intake"
                element={<Placeholder title="导入校对" />}
              />
              <Route
                path="/learning"
                element={<Placeholder title="跟师学习" />}
              />
              <Route
                path="/assistant"
                element={<Placeholder title="AI 助手" />}
              />
              <Route
                path="/dictionary"
                element={<Placeholder title="字典维护" />}
              />
              <Route
                path="/admin"
                element={<Placeholder title="数据管理" />}
              />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster richColors position="top-center" />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
