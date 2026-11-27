
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'

import ReportViewer from '../../src/components/reports/ReportViewer'
import { DEMO_USERS } from '../../src/data/users'
import {
    INSPECTIONS,
    INSPECTION_FINDINGS,
    INSPECTION_EVIDENCE,
    CORRECTIVE_ACTIONS,
} from '../../src/data/inspectionData'

afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
})

describe('ReportViewer', () => {
    const admin = DEMO_USERS.find(user => user.role === 'admin')!
    const supervisor = DEMO_USERS.find(user => user.id === 'USER-002')!
    const manager = DEMO_USERS.find(user => user.id === 'USER-005')!
    const employee = DEMO_USERS.find(user => user.role === 'employee')!

    const renderViewer = (currentUser = admin) =>
        render(
            <ReportViewer
                currentUser={currentUser}
                users={DEMO_USERS}
                inspections={INSPECTIONS}
                findings={INSPECTION_FINDINGS}
                evidence={INSPECTION_EVIDENCE}
                correctiveActions={CORRECTIVE_ACTIONS}
            />,
        )

    it('allows an admin to view all inspection reports', () => {
        renderViewer(admin)

        expect(
            screen.getByRole('heading', { name: 'Report Viewer' }),
        ).toBeInTheDocument()

        const selector = screen.getByRole('combobox', {
            name: /select inspection/i,
        })

        expect(within(selector).getAllByRole('option')).toHaveLength(
            INSPECTIONS.length,
        )
    })

    it('restricts supervisors to inspections at their own site', () => {
        renderViewer(supervisor)

        const selector = screen.getByRole('combobox', {
            name: /select inspection/i,
        })

        const options = within(selector).getAllByRole('option')

        expect(options.length).toBeGreaterThan(0)

        INSPECTIONS.filter(item => item.siteId === supervisor.siteId).forEach(
            inspection => {
                expect(
                    within(selector).getByRole('option', {
                        name: new RegExp(inspection.id),
                    }),
                ).toBeInTheDocument()
            },
        )

        INSPECTIONS.filter(item => item.siteId !== supervisor.siteId).forEach(
            inspection => {
                expect(
                    within(selector).queryByRole('option', {
                        name: new RegExp(inspection.id),
                    }),
                ).not.toBeInTheDocument()
            },
        )
    })

    it('restricts managers to their direct reports and themselves', () => {
        renderViewer(manager)

        const selector = screen.getByRole('combobox', {
            name: /select inspection/i,
        })

        const visibleInspections = INSPECTIONS.filter(inspection => {
            const assignedUser = DEMO_USERS.find(
                user => user.id === inspection.assignedToUserId,
            )

            return (
                inspection.assignedToUserId === manager.id ||
                assignedUser?.managerId === manager.id
            )
        })

        expect(within(selector).getAllByRole('option')).toHaveLength(
            visibleInspections.length,
        )

        INSPECTIONS.filter(
            inspection => !visibleInspections.includes(inspection),
        ).forEach(inspection => {
            expect(
                within(selector).queryByRole('option', {
                    name: new RegExp(inspection.id),
                }),
            ).not.toBeInTheDocument()
        })
    })

    it('shows no reports for employees', () => {
        renderViewer(employee)

        expect(
            screen.getByText('No reports available'),
        ).toBeInTheDocument()

        const selector = screen.getByRole('combobox', {
            name: /select inspection/i,
        })

        expect(within(selector).queryAllByRole('option')).toHaveLength(0)

        expect(
            screen.getByRole('button', {
                name: /print \/ save as pdf/i,
            }),
        ).toBeDisabled()
    })

    it('updates the report preview when another inspection is selected', () => {
        renderViewer(admin)

        expect(
            screen.getByRole('heading', {
                name: 'North Warehouse Safety Inspection',
            }),
        ).toBeInTheDocument()

        const selector = screen.getByRole('combobox', {
            name: /select inspection/i,
        })

        fireEvent.change(selector, {
            target: { value: INSPECTIONS[1].id },
        })

        expect(
            screen.getByRole('heading', {
                name: INSPECTIONS[1].title,
            }),
        ).toBeInTheDocument()
    })

    it('renders checklist, findings, corrective actions and evidence', () => {
        renderViewer(admin)

        expect(
            screen.getByRole('heading', { name: 'Checklist summary' }),
        ).toBeInTheDocument()

        expect(
            screen.getByText(/Are walkways and emergency exits unobstructed\?/)
        ).toBeInTheDocument()

        expect(
            screen.getByRole('heading', { name: /Findings/ }),
        ).toBeInTheDocument()

        expect(
            screen.getByText('Emergency walkway partially obstructed'),
        ).toBeInTheDocument()

        expect(
            screen.getByRole('heading', { name: /Corrective actions/ }),
        ).toBeInTheDocument()

        expect(
            screen.getByText('Clear the emergency walkway'),
        ).toBeInTheDocument()

        expect(
            screen.getByRole('heading', { name: /Evidence/ }),
        ).toBeInTheDocument()

        expect(
            screen.getByText('blocked-emergency-walkway.jpg'),
        ).toBeInTheDocument()
    })

    it('calls window.print when Print / Save as PDF is clicked', () => {
        const printSpy = vi
            .spyOn(window, 'print')
            .mockImplementation(() => undefined)

        renderViewer(admin)

        fireEvent.click(
            screen.getByRole('button', {
                name: /print \/ save as pdf/i,
            }),
        )

        expect(printSpy).toHaveBeenCalledOnce()
    })
})
