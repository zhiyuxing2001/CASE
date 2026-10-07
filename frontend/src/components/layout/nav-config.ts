import {
  BarChart3,
  BookMarked,
  Database,
  FolderOpen,
  GraduationCap,
  LayoutDashboard,
  ScanLine,
  Settings,
  type LucideIcon,
} from "lucide-react"

export interface NavItem {
  title: string
  path: string
  icon: LucideIcon
  description: string
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "总览",
    items: [
      {
        title: "工作台",
        path: "/dashboard",
        icon: LayoutDashboard,
        description: "待办与学习概览",
      },
    ],
  },
  {
    label: "病案",
    items: [
      {
        title: "病案列表",
        path: "/cases",
        icon: FolderOpen,
        description: "浏览、检索、选择、删除与导出病案",
      },
      {
        title: "病案分析",
        path: "/analytics",
        icon: BarChart3,
        description: "证型、药味与舌脉频次统计",
      },
      {
        title: "导入校对",
        path: "/intake",
        icon: ScanLine,
        description: "上传处方并校对 OCR 结果",
      },
    ],
  },
  {
    label: "学习",
    items: [
      {
        title: "跟师学习",
        path: "/learning",
        icon: GraduationCap,
        description: "跟诊日志、心得与导师点评",
      },
      {
        title: "跟师统计",
        path: "/learning/stats",
        icon: BarChart3,
        description: "跟诊病案、证型与笔记统计",
      },
    ],
  },
  {
    label: "管理",
    items: [
      {
        title: "字典维护",
        path: "/dictionary",
        icon: BookMarked,
        description: "中药、证型、方剂与术语",
      },
      {
        title: "数据管理",
        path: "/admin",
        icon: Database,
        description: "备份、审计与完整性自检",
      },
      {
        title: "设置",
        path: "/settings",
        icon: Settings,
        description: "DeepSeek API Key 与模型",
      },
    ],
  },
]

export const NAV_TITLES: Record<string, string> = {
  "/dashboard": "工作台",
  "/cases": "病案列表",
  "/analytics": "病案分析",
  "/intake": "导入校对",
  "/learning": "跟师学习",
  "/learning/stats": "跟师统计",
  "/dictionary": "字典维护",
  "/admin": "数据管理",
  "/settings": "设置",
}
