'use client'

import { useState, useRef, useCallback } from 'react'
import { processUrl } from '@/lib/api'
import type { ProcessResult } from '@/lib/types'

type Status = 'idle' | 'loading' | 'success' | 'error'

interface State {
  status: Status
  data: ProcessResult | null
  error: string | null
}

const initialState: State = { status: 'idle', data: null, error: null }

export function useProcessArticle() {
  const [state, setState] = useState<State>(initialState)
  const abortRef = useRef<AbortController | null>(null)

  const submit = useCallback(async (url: string) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setState({ status: 'loading', data: null, error: null })

    try {
      const data = await processUrl(url, controller.signal)
      setState({ status: 'success', data, error: null })
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      setState({ status: 'error', data: null, error: (err as Error).message })
    }
  }, [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setState(initialState)
  }, [])

  return { state, submit, reset }
}
