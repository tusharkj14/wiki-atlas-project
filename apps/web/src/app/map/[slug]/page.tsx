import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import MapClient from '@/components/MapClient'
import { getBySlug } from '@/lib/api'

interface Props {
  params: { slug: string }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  try {
    const data = await getBySlug(params.slug)
    return {
      title: `${data.title} — WikiMap`,
      description: `${data.total_geocoded} locations from "${data.title}" visualized on WikiMap.`,
      openGraph: {
        title: `${data.title} — WikiMap`,
        description: `Explore ${data.total_geocoded} locations mentioned in the Wikipedia article for "${data.title}".`,
        type: 'website',
      },
    }
  } catch {
    return { title: 'WikiMap' }
  }
}

export default async function SlugPage({ params }: Props) {
  const data = await getBySlug(params.slug).catch(() => null)
  if (!data) notFound()

  const features = data.geojson?.features ?? []

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <header className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200 shadow-sm flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <a href="/" className="flex items-center gap-2 flex-shrink-0">
            <span className="text-xl" aria-hidden>🌍</span>
            <span className="font-bold text-gray-900 text-lg tracking-tight">WikiMap</span>
          </a>
          <span className="text-gray-200 hidden sm:inline">|</span>
          <a
            href={data.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-gray-800 hover:underline truncate hidden sm:inline"
          >
            {data.title}
          </a>
          <span className="text-sm text-gray-500 whitespace-nowrap flex-shrink-0 hidden sm:inline">
            {data.total_geocoded} of {data.total_extracted} locations
          </span>
        </div>
        <a
          href={data.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors flex-shrink-0 ml-3"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-3.5 w-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
            />
          </svg>
          Open in Wikipedia
        </a>
      </header>

      <div className="flex-1 relative overflow-hidden">
        <MapClient features={features} />
      </div>
    </div>
  )
}
