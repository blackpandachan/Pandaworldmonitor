import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useDashboardState } from '../useDashboardState'

class MockSocket {
  static instances: MockSocket[] = []
  static OPEN = 1
  static CLOSED = 3
  readyState = 0
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  send = vi.fn()

  constructor(public url: string) {
    MockSocket.instances.push(this)
  }

  open() {
    this.readyState = MockSocket.OPEN
    this.onopen?.()
  }

  close() {
    this.readyState = MockSocket.CLOSED
    this.onclose?.()
  }

  emit(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent)
  }
}

describe('useDashboardState', () => {
  beforeEach(() => {
    MockSocket.instances = []
    vi.useFakeTimers()
    vi.stubGlobal('WebSocket', MockSocket as unknown as typeof WebSocket)
  })

  it('reconnects after websocket close and processes state update', () => {
    const { result } = renderHook(() => useDashboardState())

    expect(MockSocket.instances).toHaveLength(1)
    const first = MockSocket.instances[0]
    act(() => first.open())

    expect(result.current.isConnected).toBe(true)

    act(() => {
      first.emit({ type: 'state_update', data: { articles: [], risk_scores: [], convergence_alerts: [], watchlist_alerts: [], data_freshness: {} } })
    })
    expect(result.current.state?.articles).toEqual([])

    act(() => first.close())
    expect(result.current.isConnected).toBe(false)

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(MockSocket.instances).toHaveLength(2)
  })
})
