import { useQuery } from '@tanstack/react-query'

export type GdeltItem = {
  title?: string
  url?: string
  sourcecountry?: string
  seendate?: string
}

async function fetchGdelt(query: string): Promise<GdeltItem[]> {
  const params = new URLSearchParams({ query, mode: 'artlist', max_results: '8' })
  const res = await fetch(`/api/gdelt?${params.toString()}`)
  if (!res.ok) throw new Error('Failed to fetch GDELT data')
  return (await res.json()) as GdeltItem[]
}

export function useGdeltSearch(query: string) {
  return useQuery({
    queryKey: ['gdelt-search', query],
    queryFn: () => fetchGdelt(query),
    enabled: query.trim().length > 2,
    staleTime: 120_000,
  })
}
