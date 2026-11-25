
import { useEffect, useMemo, useState } from 'react'
import {
    AlertTriangle,
    CheckCircle2,
    ClipboardList,
    Clock3,
    ShieldAlert,
    TrendingUp,
} from 'lucide-react'
import type { InspectionRecord } from '../../inspections/types'
import { DEMO_SITES, type DemoSite } from '../../data/users'
import { getSitesApi } from '../../api/client'
import { getReviewStatus } from '../../inspections/reviewUtils'
import {
    calculateManagementDashboard,
    filterManagementInspections,
} from '../../analytics/managementDashboard'

type OverviewProps = {
    inspections: InspectionRecord[]
}

function MetricCard({
    title,
    value,
    subtitle,
    icon: Icon,
}: {
    title: string
    value: string | number
    subtitle: string
    icon: typeof ClipboardList
}) {
    return (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-slate-500">{title}</p>
                <Icon className="h-5 w-5 text-slate-400" />
            </div>
            <p className="mt-3 text-3xl font-semibold text-slate-900">{value}</p>
            <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
        </div>
    )
}

function formatDate(value?: string) {
    if (!value) return '—'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return '—'
    return date.toLocaleDateString()
}

function getSiteName(siteId: string) {
    return DEMO_SITES.find(site => site.id === siteId)?.name ?? siteId
}

