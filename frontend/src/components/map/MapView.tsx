import { useEffect, useMemo, useRef, useState } from 'react'
import maplibregl, { type GeoJSONSource, type Map as MaplibreMap, Popup } from 'maplibre-gl'
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

type MapPoint = { latitude: number; longitude: number; kind: string; label: string }

function toFeatureCollection(points: MapPoint[]): FeatureCollection<Point> {
  return {
    type: 'FeatureCollection',
    features: points.map((point) => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [point.longitude, point.latitude] },
      properties: { kind: point.kind, label: point.label },
    })),
  }
}

function pickOutagePoints(checks: Record<string, { sample?: Record<string, unknown> }> | undefined): MapPoint[] {
  if (!checks) return []
  return Object.entries(checks)
    .map(([name, check]) => {
      const sample = check.sample
      if (!sample) return null
      const latitude = Number(sample.latitude ?? sample.lat)
      const longitude = Number(sample.longitude ?? sample.lon)
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null
      return {
        latitude,
        longitude,
        kind: 'outage',
        label: `Outage (${name.replace(/_/g, ' ')})`,
      }
    })
    .filter((point): point is MapPoint => point !== null)
}

export function MapView({ layerToggles, hoursBack }: Props) {
  const ref = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<MaplibreMap | null>(null)
  const popupRef = useRef<Popup | null>(null)
  const { data } = useMapLayers(layerToggles, hoursBack)
  const [mapReady, setMapReady] = useState(false)
  const [mapError, setMapError] = useState<string | null>(null)

  const activeLayers = useMemo(
    () => Object.entries(layerToggles).filter(([, enabled]) => enabled).map(([key]) => layerLabels[key]),
    [layerToggles],
  )

  const pointCounts = useMemo(() => {
    const conflicts = data?.layers.conflicts?.length ?? 0
    const natural = data?.layers.natural?.length ?? 0
    const fires = data?.layers.fires?.length ?? 0
    const bases = data?.layers.bases?.length ?? 0
    const news = data?.layers.news?.filter((item) => Boolean(item.location)).length ?? 0
    return { conflicts, natural, fires, bases, news }
  }, [data])

  useEffect(() => {
    if (!ref.current || mapRef.current) return
    const map = new maplibregl.Map({
      container: ref.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
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

      map.addSource('countries', {
        type: 'geojson',
        data: '/data/countries.geojson',
      })
      map.addLayer({
        id: 'countries-fill',
        type: 'fill',
        source: 'countries',
        paint: {
          'fill-color': '#111827',
          'fill-opacity': 0.12,
        },
      })
      map.addLayer({
        id: 'countries-line',
        type: 'line',
        source: 'countries',
        paint: {
          'line-color': '#334155',
          'line-width': 0.7,
          'line-opacity': 0.55,
        },
      })

      map.addSource('sentinel-points', {
        type: 'geojson',
        data: toFeatureCollection([]),
        cluster: true,
        clusterMaxZoom: 5,
        clusterRadius: 40,
      })

      map.addLayer({
        id: 'sentinel-clusters',
        type: 'circle',
        source: 'sentinel-points',
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': ['step', ['get', 'point_count'], '#3b82f6', 25, '#8b5cf6', 75, '#ef4444'],
          'circle-radius': ['step', ['get', 'point_count'], 12, 25, 16, 75, 20],
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff',
        },
      })

      map.addLayer({
        id: 'sentinel-cluster-count',
        type: 'symbol',
        source: 'sentinel-points',
        filter: ['has', 'point_count'],
        layout: {
          'text-field': '{point_count_abbreviated}',
          'text-size': 11,
        },
        paint: {
          'text-color': '#ffffff',
        },
      })

      map.addLayer({
        id: 'sentinel-unclustered',
        type: 'circle',
        source: 'sentinel-points',
        filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-radius': ['match', ['get', 'kind'], 'conflict', 6, 'natural', 5, 'fire', 5, 'base', 4, 'outage', 6, 'news', 4, 4],
          'circle-color': ['match', ['get', 'kind'], 'conflict', '#dc2626', 'natural', '#f59e0b', 'fire', '#fb7185', 'base', '#22c55e', 'outage', '#a78bfa', 'news', '#60a5fa', '#0f172a'],
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff',
          'circle-opacity': 0.92,
        },
      })

      map.on('click', 'sentinel-clusters', async (event) => {
        const feature = event.features?.[0]
        if (!feature) return
        const clusterId = Number(feature.properties?.cluster_id)
        const source = map.getSource('sentinel-points') as GeoJSONSource
        try {
          const zoom = await source.getClusterExpansionZoom(clusterId)
          if (feature.geometry.type !== 'Point') return
          map.easeTo({ center: feature.geometry.coordinates as [number, number], zoom })
        } catch {
          return
        }
      })

      map.on('mouseenter', 'sentinel-clusters', () => {
        map.getCanvas().style.cursor = 'pointer'
      })
      map.on('mouseleave', 'sentinel-clusters', () => {
        map.getCanvas().style.cursor = ''
      })
      map.on('mouseenter', 'sentinel-unclustered', () => {
        map.getCanvas().style.cursor = 'pointer'
      })
      map.on('mouseleave', 'sentinel-unclustered', () => {
        map.getCanvas().style.cursor = ''
      })
      map.on('click', 'sentinel-unclustered', (event) => {
        const feature = event.features?.[0]
        if (!feature) return
        if (feature.geometry.type !== 'Point') return
        const coordinates = feature.geometry.coordinates as [number, number]
        const label = String((feature.properties as Record<string, unknown>)?.label ?? 'Event')
        popupRef.current?.remove()
        popupRef.current = new Popup({ closeButton: false, closeOnClick: true })
          .setLngLat(coordinates)
          .setHTML(`<div class="map-popup">${label}</div>`)
          .addTo(map)
      })
    })

    mapRef.current = map
    return () => {
      popupRef.current?.remove()
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
    const fires = (data?.layers.fires ?? []).map((item) => ({
      latitude: item.location.latitude,
      longitude: item.location.longitude,
      kind: 'fire',
      label: item.event_type,
    }))
    const bases = (data?.layers.bases ?? []).map((item) => ({
      latitude: item.lat,
      longitude: item.lon,
      kind: 'base',
      label: item.name,
    }))
    const outages = pickOutagePoints(data?.layers.outages?.checks)
    const news = (data?.layers.news ?? [])
      .filter((item) => item.location)
      .map((item) => ({
        latitude: item.location!.latitude,
        longitude: item.location!.longitude,
        kind: 'news',
        label: item.title,
      }))

    const source = map.getSource('sentinel-points') as GeoJSONSource | undefined
    if (source) source.setData(toFeatureCollection([...conflicts, ...natural, ...fires, ...outages, ...bases, ...news]))
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
        <div className="map-counts">
          <small>Conflicts: {pointCounts.conflicts}</small>
          <small>Natural: {pointCounts.natural}</small>
          <small>Fires: {pointCounts.fires}</small>
          <small>Bases: {pointCounts.bases}</small>
          <small>News pins: {pointCounts.news}</small>
        </div>
      </aside>
    </div>
  )
}
