import { useMemo, useState } from 'react'
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
import { useBriefComparison, useBriefHistory } from './hooks/useBriefHistory'
import { useDashboardState } from './hooks/useDashboardState'
import { useGdeltSearch } from './hooks/useGdeltSearch'
import { useInfrastructureStatus, useWatchlist, useWatchlistMutation } from './hooks/useOpsData'

const layerDefaults: Record<string, boolean> = {
  conflicts: true,
  natural: true,
  fires: true,
  outages: true,
  bases: true,
  news: true,
}

export function App() {
  const { state, isConnected, requestBrief } = useDashboardState()
  const [layers, setLayers] = useState<Record<string, boolean>>(layerDefaults)
  const [hoursBack, setHoursBack] = useState(24)
  const [selectedBriefs, setSelectedBriefs] = useState<[number | undefined, number | undefined]>([undefined, undefined])
  const [gdeltQuery, setGdeltQuery] = useState('Red Sea shipping')

  const briefHistory = useBriefHistory()
  const comparison = useBriefComparison(selectedBriefs[0], selectedBriefs[1])
  const infra = useInfrastructureStatus()
  const watchlist = useWatchlist()
  const watchlistMutation = useWatchlistMutation()
  const gdelt = useGdeltSearch(gdeltQuery)

  const selectedLayerCount = useMemo(() => Object.values(layers).filter(Boolean).length, [layers])

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
                  {name}
                </button>
              ))}
            </div>
          </div>
          <MapView layerToggles={layers} hoursBack={hoursBack} />
        </section>

        <aside className="sidebar">
          <BriefPanel state={state} />
          <DeltaPanel state={state} />
          <NewsPanel state={state} />
          <RiskPanel state={state} />
          <AlertsPanel state={state} />
          <InfrastructurePanel data={infra.data} />
          <GdeltPanel query={gdeltQuery} onQueryChange={setGdeltQuery} results={gdelt.data ?? []} loading={gdelt.isFetching} />
          <WatchlistPanel
            items={watchlist.data?.items ?? []}
            onAdd={(item) => watchlistMutation.mutate({ action: 'add', item })}
            onRemove={(item) => watchlistMutation.mutate({ action: 'remove', item })}
          />
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
        </aside>
      </main>
    </div>
  )
}
