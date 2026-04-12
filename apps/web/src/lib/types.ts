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

// ── Main Page Landing ──────────────────────────────────────────────

export interface MainPageGeoJSONProperties extends GeoJSONProperties {
  source_item_index: number
  source_item_label: string
}

export interface MainPageFeature {
  type: 'Feature'
  geometry: GeoJSONGeometry
  properties: MainPageGeoJSONProperties
}

export interface MainPageItem {
  index: number
  text: string
  links: string[]
  year?: string  // only for On This Day
}

export interface MainPageSectionResult {
  section: string
  items: MainPageItem[]
  geojson: {
    type: 'FeatureCollection'
    features: MainPageFeature[]
  }
  total_items: number
  total_geocoded: number
}

export type MainPageSection = 'in_the_news' | 'on_this_day' | 'did_you_know'
