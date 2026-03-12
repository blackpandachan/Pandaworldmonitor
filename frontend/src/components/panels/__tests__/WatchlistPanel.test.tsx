import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { WatchlistPanel } from '../Panels'

describe('WatchlistPanel', () => {
  it('submits selected severity with new watch item', () => {
    const onAdd = vi.fn()
    const onRemove = vi.fn()

    render(<WatchlistPanel items={[]} onAdd={onAdd} onRemove={onRemove} />)

    fireEvent.change(screen.getByLabelText('watchlist type'), { target: { value: 'country' } })
    fireEvent.change(screen.getByLabelText('watchlist value'), { target: { value: 'Sudan' } })
    fireEvent.change(screen.getByLabelText('watchlist severity'), { target: { value: 'high' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))

    expect(onAdd).toHaveBeenCalledWith({
      type: 'country',
      value: 'Sudan',
      notify_severity: 'high',
    })
  })
})
