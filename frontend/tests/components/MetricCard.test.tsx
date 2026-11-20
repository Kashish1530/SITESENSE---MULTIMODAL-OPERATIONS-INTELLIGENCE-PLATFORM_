
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import MetricCard from '../../src/components/dashboard/MetricCard'

const defaultProps = {
    title: 'Total Inspections',
    value: '128',
    change: '+12%',
    trend: 'up',
    description: 'Compared with last month',
}

describe('MetricCard', () => {
    it('renders all supplied content', () => {
        render(<MetricCard {...defaultProps} />)

        expect(screen.getByText('Total Inspections')).toBeInTheDocument()
        expect(screen.getByText('128')).toBeInTheDocument()
        expect(screen.getByText('+12%')).toBeInTheDocument()
        expect(screen.getByText('Compared with last month')).toBeInTheDocument()
    })

    it('uses green styling for an upward trend', () => {
        const { container } = render(
            <MetricCard {...defaultProps} trend="up" />,
        )

        expect(container.querySelector('.bg-emerald-50')).toBeInTheDocument()
        expect(container.querySelector('.text-emerald-700')).toBeInTheDocument()
    })

    it('uses red styling for a downward trend', () => {
        const { container } = render(
            <MetricCard {...defaultProps} trend="down" />,
        )

        expect(container.querySelector('.bg-red-50')).toBeInTheDocument()
        expect(container.querySelector('.text-red-700')).toBeInTheDocument()
    })

    it('uses amber styling for a warning trend', () => {
        const { container } = render(
            <MetricCard {...defaultProps} trend="warning" />,
        )

        expect(container.querySelector('.bg-amber-50')).toBeInTheDocument()
        expect(container.querySelector('.text-amber-700')).toBeInTheDocument()
    })

    it('uses neutral styling for a neutral trend', () => {
        const { container } = render(
            <MetricCard {...defaultProps} trend="neutral" />,
        )

        expect(container.querySelector('.bg-slate-100')).toBeInTheDocument()
        expect(container.querySelector('.text-slate-600')).toBeInTheDocument()
    })

    it('falls back to neutral styling for an unknown trend', () => {
        const { container } = render(
            <MetricCard {...defaultProps} trend="unknown" />,
        )

        expect(container.querySelector('.bg-slate-100')).toBeInTheDocument()
        expect(container.querySelector('.text-slate-600')).toBeInTheDocument()
    })
})
