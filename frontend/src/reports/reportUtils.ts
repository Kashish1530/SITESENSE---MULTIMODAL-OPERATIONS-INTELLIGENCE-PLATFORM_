import { DEMO_SITES, type DemoUser } from '../data/users'
import { INSPECTION_TEMPLATES } from '../data/inspectionData'
import type {
    CorrectiveAction,
    InspectionEvidence,
    InspectionFinding,
    InspectionRecord,
} from '../inspections/types'

type ReportDateFields = {
    createdAt?: string
    scheduledAt?: string
    submittedAt?: string
}

export type ReportInspection = InspectionRecord & ReportDateFields

export type InspectionReportData = {
    inspection: ReportInspection
    siteName: string
    templateName: string
    assignedUserName: string
    assignedByUserName: string
    reviewerName: string
    findings: InspectionFinding[]
    evidence: InspectionEvidence[]
    correctiveActions: CorrectiveAction[]
}

function getUserName(users: DemoUser[], userId?: string): string {
    if (!userId) return 'Not recorded'
    return users.find(user => user.id === userId)?.name ?? 'Unknown user'
}

export function getVisibleReportInspections(
    currentUser: DemoUser,
    users: DemoUser[],
    inspections: InspectionRecord[],
): ReportInspection[] {
    if (!currentUser) return []
    if (currentUser.role === 'admin') {
        return inspections
    }

    if (currentUser.role === 'supervisor') {
        return inspections.filter(
            inspection => inspection.siteId === currentUser.siteId,
        )
    }

    if (currentUser.role === 'manager') {
        const teamIds = users
            .filter(user => user.managerId === currentUser.id)
            .map(user => user.id)

        return inspections.filter(
            inspection =>
                teamIds.includes(inspection.assignedToUserId) ||
                inspection.assignedToUserId === currentUser.id,
        )
    }

    return []
}

export function buildInspectionReport(
    inspection: ReportInspection,
    users: DemoUser[],
    findings: InspectionFinding[],
    evidence: InspectionEvidence[],
    correctiveActions: CorrectiveAction[],
): InspectionReportData {
    const linkedFindings = findings.filter(
        finding =>
            finding.inspectionId === inspection.id ||
            inspection.findingIds.includes(finding.id),
    )

    const findingIds = new Set(linkedFindings.map(finding => finding.id))

    const linkedEvidence = evidence.filter(
        item =>
            item.inspectionId === inspection.id ||
            inspection.evidenceIds.includes(item.id),
    )

    const linkedActions = correctiveActions.filter(
        action =>
            action.inspectionId === inspection.id ||
            findingIds.has(action.findingId),
    )

    const site = DEMO_SITES.find(item => item.id === inspection.siteId)
    const template = INSPECTION_TEMPLATES.find(
        item => item.id === inspection.templateId,
    )

    return {
        inspection,
        siteName: site?.name ?? 'Unknown site',
        templateName: template?.name ?? 'Template unavailable',
        assignedUserName: getUserName(users, inspection.assignedToUserId),
        assignedByUserName: getUserName(users, inspection.assignedByUserId),
        reviewerName: getUserName(users, inspection.reviewerUserId),
        findings: linkedFindings,
        evidence: linkedEvidence,
        correctiveActions: linkedActions,
    }
}

export function getReportCompletionLabel(
    inspection: ReportInspection,
): string {
    if (inspection.status !== 'Completed') {
        return 'Draft - inspection not completed'
    }

    if (inspection.reviewStatus === 'Approved') {
        return 'Completed and approved'
    }

    if (inspection.reviewStatus === 'Changes Requested') {
        return 'Completed - changes requested'
    }

    if (inspection.reviewStatus === 'Under Review') {
        return 'Completed - under review'
    }

    if (inspection.reviewStatus === 'Pending') {
        return 'Completed - awaiting review'
    }

    return 'Completed - approval not recorded'
}
