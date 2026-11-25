
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
import type {
    InspectionRecord,
    InspectionEvidence,
} from '../../src/inspections/types'

const mockInspection: InspectionRecord = {
    id: 'INS-UPLOAD-TEST',
    title: 'Evidence Integration Test',
    description: 'Testing evidence integration',
    type: 'Safety',
    siteId: 'SITE-001',
    zone: 'Loading Bay',
    status: 'Scheduled',
    assignedToUserId: 'USER-011',
    assignedByUserId: 'USER-005',
    createdAt: '2026-11-20T08:00:00.000Z',
    dueDate: '2026-11-25T17:00:00.000Z',
    answers: [],
    observations: [],
    findingIds: [],
    evidenceIds: [],
}

vi.mock('../../src/components/analytics/LineChart', () => ({
    default: () => null,
}))

vi.mock('../../src/components/analytics/DonutChart', () => ({
    default: () => null,
}))

vi.mock('../../src/components/analytics/BarChart', () => ({
    default: () => null,
}))

vi.mock('../../src/components/inspections/CreateInspectionModal', () => ({
    default: ({
        onClose,
        onCreate,
    }: {
        onClose: () => void
        onCreate: (inspection: InspectionRecord, files: File[]) => void
    }) => (
        <div role="dialog">
            <button type="button" onClick={onClose}>
                Close modal
            </button>
            <button
                type="button"
                onClick={() => onCreate(mockInspection, [
                    new File(['photo'], 'evidence.jpg', {
                        type: 'image/jpeg',
                    }),
                ])}
            >
                Create with evidence
            </button>
            <button
                type="button"
                onClick={() => onCreate(mockInspection, [])}
            >
                Create without evidence
            </button>
        </div>
    ),
}))

afterEach(cleanup)

const admin = DEMO_USERS.find(user => user.role === 'admin')!

function renderDashboard(
    setInspections: Dispatch<SetStateAction<InspectionRecord[]>>,
    setEvidence: Dispatch<SetStateAction<InspectionEvidence[]>>,
) {
    render(
        <InspectionDashboard
            currentUser={admin}
            users={DEMO_USERS}
            inspections={INSPECTIONS}
            setInspections={setInspections}
            findings={INSPECTION_FINDINGS}
            setFindings={vi.fn()}
            evidence={INSPECTION_EVIDENCE}
            setEvidence={setEvidence}
            correctiveActions={CORRECTIVE_ACTIONS}
            setCorrectiveActions={vi.fn()}
        />,
    )

    fireEvent.click(
        screen.getByRole('button', { name: '+ Create Inspection' }),
    )
}

describe('Inspection evidence dashboard integration', () => {
    it('stores evidence metadata and links evidence IDs to the inspection', () => {
        let inspectionUpdate:
            | SetStateAction<InspectionRecord[]>
            | undefined

        let evidenceUpdate:
            | SetStateAction<InspectionEvidence[]>
            | undefined

        const setInspections = vi.fn(
            (update: SetStateAction<InspectionRecord[]>) => {
                inspectionUpdate = update
            },
        )

        const setEvidence = vi.fn(
            (update: SetStateAction<InspectionEvidence[]>) => {
                evidenceUpdate = update
            },
        )

        renderDashboard(setInspections, setEvidence)

        fireEvent.click(
            screen.getByRole('button', { name: 'Create with evidence' }),
        )

        expect(setInspections).toHaveBeenCalledTimes(1)
        expect(setEvidence).toHaveBeenCalledTimes(1)

        expect(typeof inspectionUpdate).toBe('function')
        expect(typeof evidenceUpdate).toBe('function')

        const updatedInspections =
            (inspectionUpdate as (previous: InspectionRecord[]) => InspectionRecord[])(
                INSPECTIONS,
            )

        const updatedEvidence =
            (evidenceUpdate as (previous: InspectionEvidence[]) => InspectionEvidence[])(
                INSPECTION_EVIDENCE,
            )

        const createdInspection = updatedInspections[0]
        const createdEvidence = updatedEvidence[0]

        expect(createdInspection.id).toBe('INS-UPLOAD-TEST')
        expect(createdInspection.evidenceIds).toEqual([createdEvidence.id])

        expect(createdEvidence).toMatchObject({
            inspectionId: 'INS-UPLOAD-TEST',
            type: 'Photo',
            fileName: 'evidence.jpg',
            mimeType: 'image/jpeg',
            uploadedByUserId: admin.id,
        })

        expect(createdEvidence.fileSizeLabel).toBeTruthy()
        expect(createdEvidence.uploadedAt).toBeTruthy()

        expect(screen.getByRole('status'))
            .toHaveTextContent(/uploads were simulated/i)
    })

    it('creates an inspection without evidence when no files are supplied', () => {
        const setInspections = vi.fn()
        const setEvidence = vi.fn()

        renderDashboard(setInspections, setEvidence)

        fireEvent.click(
            screen.getByRole('button', { name: 'Create without evidence' }),
        )

        expect(setInspections).toHaveBeenCalledTimes(1)
        expect(setEvidence).not.toHaveBeenCalled()

        const updater = setInspections.mock.calls[0][0] as (
            previous: InspectionRecord[],
        ) => InspectionRecord[]

        const updated = updater(INSPECTIONS)

        expect(updated[0].id).toBe('INS-UPLOAD-TEST')
        expect(updated[0].evidenceIds).toEqual([])
        expect(screen.getByRole('status'))
            .toHaveTextContent(/no evidence files were selected/i)
    })
})
