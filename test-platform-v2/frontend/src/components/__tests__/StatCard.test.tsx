import { render, screen } from '@testing-library/react'
import { Activity } from 'lucide-react'
import { describe, expect, it } from 'vitest'

import StatCard from '../StatCard'

describe('StatCard', () => {
  it('renders a stable fallback for a non-finite numeric value', () => {
    render(<StatCard icon={Activity} label="通过率" value={Number.NaN} />)

    expect(screen.getByText('—')).toBeTruthy()
    expect(screen.queryByText('NaN')).toBeNull()
  })
})
