
import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import DonutChart from '../../src/components/analytics/DonutChart'

afterEach(() => {
    cleanup()
})

const sampleData = [
    { label: 'Completed', value: 6, color: '#22c55e' },
    { label: 'Pending', value: 4, color: '#f59e0b' },
]

describe('DonutChart', () => {
    it('displays the empty state when data is empty', () => {
        render(<DonutChart data={[]} />)

        expect(
            screen.getByText('No data available for this period.'),
        ).toBeInTheDocument()
    })

    it('displays the empty state when all values are zero', () => {
        render(
            <DonutChart
                data={[
                    { label: 'Completed', value: 0, color: '#22c55e' },
                ]}
            />,
        )

        expect(
            screen.getByText('No data available for this period.'),
        ).toBeInTheDocument()
    })

    it('calculates the total and segment percentages correctly', () => {
        render(<DonutChart data={sampleData} />)

        expect(screen.getByText('10')).toBeInTheDocument()
        expect(screen.getByText('Completed')).toBeInTheDocument()
        expect(screen.getByText('Pending')).toBeInTheDocument()
        expect(screen.getByText('60.0%')).toBeInTheDocument()
        expect(screen.getByText('40.0%')).toBeInTheDocument()
    })

    it('excludes invalid and negative values', () => {
        render(
            <DonutChart
                data={[
                    { label: 'Valid', value: 8, color: '#22c55e' },
                    { label: 'Negative', value: -3, color: '#ef4444' },
                    { label: 'Invalid', value: Number.NaN, color: '#f59e0b' },
                    { label: 'Infinite', value: Infinity, color: '#3b82f6' },
                ]}
            />,
        )


        expect(screen.getByText('8', { selector: 'span.text-3xl' })).toBeInTheDocument()
        expect(screen.getByText('Valid')).toBeInTheDocument()
        expect(screen.queryByText('Negative')).not.toBeInTheDocument()
        expect(screen.queryByText('Invalid')).not.toBeInTheDocument()
        expect(screen.queryByText('Infinite')).not.toBeInTheDocument()
    })

    it('highlights a segment when its legend item is clicked', () => {
        const { container } = render(<DonutChart data={sampleData} />)

        const completedButton = screen.getByRole('button', {
            name: /Completed/,
        })

        const completedSegment = container.querySelectorAll('svg circle')[1]

        expect(completedSegment).toHaveAttribute('stroke-width', '24')

        fireEvent.click(completedButton)

        expect(completedSegment).toHaveAttribute('stroke-width', '29')
        expect(screen.getByText(/6 records/)).toBeInTheDocument()
    })

    it('removes the highlight when the active legend item is clicked again', () => {
        const { container } = render(<DonutChart data={sampleData} />)

        const completedButton = screen.getByRole('button', {
            name: /Completed/,
        })

        const completedSegment = container.querySelectorAll('svg circle')[1]

        fireEvent.click(completedButton)
        fireEvent.click(completedButton)

        expect(completedSegment).toHaveAttribute('stroke-width', '24')
        expect(screen.queryByText(/6 records/)).not.toBeInTheDocument()
    })
})
