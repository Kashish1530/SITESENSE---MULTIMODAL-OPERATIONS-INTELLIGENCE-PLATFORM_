import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import InspectionDetail from '../../src/components/inspections/InspectionDetail'
import { DEMO_USERS } from '../../src/data/users'
import {
    INSPECTIONS,
    INSPECTION_FINDINGS,
    INSPECTION_EVIDENCE,
    CORRECTIVE_ACTIONS,
} from '../../src/data/inspectionData'

afterEach(() => {
    cleanup()
})

describe('InspectionDetail', () => {
    const inspection = INSPECTIONS[0]

    const relatedFindings = INSPECTION_FINDINGS.filter(
        item => item.inspectionId === inspection.id,
    )

    const relatedEvidence = INSPECTION_EVIDENCE.filter(
        item => item.inspectionId === inspection.id,
    )

    const relatedActions = CORRECTIVE_ACTIONS.filter(
        item => item.inspectionId === inspection.id,
    )

    it('renders the inspection title, status and metadata', () => {
        render(
            <InspectionDetail
                inspection={inspection}
                users={DEMO_USERS}
                evidence={relatedEvidence}
                findings={relatedFindings}
                correctiveActions={relatedActions}
                onBack={vi.fn()}
            />,
        )

        expect(
            screen.getByRole('heading', {
                name: 'North Warehouse Safety Inspection',
            }),
        ).toBeInTheDocument()

        expect(
            screen.getByText('Completed', { selector: 'span' }),
        ).toBeInTheDocument()

        expect(
            screen.getByText(/North Warehouse\s*\/\s*Main Warehouse/, {
                selector: 'p',
            }),
        ).toBeInTheDocument()

        expect(
            screen.getByText('General Workplace Safety'),
        ).toBeInTheDocument()

        const inspector = DEMO_USERS.find(
            user => user.id === inspection.assignedToUserId,
        )

        expect(inspector).toBeDefined()
        expect(screen.getByText(inspector!.name)).toBeInTheDocument()
        expect(
            screen.getByText(/North Warehouse\s*\/\s*Main Warehouse/),
        ).toBeInTheDocument()
    })

    it('calculates Passed, Failed and Not Applicable counts from answers', () => {
        render(
            <InspectionDetail
                inspection={inspection}
                users={DEMO_USERS}
                evidence={relatedEvidence}
                findings={relatedFindings}
                correctiveActions={relatedActions}
                onBack={vi.fn()}
            />,
        )

        const passedCard = screen.getByText('Passed', { selector: 'p' }).parentElement
        const failedCard = screen.getByText('Failed', { selector: 'p' }).parentElement
        const notApplicableCard = screen.getByText('Not Applicable', { selector: 'p' }).parentElement

        expect(passedCard).toHaveTextContent('2')
        expect(failedCard).toHaveTextContent('1')
        expect(notApplicableCard).toHaveTextContent('0')
    })

    it('resolves checklist question text and displays answer comments', () => {
        render(
            <InspectionDetail
                inspection={inspection}
                users={DEMO_USERS}
                evidence={relatedEvidence}
                findings={relatedFindings}
                correctiveActions={relatedActions}
                onBack={vi.fn()}
            />,
        )

        expect(
            screen.getByText('Are walkways and emergency exits unobstructed?'),
        ).toBeInTheDocument()

        expect(
            screen.getByText('A pallet was partially blocking an emergency walkway.'),
        ).toBeInTheDocument()
    })

    it('renders linked evidence, findings and corrective actions', () => {
        render(
            <InspectionDetail
                inspection={inspection}
                users={DEMO_USERS}
                evidence={relatedEvidence}
                findings={relatedFindings}
                correctiveActions={relatedActions}
                onBack={vi.fn()}
            />,
        )

        expect(
            screen.getAllByText('blocked-emergency-walkway.jpg').length,
        ).toBeGreaterThan(0)

        expect(
            screen.getByText('Emergency walkway partially obstructed'),
        ).toBeInTheDocument()

        expect(
            screen.getByText('Clear the emergency walkway'),
        ).toBeInTheDocument()
    })

    it('calls onBack when the back button is clicked', () => {
        const onBack = vi.fn()

        render(
            <InspectionDetail
                inspection={inspection}
                users={DEMO_USERS}
                evidence={relatedEvidence}
                findings={relatedFindings}
                correctiveActions={relatedActions}
                onBack={onBack}
            />,
        )

        fireEvent.click(
            screen.getByRole('button', { name: /back to inspections/i }),
        )

        expect(onBack).toHaveBeenCalledTimes(1)
    })

    it('handles a missing template and unknown user references', () => {
        const incompleteInspection = {
            ...inspection,
            templateId: 'MISSING-TEMPLATE',
            assignedToUserId: 'MISSING-USER',
            assignedByUserId: 'MISSING-ASSIGNER',
            reviewerUserId: 'MISSING-REVIEWER',
            answers: [
                {
                    questionId: 'MISSING-QUESTION',
                    result: 'Passed' as const,
                    evidenceIds: [],
                },
            ],
        }

        render(
            <InspectionDetail
                inspection={incompleteInspection}
                users={DEMO_USERS}
                evidence={[]}
                findings={[]}
                correctiveActions={[]}
                onBack={vi.fn()}
            />,
        )

        expect(screen.getByText('Template unavailable')).toBeInTheDocument()
        expect(screen.getAllByText('Unknown user')).toHaveLength(3)
        expect(screen.getByText('Question details unavailable')).toBeInTheDocument()
        expect(
            screen.getByText('No findings are linked to this inspection.'),
        ).toBeInTheDocument()
    })
})