import { useEffect, useMemo, useState } from 'react'
import { MapView } from './components/map/MapView'
import {
  AlertsPanel,
  BriefHistoryPanel,
  BriefPanel,
  DeltaPanel,
  GdeltPanel,
  InfrastructurePanel,
  NewsPanel,
  RiskPanel,
  ToplinePanel,
  WatchlistPanel,
} from './components/panels/Panels'
import type { WatchlistItem } from './api/types'
import { useBriefComparison, useBriefHistory } from './hooks/useBriefHistory'
import { useDashboardState } from './hooks/useDashboardState'
import { useGdeltSearch } from './hooks/useGdeltSearch'
import { useMapLayers } from './hooks/useMapLayers'
import { useInfrastructureStatus, useWatchlist, useWatchlistMutation } from './hooks/useOpsData'

const layerDefaults: Record<string, boolean> = {
  conflicts: true,
  natural: true,
  fires: true,
  outages: true,
  bases: true,
  news: true,
}

type MobilePanelKey = 'brief' | 'news' | 'risk' | 'alerts' | 'watchlist' | 'history'

const mobilePanelTabs: Array<{ key: MobilePanelKey; label: string }> = [
  { key: 'brief', label: 'Briefs' },
  { key: 'news', label: 'News' },
  { key: 'risk', label: 'Risk' },
  { key: 'alerts', label: 'Alerts' },
  { key: 'watchlist', label: 'Watch' },
  { key: 'history', label: 'History' },
]

type Toast = { id: number; kind: 'success' | 'error'; text: string }

