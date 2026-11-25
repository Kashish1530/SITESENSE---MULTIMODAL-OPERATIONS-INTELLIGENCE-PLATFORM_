
import type {
    AnalyticsInspection,
    InspectionMetrics,
    WeeklyInspectionTrend,
    SiteInspectionPerformance,
} from './types'

function percentage(value: number, total: number): number {
    if (total <= 0) return 0
    return Math.round((value / total) * 1000) / 10
}

function validDate(value?: string | null): Date | null {
    if (!value) return null

    const date = new Date(value)

    return Number.isNaN(date.getTime()) ? null : date
}

function getDurationMinutes(
    inspection: AnalyticsInspection,
): number | null {
    if (
        typeof inspection.durationMinutes === 'number' &&
        Number.isFinite(inspection.durationMinutes) &&
        inspection.durationMinutes >= 0
    ) {
        return inspection.durationMinutes
    }

    const start = validDate(inspection.createdAt)
    const end = validDate(inspection.completedAt)

    if (!start || !end || end < start) return null

    return (end.getTime() - start.getTime()) / 60000
}

export function calculateInspectionMetrics(
    inspections: AnalyticsInspection[],
    asOf: Date = new Date(),
): InspectionMetrics {
    const total = inspections.length

    const completedInspections = inspections.filter(
        item => item.status === 'Completed',
    )

    const inProgress = inspections.filter(
        item => item.status === 'In Progress',
    ).length

    const pendingReview = inspections.filter(
        item =>
            item.status === 'Submitted' ||
            item.status === 'Under Review',
    ).length

    const overdue = inspections.filter(item => {
        if (item.status === 'Completed') return false

        const dueDate = validDate(item.dueDate)

        return dueDate !== null && dueDate < asOf
    }).length

    const passed = completedInspections.filter(
        item => item.result === 'Passed',
    ).length

    const failed = completedInspections.filter(
        item => item.result === 'Failed',
    ).length

    const reviewed = passed + failed

    const durations = completedInspections
        .map(getDurationMinutes)
        .filter((value): value is number => value !== null)

    const averageCompletionMinutes = durations.length
        ? Math.round(
            durations.reduce((sum, value) => sum + value, 0) /
            durations.length,
        )
        : 0

    return {
        total,
        completed: completedInspections.length,
        inProgress,
        pendingReview,
        overdue,
        completionRate: percentage(
            completedInspections.length,
            total,
        ),
        passRate: percentage(passed, reviewed),
        failureRate: percentage(failed, reviewed),
        averageCompletionMinutes,
    }
}

function getMonday(date: Date): Date {
    const result = new Date(Date.UTC(
        date.getUTCFullYear(),
        date.getUTCMonth(),
        date.getUTCDate(),
    ))

    const day = result.getUTCDay()
    const difference = day === 0 ? -6 : 1 - day

    result.setUTCDate(result.getUTCDate() + difference)

    return result
}

function dateKey(date: Date): string {
    return date.toISOString().slice(0, 10)
}

export function calculateWeeklyInspectionTrend(
    inspections: AnalyticsInspection[],
    weeks = 8,
    asOf: Date = new Date(),
): WeeklyInspectionTrend[] {
    const safeWeeks = Number.isFinite(weeks)
        ? Math.min(52, Math.max(1, Math.floor(weeks)))
        : 8

    const currentWeek = getMonday(asOf)

    const buckets = new Map<
        string,
        WeeklyInspectionTrend
    >()

    for (let index = safeWeeks - 1; index >= 0; index--) {
        const start = new Date(currentWeek)
        start.setUTCDate(start.getUTCDate() - index * 7)

        const key = dateKey(start)

        buckets.set(key, {
            week: start.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                timeZone: 'UTC',
            }),
            startDate: key,
            created: 0,
            completed: 0,
        })
    }

    inspections.forEach(inspection => {
        const createdAt = validDate(inspection.createdAt)

        if (createdAt) {
            const key = dateKey(getMonday(createdAt))
            const bucket = buckets.get(key)

            if (bucket) bucket.created++
        }

        if (inspection.status === 'Completed') {
            const completedAt = validDate(inspection.completedAt)

            if (completedAt) {
                const key = dateKey(getMonday(completedAt))
                const bucket = buckets.get(key)

                if (bucket) bucket.completed++
            }
        }
    })

    return Array.from(buckets.values())
}

export function calculateSitePerformance(
    inspections: AnalyticsInspection[],
): SiteInspectionPerformance[] {
    const groups = new Map<
        string,
        AnalyticsInspection[]
    >()

    inspections.forEach(inspection => {
        const group = groups.get(inspection.siteId) ?? []

        group.push(inspection)
        groups.set(inspection.siteId, group)
    })

    return Array.from(groups.entries()).map(
        ([siteId, records]) => {
            const completed = records.filter(
                item => item.status === 'Completed',
            )

            const passed = completed.filter(
                item => item.result === 'Passed',
            ).length

            const failed = completed.filter(
                item => item.result === 'Failed',
            ).length

            return {
                siteId,
                total: records.length,
                completed: completed.length,
                completionRate: percentage(
                    completed.length,
                    records.length,
                ),
                passed,
                failed,
                passRate: percentage(
                    passed,
                    passed + failed,
                ),
            }
        },
    )
}
