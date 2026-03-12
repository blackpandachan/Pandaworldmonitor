import { useCallback, useEffect, useRef, useState } from 'react'
import type { DashboardState } from '../api/types'

type WsMessage =
  | { type: 'state_update'; data: DashboardState }
  | { type: 'brief'; data: DashboardState['last_brief'] }
  | { type: 'alert'; data: unknown }

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
  const reconnectAttemptRef = useRef(0)
  const reconnectTimerRef = useRef<number | null>(null)

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
  }, [])

  const connect = useCallback(() => {
    clearReconnectTimer()

    const ws = new WebSocket(getWsUrl())
    wsRef.current = ws

    ws.onopen = () => {
      reconnectAttemptRef.current = 0
      setIsConnected(true)
    }

    ws.onclose = () => {
      setIsConnected(false)
      const attempt = reconnectAttemptRef.current
      const backoffMs = Math.min(10_000, 1000 * 2 ** attempt)
      reconnectAttemptRef.current = attempt + 1
      reconnectTimerRef.current = window.setTimeout(connect, backoffMs)
    }

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data) as WsMessage
      if (message.type === 'state_update') {
        setState(message.data)
      }
      if (message.type === 'brief') {
        setState((prev) => (prev ? { ...prev, last_brief: message.data } : prev))
      }
    }
  }, [clearReconnectTimer])

  useEffect(() => {
    connect()

    return () => {
      clearReconnectTimer()
      wsRef.current?.close()
    }
  }, [clearReconnectTimer, connect])

  const requestBrief = (params: { region?: string; country?: string; hours_back?: number }) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'request_brief', params }))
  }

  return { state, isConnected, requestBrief }
}
