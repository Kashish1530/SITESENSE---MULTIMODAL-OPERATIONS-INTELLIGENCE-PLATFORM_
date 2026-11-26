import { describe, expect, it } from 'vitest'
import { INSPECTIONS } from '../../src/data/inspectionData'
import {
  calculateManagementDashboard,
  filterManagementInspections,
} from '../../src/analytics/managementDashboard'

const allDates = {
  siteId: 'all',
  startDate: '2026-11-01',
  endDate: '2026-11-30',
}

describe('management dashboard calculations', () => {
  it('includes seeded inspections within the selected date range', () => {
    const filtered = filterManagementInspections(INSPECTIONS, allDates)
    expect(filtered.length).toBe(INSPECTIONS.length)
  })

  it('recognizes legacy Submitted and Under Review records', () => {
    const metrics = calculateManagementDashboard(
      INSPECTIONS,
      allDates,
      new Date('2026-11-20T12:00:00'),
    )

    expect(metrics.pendingReviews).toBe(2)
  })

  it('classifies completed inspections using checklist answers', () => {
    const metrics = calculateManagementDashboard(
      INSPECTIONS,
      allDates,
      new Date('2026-11-20T12:00:00'),
    )

    expect(metrics.completed).toBe(1)
    expect(metrics.failed).toBe(1)
    expect(metrics.passed).toBe(0)
    expect(metrics.passRate + metrics.failureRate).toBe(100)
  })

  it('counts created and completed inspections correctly in the trend', () => {
    const metrics = calculateManagementDashboard(
      INSPECTIONS,
      allDates,
      new Date('2026-11-20T12:00:00'),
    )

    expect(
      metrics.trend.reduce((sum, bucket) => sum + bucket.created, 0),
    ).toBe(metrics.total)

    expect(
      metrics.trend.reduce((sum, bucket) => sum + bucket.completed, 0),
    ).toBe(metrics.completed)
  })

  it('ranks failed checklist rules by frequency', () => {
    const metrics = calculateManagementDashboard(
      INSPECTIONS,
      allDates,
      new Date('2026-11-20T12:00:00'),
    )

    expect(metrics.failedRules).toHaveLength(2)
    expect(metrics.failedRules.every(rule => rule.count === 1)).toBe(true)
    expect(
      metrics.failedRules.map(rule => rule.questionId),
    ).toEqual(expect.arrayContaining(['Q-SAFETY-002', 'Q-FIRE-001']))
  })

  it('applies the site filter consistently', () => {
    const siteFilters = { ...allDates, siteId: 'SITE-001' }

    const filtered = filterManagementInspections(INSPECTIONS, siteFilters)
    const metrics = calculateManagementDashboard(
      INSPECTIONS,
      siteFilters,
      new Date('2026-11-20T12:00:00'),
    )

    expect(filtered.length).toBeGreaterThan(0)
    expect(metrics.total).toBe(filtered.length)
    expect(filtered.every(item => item.siteId === 'SITE-001')).toBe(true)
  })

  it('returns empty metrics for a date range with no inspections', () => {
    const filters = {
      siteId: 'all',
      startDate: '2020-01-01',
      endDate: '2020-01-31',
    }

    const metrics = calculateManagementDashboard(
      INSPECTIONS,
      filters,
      new Date('2026-11-20T12:00:00'),
    )

    expect(metrics.total).toBe(0)
    expect(metrics.pendingReviews).toBe(0)
    expect(metrics.failedRules).toHaveLength(0)
  })
})