export default function Overview({ inspections }: OverviewProps) {
    const [siteId, setSiteId] = useState('all')
    const [startDate, setStartDate] = useState('')
    const [endDate, setEndDate] = useState('')
    const [loadedSites, setLoadedSites] = useState<DemoSite[]>([])

    useEffect(() => {
        getSitesApi()
            .then(sites => {
                if (Array.isArray(sites) && sites.length > 0) {
                    setLoadedSites(sites.map((s: any) => ({
                        id: s.id,
                        name: s.name,
                        region: s.region || 'Default Region',
                        type: s.type,
                        location: s.location,
                        active: s.active !== false,
                    })))
                }
            })
            .catch(console.error)
    }, [])

    const availableSites = useMemo(() => {
        if (loadedSites.length > 0) return loadedSites
        const map = new Map<string, string>()
        inspections.forEach(item => {
            if (item.siteId) {
                map.set(item.siteId, item.siteName || item.siteId)
            }
        })
        return Array.from(map.entries()).map(([id, name]) => ({
            id,
            name,
            region: 'Default',
            active: true,
        }))
    }, [loadedSites, inspections])

    const filters = useMemo(
        () => ({ siteId, startDate, endDate }),
        [siteId, startDate, endDate],
    )

    const filteredInspections = useMemo(
        () => filterManagementInspections(inspections, filters),
        [inspections, filters],
    )

    const metrics = useMemo(
        () => calculateManagementDashboard(
            inspections,
            filters,
            new Date(),
        ),
        [inspections, filters],
    )

    const pendingReviews = useMemo(
        () => filteredInspections
            .filter(inspection => {
                const status = getReviewStatus(inspection)
                return status === 'Pending' || status === 'Under Review'
            })
            .sort((a, b) => {
                const aDate = a.submittedAt ?? a.createdAt
                const bDate = b.submittedAt ?? b.createdAt
                return new Date(aDate).getTime() - new Date(bDate).getTime()
            }),
        [filteredInspections],
    )

    const maxTrend = Math.max(
        1,
        ...metrics.trend.flatMap(item => [item.created, item.completed]),
    )

    const maxRuleCount = Math.max(
        1,
        ...metrics.failedRules.map(rule => rule.count),
    )

    const maxRisk = Math.max(
        1,
        ...metrics.siteRisks.map(site => site.score),
    )

    function clearFilters() {
        setSiteId('all')
        setStartDate('')
        setEndDate('')
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <h1 className="text-2xl font-semibold text-slate-900">
                        Management Dashboard
                    </h1>
                    <p className="mt-1 text-sm text-slate-500">
                        Cross-site inspection performance and operational risk
                    </p>
                </div>
            </div>

            <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                    <h2 className="font-semibold text-slate-900">Dashboard filters</h2>
                    <button
                        type="button"
                        onClick={clearFilters}
                        className="text-sm font-medium text-blue-700 hover:text-blue-900"
                    >
                        Clear filters
                    </button>
                </div>

                <div className="grid gap-4 sm:grid-cols-3">
                    <label className="text-sm text-slate-600">
                        Site
                        <select
                            value={siteId}
                            onChange={event => setSiteId(event.target.value)}
                            className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900"
                        >
                            <option value="all">All sites</option>
                            {availableSites.map(site => (
                                <option key={site.id} value={site.id}>
                                    {site.name}
                                </option>
                            ))}
                        </select>
                    </label>

                    <label className="text-sm text-slate-600">
                        From date
                        <input
                            type="date"
                            value={startDate}
                            max={endDate || undefined}
                            onChange={event => setStartDate(event.target.value)}
                            className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
                        />
                    </label>

                    <label className="text-sm text-slate-600">
                        To date
                        <input
                            type="date"
                            value={endDate}
                            min={startDate || undefined}
                            onChange={event => setEndDate(event.target.value)}
                            className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
                        />
                    </label>
                </div>
            </section>

            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                <MetricCard
                    title="Total inspections"
                    value={metrics.total}
                    subtitle="Records matching selected filters"
                    icon={ClipboardList}
                />
                <MetricCard
                    title="Pass rate"
                    value={`${metrics.passRate}%`}
                    subtitle={`${metrics.passed} passed inspections`}
                    icon={CheckCircle2}
                />
                <MetricCard
                    title="Failure rate"
                    value={`${metrics.failureRate}%`}
                    subtitle={`${metrics.failed} failed inspections`}
                    icon={AlertTriangle}
                />
                <MetricCard
                    title="Pending reviews"
                    value={metrics.pendingReviews}
                    subtitle="Pending or under review"
                    icon={Clock3}
                />
                <MetricCard
                    title="Overdue inspections"
                    value={metrics.overdue}
                    subtitle="Active inspections past due date"
                    icon={ShieldAlert}
                />
                <MetricCard
                    title="Completed inspections"
                    value={metrics.completed}
                    subtitle="Completed records in selected period"
                    icon={TrendingUp}
                />
            </section>

            <section className="grid gap-6 xl:grid-cols-2">
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <h2 className="font-semibold text-slate-900">
                        Inspection trend
                    </h2>
                    <p className="mt-1 text-xs text-slate-500">
                        Created and completed inspections by month
                    </p>

                    {metrics.trend.length === 0 ? (
                        <p className="py-12 text-center text-sm text-slate-500">
                            No trend data for this period.
                        </p>
                    ) : (
                        <div className="mt-6 space-y-5">
                            {metrics.trend.map(item => (
                                <div key={item.label}>
                                    <div className="mb-2 flex justify-between text-xs text-slate-600">
                                        <span>{item.label}</span>
                                        <span>
                                            {item.created} created · {item.completed} completed
                                        </span>
                                    </div>
                                    <div className="space-y-2">
                                        <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                                            <div
                                                className="h-full rounded-full bg-blue-500"
                                                style={{ width: `${(item.created / maxTrend) * 100}%` }}
                                            />
                                        </div>
                                        <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                                            <div
                                                className="h-full rounded-full bg-emerald-500"
                                                style={{ width: `${(item.completed / maxTrend) * 100}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>
                            ))}
                            <div className="flex gap-5 pt-1 text-xs text-slate-500">
                                <span> <span className="mr-1 inline-block h-2 w-2 rounded-full bg-blue-500" /> Created</span>
                                <span> <span className="mr-1 inline-block h-2 w-2 rounded-full bg-emerald-500" /> Completed</span>
                            </div>
                        </div>
                    )}
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <h2 className="font-semibold text-slate-900">
                        Most frequently failing rules
                    </h2>
                    <p className="mt-1 text-xs text-slate-500">
                        Failed checklist answers in the selected records
                    </p>

                    {metrics.failedRules.length === 0 ? (
                        <p className="py-12 text-center text-sm text-slate-500">
                            No failed rules found.
                        </p>
                    ) : (
                        <div className="mt-5 space-y-4">
                            {metrics.failedRules.map(rule => (
                                <div key={rule.questionId}>
                                    <div className="mb-1 flex justify-between gap-3 text-sm">
                                        <span className="text-slate-700">{rule.label}</span>
                                        <span className="shrink-0 font-semibold text-slate-900">
                                            {rule.count}
                                        </span>
                                    </div>
                                    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                                        <div
                                            className="h-full rounded-full bg-red-500"
                                            style={{ width: `${(rule.count / maxRuleCount) * 100}%` }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-4">
                    <h2 className="font-semibold text-slate-900">Site risk ranking</h2>
                    <p className="mt-1 text-xs text-slate-500">
                        Higher scores indicate more operational risk
                    </p>
                </div>

                {metrics.siteRisks.length === 0 ? (
                    <p className="py-8 text-center text-sm text-slate-500">
                        No site risk data available.
                    </p>
                ) : (
                    <div className="space-y-4">
                        {metrics.siteRisks.map((site, index) => (
                            <div key={site.siteId}>
                                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                                    <div>
                                        <span className="mr-2 text-xs text-slate-400">
                                            #{index + 1}
                                        </span>
                                        <span className="font-medium text-slate-800">
                                            {site.siteName}
                                        </span>
                                    </div>
                                    <span className="text-sm font-semibold text-slate-900">
                                        Risk score: {site.score}
                                    </span>
                                </div>
                                <div className="mb-2 h-2 overflow-hidden rounded-full bg-slate-100">
                                    <div
                                        className="h-full rounded-full bg-amber-500"
                                        style={{ width: `${(site.score / maxRisk) * 100}%` }}
                                    />
                                </div>
                                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                                    <span>{site.failedInspections} failed</span>
                                    <span>{site.overdueInspections} overdue</span>
                                    <span>{site.pendingReviews} pending reviews</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                <p className="mt-5 border-t border-slate-100 pt-3 text-xs text-slate-500">
                    Risk formula: failed inspections × 3 + overdue active inspections × 2
                    + pending reviews × 1.
                </p>
            </section>

            <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-100 p-5">
                    <h2 className="font-semibold text-slate-900">Items pending review</h2>
                    <p className="mt-1 text-xs text-slate-500">
                        {pendingReviews.length} item(s) in the selected filters
                    </p>
                </div>

                {pendingReviews.length === 0 ? (
                    <p className="p-8 text-center text-sm text-slate-500">
                        No inspections are waiting for review.
                    </p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                                <tr>
                                    <th className="px-5 py-3 font-medium">Inspection</th>
                                    <th className="px-5 py-3 font-medium">Site</th>
                                    <th className="px-5 py-3 font-medium">Submitted</th>
                                    <th className="px-5 py-3 font-medium">Review status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {pendingReviews.map(inspection => {
                                    const status = getReviewStatus(inspection)
                                    return (
                                        <tr key={inspection.id}>
                                            <td className="px-5 py-3 font-medium text-slate-800">
                                                {inspection.title}
                                                <span className="mt-1 block text-xs font-normal text-slate-400">
                                                    {inspection.id}
                                                </span>
                                            </td>
                                            <td className="px-5 py-3 text-slate-600">
                                                {getSiteName(inspection.siteId)}
                                            </td>
                                            <td className="px-5 py-3 text-slate-600">
                                                {formatDate(inspection.submittedAt ?? inspection.createdAt)}
                                            </td>
                                            <td className="px-5 py-3">
                                                <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">
                                                    {status}
                                                </span>
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>
        </div>
    )
}
