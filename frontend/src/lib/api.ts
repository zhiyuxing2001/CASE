// 轻量 fetch 封装。开发态经 Vite 代理转发到 FastAPI。

export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) {
    throw new Error(`请求失败 (${res.status})`)
  }
  return res.json() as Promise<T>
}
