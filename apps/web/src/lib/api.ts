import type { ProcessResult, MainPageSection, MainPageSectionResult } from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      // ignore parse errors
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export async function processUrl(url: string, signal?: AbortSignal): Promise<ProcessResult> {
  const res = await fetch(`${API_BASE}/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
    signal,
  })
  return handleResponse<ProcessResult>(res)
}

export async function getBySlug(slug: string): Promise<ProcessResult> {
  const res = await fetch(`${API_BASE}/article/${slug}`, { cache: 'no-store' })
  return handleResponse<ProcessResult>(res)
}

export async function getRandomArticleUrl(): Promise<string> {
  const res = await fetch(`${API_BASE}/random`)
  const data = await handleResponse<{ url: string }>(res)
  return data.url
}

export async function getMainPageSection(
  section: MainPageSection,
  signal?: AbortSignal,
): Promise<MainPageSectionResult> {
  const res = await fetch(`${API_BASE}/main-page/${section}`, { signal })
  return handleResponse<MainPageSectionResult>(res)
}