export function App() {
  const { state, isConnected, requestBrief } = useDashboardState()
  const [layers, setLayers] = useState<Record<string, boolean>>(layerDefaults)
  const [hoursBack, setHoursBack] = useState(24)
  const [selectedBriefs, setSelectedBriefs] = useState<[number | undefined, number | undefined]>([undefined, undefined])
  const [gdeltQuery, setGdeltQuery] = useState('Red Sea shipping')
  const [mobilePanel, setMobilePanel] = useState<MobilePanelKey>('brief')
  const [isMobile, setIsMobile] = useState(typeof window !== 'undefined' ? window.innerWidth <= 700 : false)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [optimisticWatchlist, setOptimisticWatchlist] = useState<WatchlistItem[] | null>(null)

  const briefHistory = useBriefHistory()
  const comparison = useBriefComparison(selectedBriefs[0], selectedBriefs[1])
  const infra = useInfrastructureStatus()
  const watchlist = useWatchlist()
  const watchlistMutation = useWatchlistMutation()
  const gdelt = useGdeltSearch(gdeltQuery)
  const mapLayers = useMapLayers(layers, hoursBack)

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= 700)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    if (watchlist.data?.items) setOptimisticWatchlist(watchlist.data.items)
  }, [watchlist.data?.items])

  const selectedLayerCount = useMemo(() => Object.values(layers).filter(Boolean).length, [layers])

  const layerLegendCounts = useMemo(() => {
    const payload = mapLayers.data?.layers
    return {
      conflicts: payload?.conflicts?.length ?? 0,
      natural: payload?.natural?.length ?? 0,
      fires: payload?.fires?.length ?? 0,
      outages: Object.keys(payload?.outages?.checks ?? {}).length,
      bases: payload?.bases?.length ?? 0,
      news: payload?.news?.filter((item) => Boolean(item.location)).length ?? 0,
    }
  }, [mapLayers.data])

  const activeWatchlist = optimisticWatchlist ?? watchlist.data?.items ?? []

  const pushToast = (kind: Toast['kind'], text: string) => {
    const id = Date.now() + Math.floor(Math.random() * 1000)
    setToasts((prev) => [...prev, { id, kind, text }])
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id))
    }, 2800)
  }

  const handleAddWatchlist = async (item: WatchlistItem) => {
    const prev = activeWatchlist
    setOptimisticWatchlist((current) => {
      const base = current ?? watchlist.data?.items ?? []
      if (base.some((entry) => entry.type === item.type && entry.value.toLowerCase() === item.value.toLowerCase())) return base
      return [...base, item]
    })
    try {
      await watchlistMutation.mutateAsync({ action: 'add', item })
      pushToast('success', `Added ${item.value} to watchlist`)
    } catch {
      setOptimisticWatchlist(prev)
      pushToast('error', `Failed to add ${item.value}`)
    }
  }

  const handleRemoveWatchlist = async (item: WatchlistItem) => {
    const prev = activeWatchlist
    setOptimisticWatchlist((current) => (current ?? watchlist.data?.items ?? []).filter((entry) => !(entry.type === item.type && entry.value === item.value)))
    try {
      await watchlistMutation.mutateAsync({ action: 'remove', item })
      pushToast('success', `Removed ${item.value} from watchlist`)
    } catch {
      setOptimisticWatchlist(prev)
      pushToast('error', `Failed to remove ${item.value}`)
    }
  }

  const desktopPanels = (
    <>
      <BriefPanel state={state} />
      <DeltaPanel state={state} />
      <NewsPanel state={state} />
      <RiskPanel state={state} onCountrySelect={(country) => requestBrief({ country, hours_back: hoursBack })} />
      <AlertsPanel state={state} />
      <InfrastructurePanel data={infra.data} />
      <GdeltPanel query={gdeltQuery} onQueryChange={setGdeltQuery} results={gdelt.data ?? []} loading={gdelt.isFetching} />
      <WatchlistPanel items={activeWatchlist} onAdd={handleAddWatchlist} onRemove={handleRemoveWatchlist} />
      <BriefHistoryPanel
        items={briefHistory.data ?? []}
        selected={selectedBriefs}
        onSelect={(slot, id) =>
          setSelectedBriefs((prev) => {
            const next: [number | undefined, number | undefined] = [...prev]
            next[slot] = Number.isFinite(id) ? id : undefined
            return next
          })
        }
        comparison={comparison.data}
      />
    </>
  )

  const mobilePanelContent = (
    <>
      {mobilePanel === 'brief' && (
        <>
          <BriefPanel state={state} />
          <DeltaPanel state={state} />
          <InfrastructurePanel data={infra.data} />
        </>
      )}
      {mobilePanel === 'news' && <NewsPanel state={state} />}
      {mobilePanel === 'risk' && <RiskPanel state={state} onCountrySelect={(country) => requestBrief({ country, hours_back: hoursBack })} />}
      {mobilePanel === 'alerts' && (
        <>
          <AlertsPanel state={state} />
          <GdeltPanel query={gdeltQuery} onQueryChange={setGdeltQuery} results={gdelt.data ?? []} loading={gdelt.isFetching} />
        </>
      )}
      {mobilePanel === 'watchlist' && <WatchlistPanel items={activeWatchlist} onAdd={handleAddWatchlist} onRemove={handleRemoveWatchlist} />}
      {mobilePanel === 'history' && (
        <BriefHistoryPanel
          items={briefHistory.data ?? []}
          selected={selectedBriefs}
          onSelect={(slot, id) =>
            setSelectedBriefs((prev) => {
              const next: [number | undefined, number | undefined] = [...prev]
              next[slot] = Number.isFinite(id) ? id : undefined
              return next
            })
          }
          comparison={comparison.data}
        />
      )}
    </>
  )

  return (
    <div className="app-shell">
      <header className="header glass">
        <div>
          <p className="eyebrow">Sentinel</p>
          <strong>World Monitor Intelligence Dashboard</strong>
          <p className="subhead">Delta-first global situational awareness for analysts</p>
        </div>
        <div className="toolbar">
          <select value={hoursBack} onChange={(e) => setHoursBack(Number(e.target.value))}>
            <option value={6}>Last 6h</option>
            <option value={24}>Last 24h</option>
            <option value={48}>Last 48h</option>
          </select>
          <button className="button" onClick={() => requestBrief({ region: 'global', hours_back: hoursBack })}>Generate Brief</button>
          <span className={`status-dot ${isConnected ? 'online' : 'offline'}`}>{isConnected ? 'Live' : 'Disconnected'}</span>
        </div>
      </header>

      <main className="main">
        <section className="map-column">
          <ToplinePanel state={state} />
          <div className="card glass controls-card">
            <div className="card-head"><h3>Map Layers</h3><span>{selectedLayerCount}/6 active</span></div>
            <div className="chips">
              {Object.entries(layers).map(([name, enabled]) => (
                <button key={name} className={`chip ${enabled ? 'active' : ''}`} onClick={() => setLayers((prev) => ({ ...prev, [name]: !prev[name] }))}>
                  {name} <span className="chip-count">{layerLegendCounts[name as keyof typeof layerLegendCounts] ?? 0}</span>
                </button>
              ))}
            </div>
          </div>
          <MapView layerToggles={layers} hoursBack={hoursBack} />
        </section>

        <aside className={`sidebar ${isMobile ? 'mobile-sheet' : ''}`}>
          {isMobile ? mobilePanelContent : desktopPanels}
        </aside>
      </main>

      {isMobile && (
        <nav className="mobile-tabs" aria-label="Dashboard panel navigation">
          {mobilePanelTabs.map((tab) => (
            <button
              key={tab.key}
              className={`mobile-tab ${mobilePanel === tab.key ? 'active' : ''}`}
              onClick={() => setMobilePanel(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      )}

      <div className="toast-stack" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast ${toast.kind}`}>
            {toast.text}
          </div>
        ))}
      </div>
    </div>
  )
}
