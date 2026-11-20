import type { InspectionRecord } from '../inspections/types'
import { getReviewStatus } from '../inspections/reviewUtils'
import { DEMO_SITES } from '../data/users'

export type DashboardFilters = {
  siteId: string
  startDate: string
  endDate: string
}

export type SiteRisk = {
  siteId: string
  siteName: string
  failedInspections: number
  overdueInspections: number
  pendingReviews: number
  score: number
}

export type FailedRule = {
  questionId: string
  label: string
  count: number
}

export type ManagementDashboardMetrics = {
  total: number
  completed: number
  passed: number
  failed: number
  passRate: number
  failureRate: number
  pendingReviews: number
  overdue: number
  trend: { label: string; created: number; completed: number }[]
  failedRules: FailedRule[]
  siteRisks: SiteRisk[]
}

type DatedInspection = InspectionRecord & {
  createdAt?: string
  scheduledAt?: string
}

function getInspectionDate(inspection: InspectionRecord): Date | null {
  const record = inspection as DatedInspection
  const value =
    record.createdAt ??
    record.scheduledAt ??
    inspection.submittedAt ??
    inspection.completedAt ??
    inspection.dueDate

  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function inDateRange(
  inspection: InspectionRecord,
  filters: DashboardFilters,
): boolean {
  const date = getInspectionDate(inspection)
  if (!date) return false

  const key = date.toISOString().slice(0, 10)
  if (filters.startDate && key < filters.startDate) return false
  if (filters.endDate && key > filters.endDate) return false
  return true
}

function isPendingReview(inspection: InspectionRecord): boolean {
  const status = getReviewStatus(inspection)
  return status === 'Pending' || status === 'Under Review'
}

function isOverdue(
  inspection: InspectionRecord,
  asOf: Date,
): boolean {
  if (
    inspection.status === 'Completed' ||
    inspection.status === 'Submitted' ||
    inspection.status === 'Under Review'
  ) return false

  const due = new Date(inspection.dueDate)
  if (Number.isNaN(due.getTime())) return false

  return due.getTime() < new Date(
    asOf.getFullYear(),
    asOf.getMonth(),
    asOf.getDate(),
  ).getTime()
}

function classifyCompleted(inspection: InspectionRecord): 'Passed' | 'Failed' | null {
  if (inspection.status !== 'Completed') return null

  const answers = inspection.answers ?? []
  if (answers.some(answer => answer.result === 'Failed')) return 'Failed'
  if (answers.some(answer => answer.result === 'Passed')) return 'Passed'
  return null
}

const RULE_LABELS: Record<string, string> = {
  'Q-SAFETY-001': 'PPE compliance',
  'Q-SAFETY-002': 'Walkways and emergency exits',
  'Q-SAFETY-003': 'Workplace hazards',
  'Q-EQUIP-001': 'Visible equipment damage',
  'Q-EQUIP-002': 'Maintenance labels',
  'Q-EQUIP-003': 'Safety guards and controls',
  'Q-FIRE-001': 'Fire extinguisher accessibility',
  'Q-FIRE-002': 'Emergency exits',
  'Q-FIRE-003': 'Fire safety signs',
  'Q-HOUSE-001': 'Cleanliness and waste',
  'Q-HOUSE-002': 'Safe storage',
  'Q-HOUSE-003': 'Slip and trip hazards',
}

export function filterManagementInspections(
  inspections: InspectionRecord[],
  filters: DashboardFilters,
): InspectionRecord[] {
  return inspections.filter(inspection =>
    (filters.siteId === 'all' || inspection.siteId === filters.siteId) &&
    inDateRange(inspection, filters),
  )
}

export function calculateManagementDashboard(
  inspections: InspectionRecord[],
  filters: DashboardFilters,
  asOf: Date = new Date(),
): ManagementDashboardMetrics {
  const filtered = filterManagementInspections(inspections, filters)
  const completed = filtered.filter(item => item.status === 'Completed')

  let passed = 0
  let failed = 0

  completed.forEach(inspection => {
    const result = classifyCompleted(inspection)
    if (result === 'Passed') passed++
    if (result === 'Failed') failed++
  })

  const reviewed = passed + failed
  const pendingReviews = filtered.filter(isPendingReview).length
  const overdue = filtered.filter(item => isOverdue(item, asOf)).length

  const failedRuleCounts = new Map<string, number>()
  filtered.forEach(inspection => {
    inspection.answers?.forEach(answer => {
      if (answer.result !== 'Failed') return
      failedRuleCounts.set(
        answer.questionId,
        (failedRuleCounts.get(answer.questionId) ?? 0) + 1,
      )
    })
  })

  const failedRules = Array.from(failedRuleCounts.entries())
    .map(([questionId, count]) => ({
      questionId,
      label: RULE_LABELS[questionId] ?? questionId,
      count,
    }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))

  const siteRisks = DEMO_SITES
    .filter(site => filters.siteId === 'all' || site.id === filters.siteId)
    .map(site => {
      const records = filtered.filter(item => item.siteId === site.id)
      const failedInspections = records.filter(
        item => classifyCompleted(item) === 'Failed',
      ).length
      const overdueInspections = records.filter(item => isOverdue(item, asOf)).length
      const sitePendingReviews = records.filter(isPendingReview).length

      return {
        siteId: site.id,
        siteName: site.name,
        failedInspections,
        overdueInspections,
        pendingReviews: sitePendingReviews,
        score: failedInspections * 3 + overdueInspections * 2 + sitePendingReviews,
      }
    })
    .sort((a, b) => b.score - a.score || a.siteName.localeCompare(b.siteName))

  const trendMap = new Map<string, { label: string; created: number; completed: number }>()
  filtered.forEach(inspection => {
    const date = getInspectionDate(inspection)
    if (!date) return
    const key = date.toISOString().slice(0, 7)
    const bucket = trendMap.get(key) ?? {
      label: date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }),
      created: 0,
      completed: 0,
    }
    bucket.created++
    if (inspection.status === 'Completed') bucket.completed++
    trendMap.set(key, bucket)
  })

  return {
    total: filtered.length,
    completed: completed.length,
    passed,
    failed,
    passRate: reviewed ? Math.round((passed / reviewed) * 100) : 0,
    failureRate: reviewed ? Math.round((failed / reviewed) * 100) : 0,
    pendingReviews,
    overdue,
    trend: Array.from(trendMap.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([, value]) => value),
    failedRules,
    siteRisks,
  }
}



