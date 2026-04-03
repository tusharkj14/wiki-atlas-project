'use client'

import { useState, useEffect, useRef, useCallback } from 'react'

interface Props {
  onSubmit: (url: string) => void
  disabled: boolean
}

interface Suggestion {
  title: string
  url: string
}

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

export default function WikiSearchBar({ onSubmit, disabled }: Props) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const [loading, setLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const selectedRef = useRef('')  // tracks the last selected title to suppress re-fetch
  const debouncedQuery = useDebounce(query, 300)

  useEffect(() => {
    if (debouncedQuery.length < 2) {
      setSuggestions([])
      setOpen(false)
      return
    }

    // Don't re-fetch after selecting a suggestion
    if (debouncedQuery === selectedRef.current) {
      return
    }

    let cancelled = false
    setLoading(true)

    fetch(
      `https://en.wikipedia.org/w/api.php?action=opensearch&search=${encodeURIComponent(debouncedQuery)}&limit=8&namespace=0&format=json&origin=*`
    )
      .then((r) => r.json())
      .then(([, titles, , urls]: [string, string[], string[], string[]]) => {
        if (cancelled) return
        setSuggestions(titles.map((title, i) => ({ title, url: urls[i] })))
        setOpen(titles.length > 0)
        setActiveIndex(-1)
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [debouncedQuery])

  const select = useCallback(
    (s: Suggestion) => {
      selectedRef.current = s.title
      setQuery(s.title)
      setSuggestions([])
      setOpen(false)
      onSubmit(s.url)
    },
    [onSubmit]
  )

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((i) => Math.min(i + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault()
      select(suggestions[activeIndex])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  const clear = () => {
    setQuery('')
    setSuggestions([])
    setOpen(false)
    setActiveIndex(-1)
    inputRef.current?.focus()
  }

  return (
    <div className="relative w-full max-w-xl">
      <div className="flex items-center bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <span className="pl-3 text-gray-400">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </span>
        <input
          ref={inputRef}
          type="text"
          className="flex-1 px-3 py-2.5 text-sm outline-none bg-transparent placeholder-gray-400 disabled:opacity-60"
          placeholder="Search Wikipedia articles..."
          value={query}
          onChange={(e) => { selectedRef.current = ''; setQuery(e.target.value) }}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          disabled={disabled}
          autoComplete="off"
        />
        {query && !disabled && (
          <button
            onClick={clear}
            className="pr-2 text-gray-400 hover:text-gray-600"
            type="button"
            aria-label="Clear"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
        {loading && (
          <div className="pr-3">
            <div className="h-4 w-4 border-2 border-gray-200 border-t-blue-500 rounded-full animate-spin" />
          </div>
        )}
      </div>

      {open && (
        <ul className="absolute top-full left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 z-50 overflow-hidden">
          {suggestions.map((s, i) => (
            <li
              key={s.url}
              className={`px-4 py-2.5 cursor-pointer text-sm flex items-center gap-2 ${
                i === activeIndex
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-800 hover:bg-gray-50'
              }`}
              onMouseDown={() => select(s)}
              onMouseEnter={() => setActiveIndex(i)}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4 text-gray-400 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                />
              </svg>
              {s.title}
            </li>
          ))}
          <li className="px-4 py-1.5 text-xs text-gray-400 border-t border-gray-100 bg-gray-50">
            Powered by Wikipedia
          </li>
        </ul>
      )}
    </div>
  )
}
