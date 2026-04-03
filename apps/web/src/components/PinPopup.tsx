import type { GeoJSONProperties, PlaceType } from '@/lib/types'

const placeTypeColours: Record<PlaceType, string> = {
  city: 'bg-blue-100 text-blue-800',
  country: 'bg-green-100 text-green-800',
  region: 'bg-purple-100 text-purple-800',
  landmark: 'bg-amber-100 text-amber-800',
  battle_site: 'bg-red-100 text-red-800',
  natural_feature: 'bg-teal-100 text-teal-800',
  other: 'bg-gray-100 text-gray-800',
}

interface Props {
  properties: GeoJSONProperties
}

export default function PinPopup({ properties }: Props) {
  const { place_name, place_type, relationship, reason, source_sentence } = properties
  const badgeClass = placeTypeColours[place_type] ?? placeTypeColours.other

  return (
    <div className="min-w-[200px] max-w-[280px] text-sm font-sans">
      <h3 className="font-semibold text-gray-900 text-base mb-1">{place_name}</h3>
      <div className="flex items-center gap-1.5 mb-2">
        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${badgeClass}`}>
          {place_type.replace(/_/g, ' ')}
        </span>
        <span className="text-gray-500 text-xs">{relationship.replace(/_/g, ' ')}</span>
      </div>
      <p className="text-gray-700 mb-2 leading-snug">{reason}</p>
      <p className="text-gray-400 italic text-xs leading-relaxed">{source_sentence}</p>
    </div>
  )
}
