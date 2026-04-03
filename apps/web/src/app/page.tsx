'use client'

import { useState, useCallback, useEffect } from 'react'
import dynamic from 'next/dynamic'
import WikiSearchBar from '@/components/WikiSearchBar'
import ErrorBanner from '@/components/ErrorBanner'
import ResultsHeader from '@/components/ResultsHeader'
import SearchHistory from '@/components/SearchHistory'
import { useProcessArticle } from '@/hooks/useProcessArticle'
import { useSearchHistory } from '@/hooks/useSearchHistory'

// SSR disabled — Leaflet requires window
const MapView = dynamic(() => import('@/components/MapView'), { ssr: false })

export default function Home() {
  const { state, submit, reset } = useProcessArticle()
  const { status, data, error } = state
  const features = data?.geojson?.features ?? []
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { history, add, remove, clear } = useSearchHistory()

  // Save to history when a search completes
  useEffect(() => {
    if (status === 'success' && data) {
      add({
        url: data.url,
        title: data.title,
        total_geocoded: data.total_geocoded,
      })
    }
  }, [status, data, add])

  const handleHistorySelect = useCallback((url: string) => {
    setSidebarOpen(false)
    submit(url)
  }, [submit])

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Sidebar */}
      <SearchHistory
        open={sidebarOpen}
        history={history}
        onSelect={handleHistorySelect}
        onRemove={remove}
        onClear={clear}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Fixed header */}
      <header className="flex items-center gap-4 px-4 py-3 bg-white border-b border-gray-200 shadow-sm z-[1000] relative flex-shrink-0">
        <button
          onClick={() => setSidebarOpen((prev) => !prev)}
          className="text-gray-500 hover:text-gray-700 flex-shrink-0 p-1"
          aria-label="Open recent searches"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xl" aria-hidden>🌍</span>
          <span className="font-bold text-gray-900 text-lg tracking-tight">WikiAtlas</span>
        </div>
        <WikiSearchBar onSubmit={submit} disabled={status === 'loading'} />
        {status === 'loading' && (
          <div className="flex items-center gap-2 text-sm text-gray-500 flex-shrink-0">
            <div className="h-4 w-4 border-2 border-gray-200 border-t-blue-600 rounded-full animate-spin" />
            <span>Extracting locations...</span>
          </div>
        )}
      </header>

      {/* Error banner */}
      {error && <ErrorBanner message={error} onDismiss={reset} />}

      {/* Results header — shown only after success */}
      {status === 'success' && data && <ResultsHeader result={data} />}

      {/* Map area — fills remaining height */}
      <div className="flex-1 relative overflow-hidden">
        <MapView features={features} />
        {status === 'loading' && (
          <div className="absolute inset-0 z-[999] flex items-center justify-center bg-white/60 backdrop-blur-[2px] pointer-events-none">
            <div className="bg-white rounded-xl shadow-lg px-8 py-6 flex flex-col items-center gap-3 text-center">
              <div className="h-8 w-8 border-[3px] border-gray-200 border-t-blue-600 rounded-full animate-spin" />
              <p className="font-medium text-gray-700 text-sm">Extracting locations...</p>
              <p className="text-xs text-gray-400">This may take up to a minute for new articles.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
