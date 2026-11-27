
import { getDirectReports } from '../data/users'
import type { DemoUser } from '../data/users'
import type {
    InspectionRecord,
    ReviewStatus,
} from './types'

export function getReviewStatus(
    inspection: InspectionRecord,
): ReviewStatus | undefined {
    if (inspection.reviewStatus) return inspection.reviewStatus

    // Backward compatibility for seeded inspections.
    if (inspection.status === 'Submitted') return 'Pending'
    if (inspection.status === 'Under Review') return 'Under Review'

    return undefined
}

export function getReviewQueue(
    inspections: InspectionRecord[],
    reviewer: DemoUser,
    users: DemoUser[] = [],
): InspectionRecord[] {
    if (
        reviewer.role !== 'admin' &&
        reviewer.role !== 'supervisor' &&
        reviewer.role !== 'manager'
    ) {
        return []
    }

    const directReportIds = reviewer.role === 'manager'
        ? new Set(
            getDirectReports(reviewer.id, users)
                .filter((user: DemoUser) => user.role === 'employee')
                .map((user: DemoUser) => user.id),
        )
        : null

    return inspections
        .filter(inspection => {
            const reviewStatus = getReviewStatus(inspection)

            if (
                reviewStatus !== 'Pending' &&
                reviewStatus !== 'Under Review'
            ) {
                return false
            }

            if (reviewer.role === 'admin') return true

            if (reviewer.role === 'supervisor') {
                return inspection.siteId === reviewer.siteId
            }

            return directReportIds!.has(inspection.assignedToUserId)
        })
        .sort(
            (a, b) =>
                new Date(a.submittedAt ?? a.createdAt).getTime() -
                new Date(b.submittedAt ?? b.createdAt).getTime(),
        )
}

export function startInspectionReview(
    inspection: InspectionRecord,
    reviewerId: string,
): InspectionRecord {
    return {
        ...inspection,
        // Preserve task status so completed tasks remain in My History.
        reviewStatus: 'Under Review',
        reviewerUserId: reviewerId,
    }
}

export function approveInspection(
    inspection: InspectionRecord,
    reviewerId: string,
    notes = '',
): InspectionRecord {
    return {
        ...inspection,
        status: 'Completed',
        reviewStatus: 'Approved',
        reviewerUserId: reviewerId,
        reviewNotes: notes.trim() || undefined,
        reviewedAt: new Date().toISOString(),
    }
}

export function requestInspectionChanges(
    inspection: InspectionRecord,
    reviewerId: string,
    notes: string,
): InspectionRecord {
    const reviewNotes = notes.trim()

    if (!reviewNotes) {
        throw new Error(
            'Review notes are required when requesting changes.',
        )
    }

    return {
        ...inspection,
        status: 'In Progress',
        reviewStatus: 'Changes Requested',
        reviewerUserId: reviewerId,
        reviewNotes,
        reviewedAt: new Date().toISOString(),
    }
}

export function resubmitInspectionCorrection(
    inspection: InspectionRecord,
    submittedAt: string,
): InspectionRecord {
    return {
        ...inspection,
        status: 'Completed',
        reviewStatus: 'Pending',
        submittedAt,
        completedAt: submittedAt,
        reviewedAt: undefined,
    }
}
