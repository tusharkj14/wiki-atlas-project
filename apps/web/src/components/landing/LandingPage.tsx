'use client'

import { useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { useMainPageSection } from '@/hooks/useMainPageSection'
import SectionPanel from './SectionPanel'
import type { MainPageSection } from '@/lib/types'

const LandingMap = dynamic(() => import('./LandingMap'), { ssr: false })

const TABS: { key: MainPageSection; label: string; icon: string }[] = [
  { key: 'in_the_news', label: 'In the News', icon: '📰' },
  { key: 'on_this_day', label: 'On This Day', icon: '📅' },
]

export default function LandingPage() {
  const [activeTab, setActiveTab] = useState<MainPageSection>('in_the_news')
  const [activeItemIndex, setActiveItemIndex] = useState<number | null>(null)
  const [panelOpen, setPanelOpen] = useState(true)
  const { status, data, error, retry } = useMainPageSection(activeTab)

  const features = data?.geojson?.features ?? []
  const items = data?.items ?? []

  const handleTabChange = useCallback((tab: MainPageSection) => {
    setActiveTab(tab)
    setActiveItemIndex(null)
  }, [])

  const handleItemSelect = useCallback((index: number) => {
    setActiveItemIndex(index)
  }, [])

  return (
    <div className="flex-1 flex overflow-hidden relative">
      {/* Side panel */}
      <div
        className={`flex-shrink-0 bg-white border-r border-gray-200 flex flex-col transition-all duration-300 z-10 ${
          panelOpen ? 'w-80 sm:w-96' : 'w-0'
        } overflow-hidden`}
      >
        {/* Tabs */}
        <div className="flex border-b border-gray-200 flex-shrink-0">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => handleTabChange(tab.key)}
              className={`flex-1 px-2 py-2.5 text-xs sm:text-sm font-medium transition-colors relative ${
                activeTab === tab.key
                  ? 'text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <span className="mr-1">{tab.icon}</span>
              <span className="hidden sm:inline">{tab.label}</span>
              <span className="sm:hidden">{tab.label.split(' ').pop()}</span>
              {activeTab === tab.key && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600" />
              )}
            </button>
          ))}
        </div>

        {/* Section header */}
        <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-100 flex-shrink-0">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700">
              {TABS.find((t) => t.key === activeTab)?.label}
            </h3>
            {status === 'success' && data && (
              <span className="text-xs text-gray-400">
                {data.total_items} items &middot; {data.total_geocoded} pins
              </span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            From Wikipedia&apos;s main page
          </p>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {status === 'loading' && (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <div className="h-8 w-8 border-[3px] border-gray-200 border-t-blue-600 rounded-full animate-spin" />
              <p className="text-sm text-gray-500">Loading section...</p>
              <p className="text-xs text-gray-400">
                Extracting locations from Wikipedia&apos;s main page
              </p>
            </div>
          )}

          {status === 'error' && (
            <div className="flex flex-col items-center justify-center h-full gap-3 px-4">
              <p className="text-sm text-red-600 text-center">{error}</p>
              <button
                onClick={retry}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Retry
              </button>
            </div>
          )}

          {status === 'success' && data && (
            <SectionPanel
              items={items}
              features={features}
              activeIndex={activeItemIndex}
              onItemSelect={handleItemSelect}
              section={activeTab}
            />
          )}
        </div>
      </div>

      {/* Panel toggle — sits inside the map area, left edge */}
      <button
        onClick={() => setPanelOpen((prev) => !prev)}
        className="absolute left-0 top-1/2 -translate-y-1/2 z-20 bg-white border border-gray-200 rounded-r-lg shadow-md px-1 py-3 hover:bg-gray-50 transition-all"
        aria-label={panelOpen ? 'Close panel' : 'Open panel'}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className={`h-4 w-4 text-gray-500 transition-transform ${panelOpen ? '' : 'rotate-180'}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* Map */}
      <div className="flex-1 relative">
        <LandingMap features={features} activeIndex={activeItemIndex} />
        {status === 'loading' && (
          <div className="absolute inset-0 z-[999] flex items-center justify-center bg-white/60 backdrop-blur-[2px] pointer-events-none">
            <div className="bg-white rounded-xl shadow-lg px-8 py-6 flex flex-col items-center gap-3 text-center">
              <div className="h-8 w-8 border-[3px] border-gray-200 border-t-blue-600 rounded-full animate-spin" />
              <p className="font-medium text-gray-700 text-sm">Processing Wikipedia&apos;s main page...</p>
              <p className="text-xs text-gray-400">Extracting and geocoding locations</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
