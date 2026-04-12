'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { getMainPageSection } from '@/lib/api'
import type { MainPageSection, MainPageSectionResult } from '@/lib/types'

type Status = 'idle' | 'loading' | 'success' | 'error'

interface State {
  status: Status
  data: MainPageSectionResult | null
  error: string | null
}

export function useMainPageSection(section: MainPageSection) {
  const [state, setState] = useState<State>({
    status: 'idle',
    data: null,
    error: null,
  })
  const abortRef = useRef<AbortController | null>(null)
  const fetchedRef = useRef<string | null>(null)

  const fetch_ = useCallback(() => {
    // Don't re-fetch if already loaded for this section
    if (fetchedRef.current === section && state.status === 'success') return

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setState({ status: 'loading', data: null, error: null })

    getMainPageSection(section, controller.signal)
      .then((data) => {
        fetchedRef.current = section
        setState({ status: 'success', data, error: null })
      })
      .catch((err) => {
        if ((err as Error).name === 'AbortError') return
        setState({ status: 'error', data: null, error: (err as Error).message })
      })
  }, [section, state.status])

  // Auto-fetch when section changes
  useEffect(() => {
    if (fetchedRef.current !== section) {
      fetch_()
    }
    return () => {
      abortRef.current?.abort()
    }
  }, [section]) // eslint-disable-line react-hooks/exhaustive-deps

  const retry = useCallback(() => {
    fetchedRef.current = null
    fetch_()
  }, [fetch_])

  return { ...state, retry }
}
