import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { InfrastructureStatus, WatchlistItem } from '../api/types'

async function fetchInfrastructure(): Promise<InfrastructureStatus> {
  const res = await fetch('/api/infrastructure')
  if (!res.ok) throw new Error('Failed to fetch infrastructure status')
  const payload = (await res.json()) as InfrastructureStatus
  return {
    generated_at: payload.generated_at,
    status: payload.status,
    checks: payload.checks || {},
  }
}

async function fetchWatchlist() {
  const res = await fetch('/api/watchlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'list' }),
  })
  if (!res.ok) throw new Error('Failed to fetch watchlist')
  return (await res.json()) as { items: WatchlistItem[] }
}

async function mutateWatchlist(action: 'add' | 'remove', item: WatchlistItem) {
  const res = await fetch('/api/watchlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, item }),
  })
  if (!res.ok) throw new Error('Failed watchlist mutation')
  return res.json()
}

export function useInfrastructureStatus() {
  return useQuery({ queryKey: ['infrastructure-status'], queryFn: fetchInfrastructure, refetchInterval: 120_000 })
}

export function useWatchlist() {
  return useQuery({ queryKey: ['watchlist'], queryFn: fetchWatchlist, refetchInterval: 60_000 })
}

export function useWatchlistMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ action, item }: { action: 'add' | 'remove'; item: WatchlistItem }) => mutateWatchlist(action, item),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['watchlist'] })
    },
  })
}
