'use client'

import dynamic from 'next/dynamic'
import type { GeoJSONFeature } from '@/lib/types'

// Dynamically import MapView with SSR disabled — Leaflet requires window
const MapView = dynamic(() => import('./MapView'), { ssr: false })

interface Props {
  features: GeoJSONFeature[]
}

export default function MapClient({ features }: Props) {
  return (
    <div className="h-full w-full">
      <MapView features={features} />
    </div>
  )
}
