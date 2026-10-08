import { Check, ChevronsUpDown, Loader2 } from "lucide-react"
import * as React from "react"
import { createPortal } from "react-dom"

import { cn } from "@/lib/utils"
import { useDebouncedValue } from "@/hooks/use-debounce"

export interface ComboboxOption {
  value: string
  label: string
  hint?: string
  meta?: Record<string, unknown>
}

interface FreeTextComboboxProps {
  value: string
  onValueChange: (value: string, option?: ComboboxOption) => void
  load: (q: string) => Promise<ComboboxOption[]>
  placeholder?: string
  className?: string
}

/**
 * 自由文本 + 联想：输入即检索，回车或点击可选中，也允许直接输入自由文本。
 * 用于药名、舌质、舌苔、脉象、证型、方剂等“字典建议但不强制”的场景。
 *
 * 下拉列表通过 portal 渲染到 body，避免被表格等 overflow-hidden 容器裁剪。
 */
export function FreeTextCombobox({
  value,
  onValueChange,
  load,
  placeholder,
  className,
}: FreeTextComboboxProps) {
  const [open, setOpen] = React.useState(false)
  const [options, setOptions] = React.useState<ComboboxOption[]>([])
  const [loading, setLoading] = React.useState(false)
  const [highlight, setHighlight] = React.useState(0)
  const rootRef = React.useRef<HTMLDivElement>(null)
  const inputRef = React.useRef<HTMLInputElement>(null)
  const [rect, setRect] = React.useState<{ top: number; left: number; width: number } | null>(null)

  const debouncedValue = useDebouncedValue(value, 220)

  function openDropdown() {
    const el = inputRef.current
    if (el) {
      const r = el.getBoundingClientRect()
      setRect({ top: r.bottom + 4, left: r.left, width: r.width })
    }
    setOpen(true)
  }

  React.useEffect(() => {
    let cancelled = false
    if (!debouncedValue.trim()) {
      setOptions([])
      setOpen(false)
      return
    }
    setLoading(true)
    load(debouncedValue.trim())
      .then((opts) => {
        if (!cancelled) {
          setOptions(opts.slice(0, 8))
          setHighlight(0)
          if (opts.length > 0) openDropdown()
        }
      })
      .catch(() => {
        if (!cancelled) setOptions([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [debouncedValue, load])

  // 点击外部关闭
  React.useEffect(() => {
    function onDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", onDown)
    return () => document.removeEventListener("mousedown", onDown)
  }, [])

  // 滚动/缩放时重算位置，保证下拉跟随输入框
  React.useEffect(() => {
    if (!open) return
    function reposition() {
      const el = inputRef.current
      if (el) {
        const r = el.getBoundingClientRect()
        setRect({ top: r.bottom + 4, left: r.left, width: r.width })
      }
    }
    window.addEventListener("scroll", reposition, true)
    window.addEventListener("resize", reposition)
    return () => {
      window.removeEventListener("scroll", reposition, true)
      window.removeEventListener("resize", reposition)
    }
  }, [open])

  function select(option: ComboboxOption) {
    onValueChange(option.label, option)
    setOpen(false)
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || options.length === 0) {
      if (e.key === "Escape") setOpen(false)
      return
    }
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setHighlight((h) => (h + 1) % options.length)
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setHighlight((h) => (h - 1 + options.length) % options.length)
    } else if (e.key === "Enter") {
      e.preventDefault()
      select(options[highlight])
    } else if (e.key === "Escape") {
      setOpen(false)
    }
  }

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <input
        ref={inputRef}
        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
        value={value}
        placeholder={placeholder}
        onChange={(e) => {
          onValueChange(e.target.value)
          openDropdown()
        }}
        onFocus={() => {
          if (options.length > 0) openDropdown()
        }}
        onKeyDown={onKeyDown}
      />
      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2">
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : (
          <ChevronsUpDown className="h-4 w-4 text-muted-foreground" />
        )}
      </span>

      {open && options.length > 0 && rect &&
        createPortal(
          <ul
            style={{ position: "fixed", top: rect.top, left: rect.left, width: rect.width }}
            className="z-[9999] max-h-64 overflow-auto rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
          >
            {options.map((option, i) => (
              <li
                key={option.value}
                onMouseEnter={() => setHighlight(i)}
                onClick={() => select(option)}
                className={cn(
                  "flex cursor-default select-none items-center justify-between rounded-sm px-2 py-1.5 text-sm outline-none",
                  i === highlight && "bg-accent text-accent-foreground",
                )}
              >
                <span>
                  {option.label}
                  {option.hint && (
                    <span className="ml-2 text-xs text-muted-foreground">
                      {option.hint}
                    </span>
                  )}
                </span>
                {option.label === value && <Check className="h-4 w-4" />}
              </li>
            ))}
          </ul>,
          document.body,
        )}
    </div>
  )
}
