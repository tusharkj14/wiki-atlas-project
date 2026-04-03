'use client'

import type { SearchEntry } from '@/hooks/useSearchHistory'

interface Props {
  open: boolean
  history: SearchEntry[]
  onSelect: (url: string) => void
  onRemove: (url: string) => void
  onClear: () => void
  onClose: () => void
}

function timeAgo(epoch: number): string {
  const seconds = Math.floor((Date.now() - epoch) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

export default function SearchHistory({ open, history, onSelect, onRemove, onClear, onClose }: Props) {
  return (
    <>
      {/* Backdrop — above everything including Leaflet */}
      {open && (
        <div
          className="fixed inset-0 z-[2000] bg-black/30 backdrop-blur-[1px]"
          onClick={onClose}
        />
      )}

      {/* Sidebar panel */}
      <div
        className={`fixed top-0 left-0 h-full w-72 sm:w-80 bg-white shadow-2xl z-[2001] transform transition-transform duration-200 ease-out flex flex-col ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 flex-shrink-0 bg-gray-50">
          <h2 className="font-semibold text-gray-800 text-sm">Recent Searches</h2>
          <div className="flex items-center gap-3">
            {history.length > 0 && (
              <button
                onClick={onClear}
                className="text-xs text-gray-400 hover:text-red-500 transition-colors"
              >
                Clear all
              </button>
            )}
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 p-1 -mr-1"
              aria-label="Close sidebar"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {history.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm px-6 text-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 mb-3 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p>No recent searches</p>
              <p className="text-xs mt-1 text-gray-300">Your searches in this session will appear here</p>
            </div>
          ) : (
            <ul className="py-1">
              {history.map((entry) => (
                <li key={entry.url} className="group">
                  <button
                    onClick={() => onSelect(entry.url)}
                    className="w-full text-left px-4 py-3 hover:bg-blue-50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-800 leading-snug truncate">
                          {entry.title}
                        </p>
                        <div className="flex items-center gap-1.5 mt-1 text-xs text-gray-400">
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                          </svg>
                          <span>{entry.total_geocoded} locations</span>
                          <span className="text-gray-300">·</span>
                          <span>{timeAgo(entry.searched_at)}</span>
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onRemove(entry.url)
                        }}
                        className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-400 transition-all flex-shrink-0 p-1 -mr-1"
                        aria-label={`Remove ${entry.title}`}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </>
  )
}
