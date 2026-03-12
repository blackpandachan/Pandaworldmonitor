import { useMemo, useState } from 'react'
import type { BriefComparison, BriefHistoryItem, DashboardState, InfrastructureStatus, Severity, WatchlistItem } from '../../api/types'
import type { GdeltItem } from '../../hooks/useGdeltSearch'

const severityClass: Record<Severity, string> = {
  critical: 'badge critical',
  high: 'badge high',
  medium: 'badge medium',
  low: 'badge low',
  info: 'badge info',
}

function timeAgo(iso: string): string {
  const ts = new Date(iso).getTime()
  if (Number.isNaN(ts)) return 'n/a'
  const diff = Date.now() - ts
  const mins = Math.max(1, Math.round(diff / 60_000))
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.round(hrs / 24)}d ago`
}

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((token) => token.length > 3)
}

export function ToplinePanel({ state }: { state: DashboardState | null }) {
  const articles = state?.articles ?? []
  const critical = articles.filter((a) => a.classification?.severity === 'critical').length
  const high = articles.filter((a) => a.classification?.severity === 'high').length
  const staleSources = Object.keys(state?.data_freshness ?? {}).length

  return (
    <section className="card topline">
      <div>
        <small>Critical</small>
        <strong>{critical}</strong>
      </div>
      <div>
        <small>High</small>
        <strong>{high}</strong>
      </div>
      <div>
        <small>Articles</small>
        <strong>{articles.length}</strong>
      </div>
      <div>
        <small>Live Sources</small>
        <strong>{staleSources}</strong>
      </div>
    </section>
  )
}

export function BriefPanel({ state }: { state: DashboardState | null }) {
  const text = state?.last_brief?.brief_text || state?.last_brief?.brief || 'No brief generated yet.'
  return (
    <section className="card featured">
      <div className="card-head"><h3>Situation Brief</h3><span>{state?.last_brief?.generated_at ? timeAgo(state.last_brief.generated_at) : 'n/a'}</span></div>
      <p className="brief-text">{text}</p>
    </section>
  )
}

export function DeltaPanel({ state }: { state: DashboardState | null }) {
  return (
    <section className="card">
      <div className="card-head"><h3>Delta Signals</h3><span>24h</span></div>
      <div className="metric-grid">
        <div><strong>{state?.convergence_alerts.length ?? 0}</strong><small>Convergence</small></div>
        <div><strong>{state?.watchlist_alerts.length ?? 0}</strong><small>Watchlist</small></div>
        <div><strong>{Object.keys(state?.data_freshness ?? {}).length}</strong><small>Data Sources</small></div>
      </div>
    </section>
  )
}

export function NewsPanel({ state }: { state: DashboardState | null }) {
  const [severityFilter, setSeverityFilter] = useState<'all' | Severity>('all')
  const articles = state?.articles ?? []

  const filtered = useMemo(
    () => (severityFilter === 'all' ? articles : articles.filter((a) => (a.classification?.severity || 'info') === severityFilter)),
    [articles, severityFilter],
  )

  return (
    <section className="card">
      <div className="card-head"><h3>Priority Feed</h3><span>{filtered.length} shown</span></div>
      <div className="tabs">
        {['all', 'critical', 'high', 'medium'].map((s) => (
          <button
            key={s}
            className={`tab ${severityFilter === s ? 'active' : ''}`}
            onClick={() => setSeverityFilter(s as 'all' | Severity)}
          >
            {s}
          </button>
        ))}
      </div>
      <div className="stack">
        {filtered.slice(0, 8).map((article) => (
          <article key={article.id} className="news-item">
            <span className={severityClass[article.classification?.severity || 'info']}>{article.classification?.severity || 'info'}</span>
            <div>
              <p>{article.title}</p>
              <small>{article.source} • {timeAgo(article.published_at)}</small>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

export function RiskPanel({
  state,
  onCountrySelect,
}: {
  state: DashboardState | null
  onCountrySelect?: (countryCode: string) => void
}) {
  return (
    <section className="card">
      <div className="card-head"><h3>Country Risk</h3><span>CII-like</span></div>
      <div className="stack">
        {(state?.risk_scores ?? []).map((r) => (
          <div key={r.country_code} className="risk-row">
            <div>
              <button className="link-like" onClick={() => onCountrySelect?.(r.country_code)}>{r.country_code}</button>
              <small>{r.trend}</small>
            </div>
            <div className="risk-bar"><span style={{ width: `${Math.min(100, r.score)}%` }} /></div>
            <strong>{r.score.toFixed(0)}</strong>
          </div>
        ))}
      </div>
    </section>
  )
}

export function AlertsPanel({ state }: { state: DashboardState | null }) {
  return (
    <section className="card">
      <div className="card-head"><h3>Convergence Alerts</h3><span>{state?.convergence_alerts.length ?? 0}</span></div>
      <div className="stack">
        {(state?.convergence_alerts ?? []).slice(0, 5).map((a, idx) => (
          <div className="alert-item" key={`${a.location_name}-${idx}`}>
            <strong>{a.location_name}</strong>
            <p>{a.explanation || 'Multi-signal convergence active.'}</p>
            <small>Score {a.score.toFixed(1)}</small>
          </div>
        ))}
      </div>
    </section>
  )
}

export function BriefHistoryPanel({
  items,
  selected,
  onSelect,
  comparison,
}: {
  items: BriefHistoryItem[]
  selected: [number | undefined, number | undefined]
  onSelect: (slot: 0 | 1, id: number) => void
  comparison: BriefComparison | null | undefined
}) {
  const [detailId, setDetailId] = useState<number | null>(null)
  const detailBrief = useMemo(() => items.find((item) => item.id === detailId) ?? null, [detailId, items])

  const sharedTerms = useMemo(() => {
    if (!comparison) return []
    const first = new Set(tokenize(comparison.first.brief_text))
    const second = new Set(tokenize(comparison.second.brief_text))
    return Array.from(first).filter((term) => second.has(term)).slice(0, 24)
  }, [comparison])

  return (
    <section className="card">
      <div className="card-head"><h3>Brief History & Compare</h3><span>{items.length}</span></div>
      <div className="brief-picks">
        <select value={selected[0] ?? ''} onChange={(e) => onSelect(0, Number(e.target.value))}>
          <option value="">Select A</option>
          {items.map((item) => <option key={`a-${item.id}`} value={item.id}>#{item.id} {item.type}</option>)}
        </select>
        <select value={selected[1] ?? ''} onChange={(e) => onSelect(1, Number(e.target.value))}>
          <option value="">Select B</option>
          {items.map((item) => <option key={`b-${item.id}`} value={item.id}>#{item.id} {item.type}</option>)}
        </select>
      </div>

      <div className="brief-list">
        {items.slice(0, 8).map((item) => (
          <button key={item.id} className="brief-row" onClick={() => setDetailId(item.id)}>
            <strong>#{item.id} {item.type}</strong>
            <small>{timeAgo(item.generated_at)}</small>
          </button>
        ))}
      </div>

      {comparison && (
        <div className="compare-box">
          <small>Shared terms: {comparison.summary.shared_terms}</small>
          <div className="term-group">
            <strong>Added</strong>
            <div className="term-chips">
              {comparison.summary.added_terms.slice(0, 16).map((term) => <span className="term-chip added" key={`a-${term}`}>+ {term}</span>)}
            </div>
          </div>
          <div className="term-group">
            <strong>Removed</strong>
            <div className="term-chips">
              {comparison.summary.removed_terms.slice(0, 16).map((term) => <span className="term-chip removed" key={`r-${term}`}>- {term}</span>)}
            </div>
          </div>
          <div className="term-group">
            <strong>Still prominent</strong>
            <div className="term-chips">
              {sharedTerms.map((term) => <span className="term-chip shared" key={`s-${term}`}>{term}</span>)}
            </div>
          </div>
        </div>
      )}

      {detailBrief && (
        <div className="brief-drawer">
          <div className="card-head">
            <h3>Brief #{detailBrief.id}</h3>
            <button className="chip" onClick={() => setDetailId(null)}>Close</button>
          </div>
          <small>{detailBrief.type} • {detailBrief.country || detailBrief.region || 'global'} • {detailBrief.model} • {timeAgo(detailBrief.generated_at)}</small>
          <p className="brief-text full">{detailBrief.brief_text}</p>
        </div>
      )}
    </section>
  )
}

export function InfrastructurePanel({ data }: { data: InfrastructureStatus | undefined }) {
  return (
    <section className="card">
      <div className="card-head"><h3>Infrastructure Status</h3><span>{data?.generated_at ? timeAgo(data.generated_at) : (data?.status || 'n/a')}</span></div>
      <div className="stack">
        {Object.entries(data?.checks ?? {}).map(([name, check]) => {
          const ok = check.available || check.status === 'ok'
          return (
            <div className="infra-row" key={name}>
              <strong>{name.replace(/_/g, ' ')}</strong>
              <span className={`status-pill ${ok ? 'ok' : 'warn'}`}>{ok ? 'ok' : 'degraded'}</span>
            </div>
          )
        })}
      </div>
    </section>
  )
}

export function WatchlistPanel({
  items,
  onAdd,
  onRemove,
}: {
  items: WatchlistItem[]
  onAdd: (item: WatchlistItem) => void
  onRemove: (item: WatchlistItem) => void
}) {
  const [type, setType] = useState<WatchlistItem['type']>('country')
  const [value, setValue] = useState('')
  const [severity, setSeverity] = useState<WatchlistItem['notify_severity']>('medium')

  return (
    <section className="card">
      <div className="card-head"><h3>Watchlist</h3><span>{items.length} tracked</span></div>
      <div className="watchlist-form">
        <select aria-label="watchlist type" value={type} onChange={(e) => setType(e.target.value as WatchlistItem['type'])}>
          <option value="country">Country</option>
          <option value="region">Region</option>
          <option value="topic">Topic</option>
          <option value="entity">Entity</option>
        </select>
        <input aria-label="watchlist value" value={value} onChange={(e) => setValue(e.target.value)} placeholder="e.g. Ukraine" />
        <select aria-label="watchlist severity" value={severity} onChange={(e) => setSeverity(e.target.value as WatchlistItem['notify_severity'])}>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <button
          className="button"
          onClick={() => {
            if (!value.trim()) return
            onAdd({ type, value: value.trim(), notify_severity: severity })
            setValue('')
            setSeverity('medium')
          }}
        >
          Add
        </button>
      </div>
      <div className="stack">
        {items.slice(0, 8).map((item) => (
          <div className="watch-item" key={`${item.type}-${item.value}`}>
            <span>{item.type}: <strong>{item.value}</strong> <small>({item.notify_severity})</small></span>
            <button className="chip" onClick={() => onRemove(item)}>Remove</button>
          </div>
        ))}
      </div>
    </section>
  )
}

export function GdeltPanel({
  query,
  onQueryChange,
  results,
  loading,
}: {
  query: string
  onQueryChange: (value: string) => void
  results: GdeltItem[]
  loading: boolean
}) {
  return (
    <section className="card">
      <div className="card-head"><h3>GDELT Search</h3><span>{results.length} hits</span></div>
      <div className="gdelt-form">
        <input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Search entity / location / incident"
        />
      </div>
      {loading && <small>Searching…</small>}
      <div className="stack">
        {results.slice(0, 6).map((row, idx) => (
          <a className="gdelt-item" href={row.url || '#'} target="_blank" rel="noreferrer" key={`${row.url || row.title}-${idx}`}>
            <strong>{row.title || 'Untitled result'}</strong>
            <small>{row.sourcecountry || 'unknown source'} • {row.seendate ? timeAgo(row.seendate) : 'n/a'}</small>
          </a>
        ))}
      </div>
    </section>
  )
}
