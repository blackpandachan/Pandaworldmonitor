import { useQuery } from '@tanstack/react-query'

export type LayerPayload = {
  layers: {
    conflicts?: Array<{ location: { latitude: number; longitude: number }; event_type: string }>
    natural?: Array<{ location: { latitude: number; longitude: number }; event_type: string }>
    fires?: Array<{ location: { latitude: number; longitude: number }; event_type: string }>
    bases?: Array<{ lat: number; lon: number; name: string; country?: string; type?: string }>
    outages?: {
      checks?: Record<string, { sample?: Record<string, unknown> }>
    }
    news?: Array<{ location?: { latitude: number; longitude: number } | null; title: string }>
  }
}

async function fetchMapLayers(layers: string[], hoursBack: number): Promise<LayerPayload> {
  const params = new URLSearchParams({ layers: layers.join(','), hours_back: String(hoursBack) })
  const res = await fetch(`/api/map/layers?${params.toString()}`)
  if (!res.ok) throw new Error('Failed to fetch map layers')
  return (await res.json()) as LayerPayload
}

export function useMapLayers(layerToggles: Record<string, boolean>, hoursBack: number) {
  const selected = Object.entries(layerToggles)
    .filter(([, enabled]) => enabled)
    .map(([name]) => name)

  return useQuery({
    queryKey: ['map-layers', selected.join(','), hoursBack],
    queryFn: () => fetchMapLayers(selected, hoursBack),
    staleTime: 60_000,
  })
}
