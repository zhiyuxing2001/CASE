import { cn } from "@/lib/utils"

/**
 * CASE 品牌图标——葫芦（悬壶济世）。
 *
 * 葫芦是中医临床的经典符号（“悬壶济世”），双腹造型简洁可辨识；
 * 顶部的小叶点出“本草”，呼应跟师学习与中药辨治。沿用蓝白配色，
 * 图标本身用 currentColor 填充，置于品牌底色上即可。
 */
export function CaseLogo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      className={cn("h-6 w-6", className)}
      aria-hidden="true"
    >
      {/* 葫芦茎 */}
      <path
        d="M12 1.8v2.6"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      {/* 小叶（本草） */}
      <path
        d="M12.1 2.5c1.9 0 3.1 1.2 3.1 3 0 1.3-.8 2.2-2 2.6"
        stroke="currentColor"
        strokeWidth="1.15"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* 葫芦上腹 */}
      <circle cx="12" cy="8.4" r="3.6" fill="currentColor" />
      {/* 葫芦下腹 */}
      <circle cx="12" cy="16.6" r="5.8" fill="currentColor" />
    </svg>
  )
}
