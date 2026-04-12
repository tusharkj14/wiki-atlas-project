'use client'

import { useEffect, useMemo, useRef, useCallback } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import type { MainPageFeature } from '@/lib/types'
import PinPopup from '../PinPopup'

const defaultIcon = L.icon({
  iconUrl: '/marker-icon.png',
  iconRetinaUrl: '/marker-icon-2x.png',
  shadowUrl: '/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

const activeIcon = L.icon({
  iconUrl: '/marker-icon.png',
  iconRetinaUrl: '/marker-icon-2x.png',
  shadowUrl: '/marker-shadow.png',
  iconSize: [30, 49],
  iconAnchor: [15, 49],
  popupAnchor: [1, -40],
  shadowSize: [49, 49],
})

const dimmedIcon = L.icon({
  iconUrl: '/marker-icon.png',
  iconRetinaUrl: '/marker-icon-2x.png',
  shadowUrl: '/marker-shadow.png',
  iconSize: [20, 33],
  iconAnchor: [10, 33],
  popupAnchor: [1, -28],
  shadowSize: [33, 33],
})

function FlyToActive({
  features,
  activeIndex,
  markerRefs,
}: {
  features: MainPageFeature[]
  activeIndex: number | null
  markerRefs: React.MutableRefObject<Map<string, L.Marker>>
}) {
  const map = useMap()

  useEffect(() => {
    if (features.length === 0) return

    if (activeIndex !== null) {
      const activeFeatures = features.filter(
        (f) => f.properties.source_item_index === activeIndex,
      )
      if (activeFeatures.length > 0) {
        const bounds = L.latLngBounds(
          activeFeatures.map((f) => [f.geometry.coordinates[1], f.geometry.coordinates[0]]),
        )
        map.flyToBounds(bounds, { padding: [60, 60], maxZoom: 8, duration: 0.8 })

        // Open the first active pin's popup after the fly animation
        const firstActive = activeFeatures[0]
        const key = `${firstActive.properties.place_name}-${activeIndex}-0`
        setTimeout(() => {
          // Find the first marker ref that belongs to this active index
          for (const [refKey, marker] of markerRefs.current.entries()) {
            if (refKey.startsWith(`active-${activeIndex}-`)) {
              marker.openPopup()
              break
            }
          }
        }, 900)
        return
      }
    }

    // No active item — fit all features
    const bounds = L.latLngBounds(
      features.map((f) => [f.geometry.coordinates[1], f.geometry.coordinates[0]]),
    )
    map.fitBounds(bounds, { padding: [48, 48] })
  }, [features, activeIndex, map, markerRefs])

  return null
}

interface Props {
  features: MainPageFeature[]
  activeIndex: number | null
}

export default function LandingMap({ features, activeIndex }: Props) {
  const markerRefs = useRef<Map<string, L.Marker>>(new Map())

  const setMarkerRef = useCallback((key: string, marker: L.Marker | null) => {
    if (marker) {
      markerRefs.current.set(key, marker)
    } else {
      markerRefs.current.delete(key)
    }
  }, [])

  const sortedFeatures = useMemo(() => {
    if (activeIndex === null) return features
    return [
      ...features.filter((f) => f.properties.source_item_index !== activeIndex),
      ...features.filter((f) => f.properties.source_item_index === activeIndex),
    ]
  }, [features, activeIndex])

  // Track per-active-index counter for ref keys
  let activeCounter = 0

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
      {sortedFeatures.map((feature, i) => {
        const isActive = activeIndex !== null && feature.properties.source_item_index === activeIndex
        const isDimmed = activeIndex !== null && !isActive
        const refKey = isActive
          ? `active-${activeIndex}-${activeCounter++}`
          : `pin-${i}`

        return (
          <Marker
            key={`${feature.properties.place_name}-${i}`}
            position={[feature.geometry.coordinates[1], feature.geometry.coordinates[0]]}
            icon={isActive ? activeIcon : isDimmed ? dimmedIcon : defaultIcon}
            opacity={isDimmed ? 0.4 : 1}
            zIndexOffset={isActive ? 1000 : 0}
            ref={(ref) => setMarkerRef(refKey, ref)}
          >
            <Popup>
              <PinPopup properties={feature.properties} />
              <p className="text-xs text-blue-600 mt-2 font-medium border-t border-gray-100 pt-2">
                {feature.properties.source_item_label}
              </p>
            </Popup>
          </Marker>
        )
      })}
      <FlyToActive features={features} activeIndex={activeIndex} markerRefs={markerRefs} />
    </MapContainer>
  )
}
