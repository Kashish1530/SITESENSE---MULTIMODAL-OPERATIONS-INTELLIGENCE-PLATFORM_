
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import type { Dispatch, SetStateAction } from 'react'

import InspectionDashboard from '../../src/components/inspections/InspectionDashboard'
import { DEMO_USERS } from '../../src/data/users'
import {
    INSPECTIONS,
    INSPECTION_FINDINGS,
    INSPECTION_EVIDENCE,
    CORRECTIVE_ACTIONS,
} from '../../src/data/inspectionData'
import type { DemoUser } from '../../src/data/users'
import type { InspectionRecord } from '../../src/inspections/types'

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
    default: ({ onClose, onCreate }: {
        onClose: () => void
        onCreate: (inspection: InspectionRecord) => void
    }) => (
        <div role="dialog" aria-label="Create inspection test modal">
            <button type="button" onClick={onClose}>
                Close modal
            </button>
            <button
                type="button"
                onClick={() => onCreate({
                    id: 'INS-TEST-001',
                    title: 'New Dashboard Test Inspection',
                    description: 'Created during dashboard testing.',
                    type: 'Safety',
                    siteId: 'SITE-001',
                    zone: 'Test Zone',
                    status: 'Scheduled',
                    assignedToUserId: 'USER-011',
                    assignedByUserId: 'USER-005',
                    createdAt: '2026-11-19T08:00:00.000Z',
                    dueDate: '2026-11-25T17:00:00.000Z',
                    answers: [],
                    observations: [],
                    findingIds: [],
                    evidenceIds: [],
                })}
            >
                Create test inspection
            </button>
        </div>
    ),
}))

afterEach(() => {
    cleanup()
})

const admin = DEMO_USERS.find(user => user.role === 'admin')!
const supervisor = DEMO_USERS.find(user => user.id === 'USER-002')!
const manager = DEMO_USERS.find(user => user.id === 'USER-005')!
const employee = DEMO_USERS.find(user => user.id === 'USER-011')!
const southEmployee = DEMO_USERS.find(user => user.id === 'USER-016')!

function renderDashboard(
    currentUser: DemoUser = admin,
    overrides: {
        inspections?: InspectionRecord[]
        findings?: typeof INSPECTION_FINDINGS
        evidence?: typeof INSPECTION_EVIDENCE
        correctiveActions?: typeof CORRECTIVE_ACTIONS
        users?: DemoUser[]
        setInspections?: Dispatch<SetStateAction<InspectionRecord[]>>
    } = {},
) {
    const setInspections =
        overrides.setInspections ??
        (vi.fn() as Dispatch<SetStateAction<InspectionRecord[]>>)

    const result = render(
        <InspectionDashboard
            currentUser={currentUser}
            users={overrides.users ?? DEMO_USERS}
            inspections={overrides.inspections ?? INSPECTIONS}
            setInspections={setInspections}
            findings={overrides.findings ?? INSPECTION_FINDINGS}
            setFindings={vi.fn()}
            evidence={overrides.evidence ?? INSPECTION_EVIDENCE}
            setEvidence={vi.fn()}
            correctiveActions={overrides.correctiveActions ?? CORRECTIVE_ACTIONS}
            setCorrectiveActions={vi.fn()}
        />,
    )

    return { ...result, setInspections }
}

function openTab(name: string) {
    fireEvent.click(screen.getByRole('button', { name }))
}

function getInspectionRows() {
    return screen.getAllByRole('row').slice(1)
}

