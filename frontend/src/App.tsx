import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { Toaster } from "sonner"

import { AppShell } from "@/components/layout/app-shell"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Admin } from "@/pages/admin"
import { Analytics } from "@/pages/analytics"
import { CaseDetail } from "@/pages/case-detail"
import { CaseEntry } from "@/pages/case-entry"
import { CaseReview } from "@/pages/case-review"
import { Cases } from "@/pages/cases"
import { Dashboard } from "@/pages/dashboard"
import { Dictionary } from "@/pages/dictionary"
import { Intake } from "@/pages/intake"
import { Learning } from "@/pages/learning"
import { LearningStats } from "@/pages/learning-stats"
import { MentorDetail } from "@/pages/mentor-detail"
import { Mentors } from "@/pages/mentors"
import { NoteEditor } from "@/pages/note-editor"
import { OcrReview } from "@/pages/ocr-review"
import { Settings } from "@/pages/settings"

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
              <Route path="/cases/:recordId/edit" element={<CaseEntry />} />
              <Route path="/cases/:recordId/review" element={<CaseReview />} />
              <Route path="/cases/:recordId" element={<CaseDetail />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/intake" element={<Intake />} />
              <Route path="/intake/:jobId" element={<OcrReview />} />
              <Route path="/learning" element={<Learning />} />
              <Route path="/learning/stats" element={<LearningStats />} />
              <Route path="/learning/new" element={<NoteEditor />} />
              <Route path="/learning/:noteId" element={<NoteEditor />} />
              <Route path="/mentors" element={<Mentors />} />
              <Route path="/mentors/:mentorId" element={<MentorDetail />} />
              <Route path="/dictionary" element={<Dictionary />} />
              <Route path="/admin" element={<Admin />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster richColors position="top-center" />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
