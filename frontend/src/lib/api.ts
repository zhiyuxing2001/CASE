// 轻量 fetch 封装。开发态经 Vite 代理转发到 FastAPI。

export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) {
    throw new Error(`请求失败 (${res.status})`)
  }
  return res.json() as Promise<T>
}

export async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`请求失败 (${res.status}) ${detail}`)
  }
  return res.json() as Promise<T>
}

export async function putJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`请求失败 (${res.status}) ${detail}`)
  }
  return res.json() as Promise<T>
}
