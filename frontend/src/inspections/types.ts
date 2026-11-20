
import type {
    InspectionStatus,
    InspectionResult,
} from '../analytics/types'

export type FindingSeverity = 'Critical' | 'High' | 'Medium' | 'Low'

export type FindingStatus =
    | 'Open'
    | 'Action Required'
    | 'In Progress'
    | 'Resolved'
    | 'Verified'

export type CorrectiveActionStatus =
    | 'Open'
    | 'In Progress'
    | 'Completed'

export type EvidenceType = 'Photo' | 'Video' | 'Document'

export type InspectionType =
    | 'Safety'
    | 'Equipment'
    | 'Housekeeping'
    | 'Fire Safety'
    | 'Custom'

export type ChecklistQuestion = {
    id: string
    question: string
    description?: string
    required: boolean
    requiresEvidenceOnFail: boolean
}

export type InspectionTemplate = {
    id: string
    name: string
    description: string
    category: InspectionType
    estimatedMinutes: number
    isActive: boolean
    createdByUserId: string
    checklist: ChecklistQuestion[]
}

export type ChecklistAnswer = {
    questionId: string
    result: InspectionResult
    comment?: string
    evidenceIds: string[]
}

export type InspectionEvidence = {
    id: string
    inspectionId: string
    findingId?: string
    questionId?: string
    type: EvidenceType
    fileName: string
    fileSizeLabel: string
    mimeType: string
    caption?: string
    uploadedByUserId: string
    uploadedAt: string
    previewUrl?: string
}

export type InspectionObservation = {
    id: string
    description: string
    location: string
    reportedByUserId: string
    createdAt: string
    evidenceIds: string[]
}

export type InspectionFinding = {
    id: string
    inspectionId: string
    questionId?: string
    title: string
    description: string
    location: string
    severity: FindingSeverity
    status: FindingStatus
    recommendedAction: string
    requiresCorrectiveAction: boolean
    correctiveActionId?: string
    reportedByUserId: string
    createdAt: string
    verifiedByUserId?: string
    verifiedAt?: string
}

export type CorrectiveAction = {
    id: string
    findingId: string
    inspectionId: string
    title: string
    description: string
    assignedToUserId: string
    assignedByUserId: string
    dueDate: string
    status: CorrectiveActionStatus
    completionNotes?: string
    evidenceIds: string[]
    completedAt?: string
    verifiedByUserId?: string
    verifiedAt?: string
}

export type InspectionRecord = {
    id: string
    title: string
    description: string
    type: InspectionType
    templateId?: string
    siteId: string
    zone: string
    status: InspectionStatus
    assignedToUserId: string
    assignedByUserId: string
    createdAt: string
    scheduledAt?: string
    dueDate: string
    startedAt?: string
    submittedAt?: string
    completedAt?: string
    reviewerUserId?: string
    reviewNotes?: string
    answers: ChecklistAnswer[]
    observations: InspectionObservation[]
    findingIds: string[]
    evidenceIds: string[]
    reviewStatus?: ReviewStatus
    reviewedAt?: string
}

export type ReviewStatus =
    | 'Pending'
    | 'Under Review'
    | 'Changes Requested'
    | 'Approved'