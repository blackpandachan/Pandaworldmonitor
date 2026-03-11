import { useEffect, useMemo, useRef, useState } from 'react'
import maplibregl, { type GeoJSONSource, type Map as MaplibreMap } from 'maplibre-gl'
import type { FeatureCollection, Point } from 'geojson'
import { useMapLayers } from '../../hooks/useMapLayers'

type Props = { layerToggles: Record<string, boolean>; hoursBack: number }

const layerLabels: Record<string, string> = {
  conflicts: 'Active conflicts',
  natural: 'Natural hazards',
  fires: 'Wildfires',
  outages: 'Outages',
  bases: 'Military bases',
  news: 'News pins',
}

function toFeatureCollection(points: Array<{ latitude: number; longitude: number; kind: string; label: string }>): FeatureCollection<Point> {
  return {
    type: 'FeatureCollection',
    features: points.map((point) => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [point.longitude, point.latitude] },
      properties: { kind: point.kind, label: point.label },
    })),
  }
}

export function MapView({ layerToggles, hoursBack }: Props) {
  const ref = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<MaplibreMap | null>(null)
  const { data } = useMapLayers(layerToggles, hoursBack)
  const [mapReady, setMapReady] = useState(false)
  const [mapError, setMapError] = useState<string | null>(null)

  const activeLayers = useMemo(
    () => Object.entries(layerToggles).filter(([, enabled]) => enabled).map(([key]) => layerLabels[key]),
    [layerToggles],
  )

  useEffect(() => {
    if (!ref.current || mapRef.current) return
    const map = new maplibregl.Map({
      container: ref.current,
      style: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
      center: [20, 15],
      zoom: 1.5,
      attributionControl: false,
    })

    map.on('error', (event) => {
      const message = (event.error as Error | undefined)?.message || 'Map rendering error'
      setMapError(message)
    })

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right')

    map.on('load', () => {
      setMapReady(true)
      map.addSource('sentinel-points', { type: 'geojson', data: toFeatureCollection([]) })
      map.addLayer({
        id: 'sentinel-points-layer',
        type: 'circle',
        source: 'sentinel-points',
        paint: {
          'circle-radius': ['match', ['get', 'kind'], 'conflict', 6, 'natural', 5, 'news', 4, 4],
          'circle-color': ['match', ['get', 'kind'], 'conflict', '#dc2626', 'natural', '#f59e0b', 'news', '#2563eb', '#0f172a'],
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff',
          'circle-opacity': 0.92,
        },
      })
    })

    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return

    const conflicts = (data?.layers.conflicts ?? []).map((item) => ({
      latitude: item.location.latitude,
      longitude: item.location.longitude,
      kind: 'conflict',
      label: item.event_type,
    }))
    const natural = (data?.layers.natural ?? []).map((item) => ({
      latitude: item.location.latitude,
      longitude: item.location.longitude,
      kind: 'natural',
      label: item.event_type,
    }))
    const news = (data?.layers.news ?? [])
      .filter((item) => item.location)
      .map((item) => ({
        latitude: item.location!.latitude,
        longitude: item.location!.longitude,
        kind: 'news',
        label: item.title,
      }))

    const source = map.getSource('sentinel-points') as GeoJSONSource | undefined
    if (source) source.setData(toFeatureCollection([...conflicts, ...natural, ...news]))
  }, [data])

  return (
    <div className="map-wrap">
      <div className="map" ref={ref} data-layers={JSON.stringify(layerToggles)} />
      {!mapReady && <div className="map-status">Loading basemap…</div>}
      {mapError && <div className="map-status error">{mapError}</div>}
      <aside className="map-overlay">
        <h4>Live Layers</h4>
        {activeLayers.length ? (
          <ul>
            {activeLayers.map((label) => (
              <li key={label}>{label}</li>
            ))}
          </ul>
        ) : (
          <p>No active layers</p>
        )}
      </aside>
    </div>
  )
}
