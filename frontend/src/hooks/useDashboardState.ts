import { useEffect, useRef, useState } from 'react'
import type { DashboardState } from '../api/types'

function getWsUrl(): string {
  const configured = import.meta.env.VITE_WS_URL as string | undefined
  if (configured) return configured
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/ws`
}

export function useDashboardState() {
  const [state, setState] = useState<DashboardState | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const ws = new WebSocket(getWsUrl())
    wsRef.current = ws
    ws.onopen = () => setIsConnected(true)
    ws.onclose = () => setIsConnected(false)
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data) as { type: string; data: DashboardState }
      if (message.type === 'state_update') setState(message.data)
      if (message.type === 'brief') {
        setState((prev) => (prev ? { ...prev, last_brief: message.data as unknown as DashboardState['last_brief'] } : prev))
      }
    }
    return () => ws.close()
  }, [])

  const requestBrief = (params: { region?: string; country?: string; hours_back?: number }) => {
    wsRef.current?.send(JSON.stringify({ type: 'request_brief', params }))
  }

  return { state, isConnected, requestBrief }
}
