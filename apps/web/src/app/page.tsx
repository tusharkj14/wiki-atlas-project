'use client'

import { useState, useCallback, useEffect } from 'react'
import dynamic from 'next/dynamic'
import WikiSearchBar from '@/components/WikiSearchBar'
import ErrorBanner from '@/components/ErrorBanner'
import ResultsHeader from '@/components/ResultsHeader'
import SearchHistory from '@/components/SearchHistory'
import LandingPage from '@/components/landing/LandingPage'
import { useStreamProcess } from '@/hooks/useStreamProcess'
import { useSearchHistory } from '@/hooks/useSearchHistory'
import { getRandomArticleUrl } from '@/lib/api'

// SSR disabled — Leaflet requires window
const MapView = dynamic(() => import('@/components/MapView'), { ssr: false })

export default function Home() {
  const { state, result, submit, reset } = useStreamProcess()
  const { status, features, meta, error } = state
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { history, add, remove, clear } = useSearchHistory()

  // Show landing page when idle (no article searched)
  const showLanding = status === 'idle'

  // Save to history when stream completes
  useEffect(() => {
    if (status === 'success' && result) {
      add({
        url: result.url,
        title: result.title,
        total_geocoded: result.total_geocoded,
      })
    }
  }, [status, result, add])

  const handleHistorySelect = useCallback((url: string) => {
    setSidebarOpen(false)
    submit(url)
  }, [submit])

  const [randomLoading, setRandomLoading] = useState(false)

  const handleRandom = useCallback(async () => {
    setRandomLoading(true)
    try {
      const url = await getRandomArticleUrl()
      submit(url)
    } catch {
      // fall back silently — user can retry
    } finally {
      setRandomLoading(false)
    }
  }, [submit])

  const handleReset = useCallback(() => {
    reset()
  }, [reset])

  const isLoading = status === 'loading'

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
      <header className="flex items-center gap-2 sm:gap-4 px-3 sm:px-4 py-2 sm:py-3 bg-white border-b border-gray-200 shadow-sm z-[1000] relative flex-shrink-0">
        <button
          onClick={() => setSidebarOpen((prev) => !prev)}
          className="text-gray-500 hover:text-gray-700 flex-shrink-0 p-1"
          aria-label="Open recent searches"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <button
          onClick={handleReset}
          className="flex items-center gap-2 flex-shrink-0 hover:opacity-80 transition-opacity"
        >
          <span className="text-xl" aria-hidden>🌍</span>
          <span className="font-bold text-gray-900 text-lg tracking-tight hidden sm:inline">WikiAtlas</span>
        </button>
        <WikiSearchBar onSubmit={submit} disabled={isLoading} />
        <button
          onClick={handleRandom}
          disabled={isLoading || randomLoading}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs sm:text-sm font-medium bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 transition-colors flex-shrink-0 disabled:opacity-50 whitespace-nowrap"
          title="Random Wikipedia article"
        >
          {randomLoading ? (
            <div className="h-4 w-4 border-2 border-amber-200 border-t-amber-600 rounded-full animate-spin" />
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          )}
          <span className="hidden sm:inline">I&apos;m Feeling Lucky</span>
        </button>
        {isLoading && (
          <div className="hidden sm:flex items-center gap-2 text-sm text-gray-500 flex-shrink-0">
            <div className="h-4 w-4 border-2 border-gray-200 border-t-blue-600 rounded-full animate-spin" />
            <span>
              {meta
                ? `${features.length}/${meta.total_extracted} locations...`
                : 'Extracting locations...'}
            </span>
          </div>
        )}
      </header>

      {/* Error banner */}
      {error && <ErrorBanner message={error} onDismiss={reset} />}

      {/* Results header — shown only after success */}
      {status === 'success' && result && <ResultsHeader result={result} />}

      {/* Landing page or Map area */}
      {showLanding ? (
        <LandingPage />
      ) : (
        <div className="flex-1 relative overflow-hidden">
          <MapView features={features} />
          {isLoading && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-[999] pointer-events-none">
              <div className="bg-white rounded-xl shadow-lg px-6 py-3 flex items-center gap-3">
                <div className="h-5 w-5 border-[3px] border-gray-200 border-t-blue-600 rounded-full animate-spin" />
                <div>
                  <p className="font-medium text-gray-700 text-sm">
                    {meta ? meta.title : 'Processing...'}
                  </p>
                  <p className="text-xs text-gray-400">
                    {meta
                      ? `${features.length} of ${meta.total_extracted} locations geocoded`
                      : 'Scraping and extracting locations...'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
