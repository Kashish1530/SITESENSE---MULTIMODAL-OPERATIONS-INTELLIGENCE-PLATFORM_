
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import InspectionDashboard from '../../src/components/inspections/InspectionDashboard'
import { DEMO_USERS } from '../../src/data/users'
import {
    INSPECTIONS,
    INSPECTION_FINDINGS,
    INSPECTION_EVIDENCE,
    CORRECTIVE_ACTIONS,
} from '../../src/data/inspectionData'

vi.mock('../../src/components/analytics/LineChart', () => ({
    default: ({ title }: { title: string }) => <h2>{title}</h2>,
}))

vi.mock('../../src/components/analytics/DonutChart', () => ({
    default: () => null,
}))

vi.mock('../../src/components/analytics/BarChart', () => ({
    default: () => null,
}))

vi.mock('../../src/components/inspections/CreateInspectionModal', () => ({
    default: () => null,
}))

afterEach(() => {
    cleanup()
})

function renderDashboard(userId = 'USER-001') {
    const currentUser = DEMO_USERS.find(user => user.id === userId)!

    return render(
        <InspectionDashboard
            currentUser={currentUser}
            users={DEMO_USERS}
            inspections={INSPECTIONS}
            setInspections={vi.fn()}
            findings={INSPECTION_FINDINGS}
            setFindings={vi.fn()}
            evidence={INSPECTION_EVIDENCE}
            setEvidence={vi.fn()}
            correctiveActions={CORRECTIVE_ACTIONS}
            setCorrectiveActions={vi.fn()}
        />,
    )
}

function openAllInspections() {
    fireEvent.click(
        screen.getByRole('button', { name: 'All Inspections' }),
    )
}

describe('Inspection detail navigation', () => {
    it('opens an inspection detail and preserves search and status filters on return', () => {
        renderDashboard()

        openAllInspections()

        const searchInput = screen.getByPlaceholderText(
            'Search inspection name or ID...',
        )

        fireEvent.change(searchInput, {
            target: { value: 'INS-2026-001' },
        })

        fireEvent.change(screen.getByRole('combobox'), {
            target: { value: 'Completed' },
        })

        fireEvent.click(
            screen.getByRole('button', {
                name: 'View North Warehouse Safety Inspection',
            }),
        )

        expect(
            screen.getByRole('heading', {
                name: 'North Warehouse Safety Inspection',
            }),
        ).toBeInTheDocument()

        fireEvent.click(
            screen.getByRole('button', { name: /back to inspections/i }),
        )

        expect(
            screen.getByPlaceholderText('Search inspection name or ID...'),
        ).toHaveValue('INS-2026-001')

        expect(screen.getByRole('combobox')).toHaveValue('Completed')

        expect(
            screen.getByRole('button', {
                name: 'View North Warehouse Safety Inspection',
            }),
        ).toBeInTheDocument()
    })

    it('only offers detail navigation for inspections visible to the current employee', () => {
        renderDashboard('USER-011')

        openAllInspections()

        expect(screen.getAllByRole('row')).toHaveLength(2)

        expect(
            screen.getByRole('button', {
                name: 'View North Warehouse Safety Inspection',
            }),
        ).toBeInTheDocument()

        expect(
            screen.queryByRole('button', {
                name: 'View South Warehouse Fire Safety Check',
            }),
        ).not.toBeInTheDocument()

        fireEvent.click(
            screen.getByRole('button', {
                name: 'View North Warehouse Safety Inspection',
            }),
        )

        expect(
            screen.getByRole('heading', {
                name: 'North Warehouse Safety Inspection',
            }),
        ).toBeInTheDocument()

        expect(
            screen.queryByText('South Warehouse Fire Safety Check'),
        ).not.toBeInTheDocument()
    })
})
