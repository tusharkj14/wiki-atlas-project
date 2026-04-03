'use client'

import { useState, useCallback, useEffect } from 'react'

const STORAGE_KEY = 'wikimap:recent_searches'
const MAX_ENTRIES = 20

export interface SearchEntry {
  url: string
  title: string
  total_geocoded: number
  searched_at: number // epoch ms
}

function load(): SearchEntry[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as SearchEntry[]) : []
  } catch {
    return []
  }
}

function save(entries: SearchEntry[]) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(entries))
  } catch {
    // storage full or unavailable — silently ignore
  }
}

export function useSearchHistory() {
  const [history, setHistory] = useState<SearchEntry[]>([])

  // Load from sessionStorage on mount
  useEffect(() => {
    setHistory(load())
  }, [])

  const add = useCallback((entry: Omit<SearchEntry, 'searched_at'>) => {
    setHistory((prev) => {
      // Remove duplicate if same URL already exists
      const filtered = prev.filter((e) => e.url !== entry.url)
      const updated = [{ ...entry, searched_at: Date.now() }, ...filtered].slice(0, MAX_ENTRIES)
      save(updated)
      return updated
    })
  }, [])

  const remove = useCallback((url: string) => {
    setHistory((prev) => {
      const updated = prev.filter((e) => e.url !== url)
      save(updated)
      return updated
    })
  }, [])

  const clear = useCallback(() => {
    setHistory([])
    try { sessionStorage.removeItem(STORAGE_KEY) } catch {}
  }, [])

  return { history, add, remove, clear }
}
