'use client'

import type { MainPageItem, MainPageFeature } from '@/lib/types'

interface Props {
  items: MainPageItem[]
  features: MainPageFeature[]
  activeIndex: number | null
  onItemSelect: (index: number) => void
  section: string
}

export default function SectionPanel({
  items,
  features,
  activeIndex,
  onItemSelect,
  section,
}: Props) {
  const pinCountByItem = (index: number) =>
    features.filter((f) => f.properties.source_item_index === index).length

  return (
    <div className="h-full overflow-y-auto">
      <ul className="divide-y divide-gray-100">
        {items.map((item) => {
          const isActive = activeIndex === item.index
          const pins = pinCountByItem(item.index)
          const hasPins = pins > 0

          return (
            <li
              key={item.index}
              className={`px-4 py-3 transition-colors ${
                hasPins ? 'cursor-pointer' : 'cursor-default'
              } ${
                isActive
                  ? 'bg-blue-50 border-l-3 border-blue-500'
                  : hasPins
                    ? 'hover:bg-gray-50 border-l-3 border-transparent'
                    : 'border-l-3 border-transparent opacity-70'
              }`}
              onClick={() => hasPins && onItemSelect(item.index)}
            >
              <div className="flex items-start gap-2">
                {section === 'on_this_day' && item.year && (
                  <span className={`flex-shrink-0 text-xs font-bold px-2 py-0.5 rounded-full mt-0.5 ${
                    isActive
                      ? 'text-blue-700 bg-blue-100'
                      : 'text-blue-600 bg-blue-50'
                  }`}>
                    {item.year}
                  </span>
                )}
                <p className={`text-sm leading-relaxed ${
                  isActive ? 'text-gray-900 font-medium' : 'text-gray-700'
                }`}>
                  {item.text}
                </p>
              </div>
              <div className="mt-1.5 flex items-center gap-1 text-xs">
                {hasPins ? (
                  <span className={`flex items-center gap-1 ${isActive ? 'text-blue-500' : 'text-gray-400'}`}>
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    {pins} location{pins !== 1 ? 's' : ''}
                  </span>
                ) : (
                  <span className="text-gray-300 italic">No locations tagged</span>
                )}
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
