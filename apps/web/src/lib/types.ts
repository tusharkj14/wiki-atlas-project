export type PlaceType =
  | 'city'
  | 'country'
  | 'region'
  | 'landmark'
  | 'battle_site'
  | 'natural_feature'
  | 'other'

export type Relationship =
  | 'birthplace'
  | 'death_place'
  | 'battle_site'
  | 'headquarters'
  | 'founded_in'
  | 'visited'
  | 'mentioned'
  | 'other'

export interface GeoJSONProperties {
  place_name: string
  place_type: PlaceType
  relationship: Relationship
  reason: string
  source_sentence: string
  geocoder: string | null
}

export interface GeoJSONGeometry {
  type: 'Point'
  coordinates: [number, number] // [lng, lat]
}

export interface GeoJSONFeature {
  type: 'Feature'
  geometry: GeoJSONGeometry
  properties: GeoJSONProperties
}

export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection'
  features: GeoJSONFeature[]
}

export interface ProcessResult {
  url: string
  url_hash: string
  title: string
  geojson: GeoJSONFeatureCollection
  total_extracted: number
  total_geocoded: number
  share_slug: string | null
  cache_hit: boolean
}
