import type { ProcessResult } from '@/lib/types'
import ShareButton from './ShareButton'
import ExportButton from './ExportButton'

interface Props {
  result: ProcessResult
}

export default function ResultsHeader({ result }: Props) {
  const { title, url, total_extracted, total_geocoded, cache_hit, share_slug } = result

  return (
    <div className="flex items-center justify-between px-3 sm:px-4 py-2 bg-white border-b border-gray-100 text-sm">
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold text-gray-900 hover:underline truncate text-xs sm:text-sm"
        >
          {title}
        </a>
        <span className="text-gray-400 whitespace-nowrap text-xs sm:text-sm">
          {total_geocoded}/{total_extracted} <span className="hidden sm:inline">locations mapped</span><span className="sm:hidden">locations</span>
        </span>
        {cache_hit && (
          <span className="hidden sm:inline-block px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700 font-medium whitespace-nowrap">
            Cached
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <ExportButton geojson={result.geojson} title={title} />
        {share_slug && <ShareButton slug={share_slug} />}
      </div>
    </div>
  )
}
