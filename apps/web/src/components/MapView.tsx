'use client'

import { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import type { GeoJSONFeature } from '@/lib/types'
import PinPopup from './PinPopup'

// Fix Leaflet default icon resolution broken by Webpack/Next.js bundler
const defaultIcon = L.icon({
  iconUrl: '/marker-icon.png',
  iconRetinaUrl: '/marker-icon-2x.png',
  shadowUrl: '/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

function FitBounds({ features }: { features: GeoJSONFeature[] }) {
  const map = useMap()
  useEffect(() => {
    if (features.length === 0) return
    const bounds = L.latLngBounds(
      features.map((f) => [f.geometry.coordinates[1], f.geometry.coordinates[0]])
    )
    map.fitBounds(bounds, { padding: [48, 48] })
  }, [features, map])
  return null
}

interface Props {
  features: GeoJSONFeature[]
}

export default function MapView({ features }: Props) {
  return (
    <MapContainer
      center={[20, 0]}
      zoom={2}
      className="h-full w-full"
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {features.map((feature, i) => (
        <Marker
          key={`${feature.properties.place_name}-${i}`}
          position={[feature.geometry.coordinates[1], feature.geometry.coordinates[0]]}
          icon={defaultIcon}
        >
          <Popup>
            <PinPopup properties={feature.properties} />
          </Popup>
        </Marker>
      ))}
      <FitBounds features={features} />
    </MapContainer>
  )
}
