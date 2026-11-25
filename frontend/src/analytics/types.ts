
export type InspectionStatus =
    | 'Draft'
    | 'Scheduled'
    | 'In Progress'
    | 'Submitted'
    | 'Under Review'
    | 'Completed'

export type InspectionResult =
    | 'Passed'
    | 'Failed'
    | 'Not Applicable'

export type AnalyticsInspection = {
    id: string
    siteId: string
    status: InspectionStatus
    result?: InspectionResult
    createdAt: string
    completedAt?: string | null
    dueDate?: string | null
    durationMinutes?: number | null
}

export type InspectionMetrics = {
    total: number
    completed: number
    inProgress: number
    pendingReview: number
    overdue: number
    completionRate: number
    passRate: number
    failureRate: number
    averageCompletionMinutes: number
}

export type WeeklyInspectionTrend = {
    week: string
    startDate: string
    created: number
    completed: number
}

export type SiteInspectionPerformance = {
    siteId: string
    total: number
    completed: number
    completionRate: number
    passed: number
    failed: number
    passRate: number
}
