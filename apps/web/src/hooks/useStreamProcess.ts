'use client'

import { useState, useRef, useCallback } from 'react'
import type { GeoJSONFeature, ProcessResult } from '@/lib/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

type Status = 'idle' | 'loading' | 'success' | 'error'

interface StreamState {
  status: Status
  features: GeoJSONFeature[]
  meta: {
    title: string
    url: string
    url_hash: string
    total_extracted: number
  } | null
  done: {
    total_geocoded: number
    share_slug: string | null
    cache_hit: boolean
  } | null
  error: string | null
}

const initialState: StreamState = {
  status: 'idle',
  features: [],
  meta: null,
  done: null,
  error: null,
}

export function useStreamProcess() {
  const [state, setState] = useState<StreamState>(initialState)
  const abortRef = useRef<AbortController | null>(null)

  const submit = useCallback((url: string) => {
    // Abort any in-flight stream
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setState({ ...initialState, status: 'loading' })

    const streamUrl = `${API_BASE}/process/stream?url=${encodeURIComponent(url)}`

    // Use fetch + ReadableStream for SSE (works with AbortController, unlike EventSource)
    fetch(streamUrl, { signal: controller.signal })
      .then(async (res) => {
        if (!res.ok) {
          let detail = `HTTP ${res.status}`
          try {
            const body = await res.json()
            detail = body.detail ?? detail
          } catch { /* ignore */ }
          setState((s) => ({ ...s, status: 'error', error: detail }))
          return
        }

        const reader = res.body?.getReader()
        if (!reader) {
          setState((s) => ({ ...s, status: 'error', error: 'No response body' }))
          return
        }

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          // Parse SSE frames from buffer
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''  // keep incomplete last line

          let currentEvent = ''
          let currentData = ''

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7).trim()
            } else if (line.startsWith('data: ')) {
              currentData = line.slice(6)
            } else if (line === '' && currentEvent && currentData) {
              // End of SSE frame — process it
              try {
                const parsed = JSON.parse(currentData)
                if (currentEvent === 'meta') {
                  setState((s) => ({ ...s, meta: parsed }))
                } else if (currentEvent === 'pin') {
                  setState((s) => ({
                    ...s,
                    features: [...s.features, parsed as GeoJSONFeature],
                  }))
                } else if (currentEvent === 'done') {
                  setState((s) => ({
                    ...s,
                    status: 'success',
                    done: parsed,
                  }))
                } else if (currentEvent === 'error') {
                  setState((s) => ({
                    ...s,
                    status: 'error',
                    error: parsed.message,
                  }))
                }
              } catch { /* ignore parse errors */ }
              currentEvent = ''
              currentData = ''
            }
          }
        }
      })
      .catch((err) => {
        if ((err as Error).name === 'AbortError') return
        setState((s) => ({
          ...s,
          status: 'error',
          error: (err as Error).message,
        }))
      })
  }, [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setState(initialState)
  }, [])

  // Build a ProcessResult-compatible object for ResultsHeader/ShareButton
  const result: ProcessResult | null =
    state.meta && state.done
      ? {
          url: state.meta.url,
          url_hash: state.meta.url_hash,
          title: state.meta.title,
          geojson: { type: 'FeatureCollection' as const, features: state.features },
          total_extracted: state.meta.total_extracted,
          total_geocoded: state.done.total_geocoded,
          share_slug: state.done.share_slug,
          cache_hit: state.done.cache_hit,
        }
      : null

  return { state, result, submit, reset }
}
