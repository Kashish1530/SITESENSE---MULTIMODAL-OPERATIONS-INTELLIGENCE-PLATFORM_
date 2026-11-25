import { describe, expect, it } from 'vitest'
import { DEMO_USERS } from '../../src/data/users'
import { INSPECTIONS } from '../../src/data/inspectionData'
import type {
    CorrectiveAction,
    InspectionEvidence,
    InspectionFinding,
} from '../../src/inspections/types'
import {
    buildInspectionReport,
    getReportCompletionLabel,
    getVisibleReportInspections,
} from '../../src/reports/reportUtils'

describe('report utilities', () => {
    it('allows admins to see all inspections', () => {
        const admin = DEMO_USERS.find(user => user.role === 'admin')!

        expect(
            getVisibleReportInspections(admin, DEMO_USERS, INSPECTIONS),
        ).toHaveLength(INSPECTIONS.length)
    })

    it('limits supervisors to inspections at their site', () => {
        const supervisor = DEMO_USERS.find(
            user => user.role === 'supervisor',
        )!

        const visible = getVisibleReportInspections(
            supervisor,
            DEMO_USERS,
            INSPECTIONS,
        )

        expect(
            visible.every(item => item.siteId === supervisor.siteId),
        ).toBe(true)
    })

    it('limits managers to their direct reports and themselves', () => {
        const manager = DEMO_USERS.find(user => user.role === 'manager')!

        const visible = getVisibleReportInspections(
            manager,
            DEMO_USERS,
            INSPECTIONS,
        )

        const teamIds = DEMO_USERS
            .filter(user => user.managerId === manager.id)
            .map(user => user.id)

        expect(
            visible.every(
                item =>
                    teamIds.includes(item.assignedToUserId) ||
                    item.assignedToUserId === manager.id,
            ),
        ).toBe(true)
    })

    it('does not expose reports to employees', () => {
        const employee = DEMO_USERS.find(user => user.role === 'employee')!

        expect(
            getVisibleReportInspections(employee, DEMO_USERS, INSPECTIONS),
        ).toEqual([])
    })

    it('builds a report with its linked findings, evidence and actions', () => {
        const inspection = {
            ...INSPECTIONS[0],
            findingIds: ['F-TEST'],
            evidenceIds: ['E-TEST'],
        }

        const finding: InspectionFinding = {
            id: 'F-TEST',
            inspectionId: inspection.id,
            title: 'Blocked emergency exit',
            description: 'Emergency exit is obstructed.',
            location: 'Warehouse',
            severity: 'High',
            status: 'Open',
            recommendedAction: 'Clear the exit',
            requiresCorrectiveAction: true,
            reportedByUserId: inspection.assignedToUserId,
            createdAt: '2026-11-20T10:00:00',
        }

        const evidence: InspectionEvidence = {
            id: 'E-TEST',
            inspectionId: inspection.id,
            type: 'Photo',
            fileName: 'exit-photo.jpg',
            fileSizeLabel: '1 MB',
            mimeType: 'image/jpeg',
            uploadedByUserId: inspection.assignedToUserId,
            uploadedAt: '2026-11-20T10:00:00',
        }

        const action: CorrectiveAction = {
            id: 'A-TEST',
            findingId: finding.id,
            inspectionId: inspection.id,
            title: 'Clear emergency exit',
            description: 'Remove stored materials.',
            assignedToUserId: inspection.assignedToUserId,
            assignedByUserId: inspection.assignedByUserId,
            dueDate: '2026-11-25',
            status: 'Open',
            evidenceIds: [],
        }

        const report = buildInspectionReport(
            inspection,
            DEMO_USERS,
            [finding],
            [evidence],
            [action],
        )

        expect(report.findings).toEqual([finding])
        expect(report.evidence).toEqual([evidence])
        expect(report.correctiveActions).toEqual([action])
        expect(report.siteName).toBeTruthy()
        expect(report.assignedUserName).toBeTruthy()
    })

    it('labels incomplete inspections as drafts', () => {
        expect(
            getReportCompletionLabel({
                ...INSPECTIONS[0],
                status: 'In Progress',
            }),
        ).toBe('Draft - inspection not completed')
    })

    it('labels approved completed inspections correctly', () => {
        expect(
            getReportCompletionLabel({
                ...INSPECTIONS[0],
                status: 'Completed',
                reviewStatus: 'Approved',
            }),
        ).toBe('Completed and approved')
    })
})