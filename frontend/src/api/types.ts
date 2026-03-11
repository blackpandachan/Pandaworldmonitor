export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'

export type DashboardState = {
  articles: Array<{
    id: string
    title: string
    source: string
    published_at: string
    classification?: { severity: Severity; category: string } | null
  }>
  risk_scores: Array<{ country_code: string; score: number; trend: string }>
  convergence_alerts: Array<{ location_name: string; score: number; explanation?: string }>
  watchlist_alerts: Array<{ message?: string; severity?: Severity; title?: string; reason?: string }>
  data_freshness: Record<string, string>
  last_brief?: { brief_text?: string; brief?: string; generated_at: string } | null
}

export type BriefHistoryItem = {
  id: number
  type: 'situation' | 'delta'
  region: string | null
  country: string | null
  brief_text: string
  model: string
  generated_at: string
}

export type BriefComparison = {
  first: BriefHistoryItem
  second: BriefHistoryItem
  summary: {
    shared_terms: number
    added_terms: string[]
    removed_terms: string[]
  }
}

export type InfrastructureStatus = {
  generated_at?: string
  status?: string
  checks: Record<string, {
    available?: boolean
    status?: string
    summary?: string
    sample?: Record<string, unknown>
  }>
}

export type WatchlistItem = {
  type: 'region' | 'country' | 'topic' | 'entity'
  value: string
  notify_severity: 'critical' | 'high' | 'medium' | 'low'
}
