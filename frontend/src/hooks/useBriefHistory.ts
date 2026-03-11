import { useQuery } from '@tanstack/react-query'
import type { BriefComparison, BriefHistoryItem } from '../api/types'

async function fetchBriefHistory(): Promise<BriefHistoryItem[]> {
  const res = await fetch('/api/brief/history?limit=12')
  if (!res.ok) throw new Error('Failed to fetch brief history')
  return (await res.json()) as BriefHistoryItem[]
}

async function fetchBriefComparison(firstId: number, secondId: number): Promise<BriefComparison | null> {
  const res = await fetch(`/api/brief/compare?first_id=${firstId}&second_id=${secondId}`)
  if (!res.ok) throw new Error('Failed to compare briefs')
  const payload = (await res.json()) as BriefComparison | { error: string }
  return 'error' in payload ? null : payload
}

export function useBriefHistory() {
  return useQuery({ queryKey: ['brief-history'], queryFn: fetchBriefHistory, refetchInterval: 60_000 })
}

export function useBriefComparison(firstId?: number, secondId?: number) {
  return useQuery({
    queryKey: ['brief-compare', firstId, secondId],
    queryFn: () => fetchBriefComparison(firstId!, secondId!),
    enabled: Boolean(firstId && secondId),
  })
}