describe('InspectionDashboard', () => {
    it('renders the dashboard heading and initial overview', () => {
        renderDashboard()

        expect(screen.getByRole('heading', { name: 'Inspections' })).toBeInTheDocument()
        expect(screen.getByText('Viewing: Organisation-wide')).toBeInTheDocument()
        expect(screen.getByText('Total Inspections')).toBeInTheDocument()
        expect(screen.getByText('Inspection Completion Trend')).toBeInTheDocument()
    })

    it('shows all inspections to an admin', () => {
        renderDashboard(admin)
        openTab('All Inspections')

        expect(getInspectionRows()).toHaveLength(INSPECTIONS.length)
        expect(screen.getByText('North Warehouse Safety Inspection')).toBeInTheDocument()
        expect(screen.getByText('Central Distribution Equipment Review')).toBeInTheDocument()
    })

    it('limits a supervisor to inspections at their assigned site', () => {
        renderDashboard(supervisor)
        openTab('All Inspections')

        expect(screen.getByText('Viewing: North Warehouse')).toBeInTheDocument()
        expect(getInspectionRows()).toHaveLength(2)
        expect(screen.getByText('North Warehouse Safety Inspection')).toBeInTheDocument()
        expect(screen.queryByText('South Warehouse Fire Safety Check')).not.toBeInTheDocument()
    })

    it('limits a manager to their direct reports and own assigned inspections', () => {
        renderDashboard(manager)
        openTab('All Inspections')

        expect(screen.getByText('Viewing: Your assigned team')).toBeInTheDocument()
        expect(getInspectionRows()).toHaveLength(2)
        expect(screen.getByText('North Warehouse Safety Inspection')).toBeInTheDocument()
        expect(screen.getByText('North Warehouse Equipment Check')).toBeInTheDocument()
        expect(screen.queryByText('South Warehouse Fire Safety Check')).not.toBeInTheDocument()
    })

    it('limits an employee to their own assigned inspections', () => {
        renderDashboard(employee)
        openTab('All Inspections')

        expect(screen.getByText('Viewing: Your personal inspections')).toBeInTheDocument()
        expect(getInspectionRows()).toHaveLength(1)
        expect(screen.getByText('North Warehouse Safety Inspection')).toBeInTheDocument()
        expect(screen.queryByText('North Warehouse Equipment Check')).not.toBeInTheDocument()
    })

    it('shows only findings associated with inspections in the employee scope', () => {
        renderDashboard(employee)
        openTab('Findings')

        expect(screen.getByText('Emergency walkway partially obstructed')).toBeInTheDocument()
        expect(screen.queryByText('Fire extinguisher inspection tag expired')).not.toBeInTheDocument()
    })

    it('shows evidence count only for inspections in the current scope', () => {
        renderDashboard(employee)
        openTab('Findings')

        expect(screen.getByText('1 evidence files in this scope')).toBeInTheDocument()
    })

    it('shows the corrective action status associated with a finding', () => {
        renderDashboard(employee)
        openTab('Findings')

        expect(screen.getByText('Action: In Progress')).toBeInTheDocument()
    })

    it('shows the empty findings state when no findings are in scope', () => {
        renderDashboard(southEmployee, { findings: [] })
        openTab('Findings')

        expect(screen.getByText('No findings in this scope.')).toBeInTheDocument()
    })

    it('searches inspections by title', () => {
        renderDashboard()
        openTab('All Inspections')

        fireEvent.change(
            screen.getByPlaceholderText('Search inspection name or ID...'),
            { target: { value: 'Fire Safety' } },
        )

        expect(getInspectionRows()).toHaveLength(1)
        expect(screen.getByText('South Warehouse Fire Safety Check')).toBeInTheDocument()
    })

    it('searches inspections by ID', () => {
        renderDashboard()
        openTab('All Inspections')

        fireEvent.change(
            screen.getByPlaceholderText('Search inspection name or ID...'),
            { target: { value: 'INS-2026-005' } },
        )

        expect(getInspectionRows()).toHaveLength(1)
        expect(screen.getByText('Central Distribution Safety Inspection')).toBeInTheDocument()
    })

    it('filters inspections by status', () => {
        renderDashboard()
        openTab('All Inspections')

        fireEvent.change(screen.getByRole('combobox'), {
            target: { value: 'Completed' },
        })

        expect(getInspectionRows()).toHaveLength(1)
        expect(screen.getByText('North Warehouse Safety Inspection')).toBeInTheDocument()
        expect(screen.queryByText('South Warehouse Fire Safety Check')).not.toBeInTheDocument()
    })

    it('shows an empty state when no inspections match the search', () => {
        renderDashboard()
        openTab('All Inspections')

        fireEvent.change(
            screen.getByPlaceholderText('Search inspection name or ID...'),
            { target: { value: 'does-not-exist' } },
        )

        expect(screen.getByText('No inspections found.')).toBeInTheDocument()
    })

    it('renders the available inspection templates', () => {
        renderDashboard()
        openTab('Templates')

        expect(screen.getByText('General Workplace Safety')).toBeInTheDocument()
        expect(screen.getByText('Equipment Inspection')).toBeInTheDocument()
        expect(screen.getByText('Fire Safety Inspection')).toBeInTheDocument()
        expect(screen.getByText('Housekeeping Inspection')).toBeInTheDocument()
    })

    it('allows managers to create inspections', () => {
        renderDashboard(manager)

        expect(screen.getByRole('button', { name: '+ Create Inspection' })).toBeInTheDocument()
    })

    it('does not allow employees to create inspections', () => {
        renderDashboard(employee)

        expect(screen.queryByRole('button', { name: '+ Create Inspection' })).not.toBeInTheDocument()
    })

    it('adds a created inspection and switches to All Inspections', () => {
        const setInspections = vi.fn()
        renderDashboard(admin, { setInspections })

        fireEvent.click(screen.getByRole('button', { name: '+ Create Inspection' }))

        expect(
            screen.getByRole('dialog', { name: 'Create inspection test modal' }),
        ).toBeInTheDocument()

        fireEvent.click(screen.getByRole('button', { name: 'Create test inspection' }))

        expect(setInspections).toHaveBeenCalledTimes(1)

        const updater = setInspections.mock.calls[0][0]
        const updatedInspections = updater(INSPECTIONS)

        expect(updatedInspections[0].id).toBe('INS-TEST-001')
        expect(updatedInspections[0].title).toBe('New Dashboard Test Inspection')

        // The dashboard switches tabs; the parent owns the updated inspections state.
        expect(
            screen.getByPlaceholderText('Search inspection name or ID...'),
        ).toBeInTheDocument()
    })
})
