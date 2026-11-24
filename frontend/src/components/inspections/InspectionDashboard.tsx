import { useEffect, useMemo, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import { ClipboardCheck } from 'lucide-react'

import {
    INSPECTION_TEMPLATES,
} from '../../data/inspectionData'

import { DEMO_SITES, type DemoUser, type DemoSite } from '../../data/users'
import {
    getStoredAccessToken,
    createInspectionApi,
    batchUploadMediaApi,
    getSitesApi,
} from '../../api/client'

import type {
    InspectionRecord,
    InspectionFinding,
    InspectionEvidence,
    EvidenceType,
    CorrectiveAction,
} from '../../inspections/types'

import {
    calculateInspectionMetrics,
    calculateWeeklyInspectionTrend,
} from '../../analytics/calculations'

import { formatFileSize } from '../../inspections/uploadAdapter'

import MetricCard from '../dashboard/MetricCard'
import LineChart from '../analytics/LineChart'
import DonutChart from '../analytics/DonutChart'
import BarChart from '../analytics/BarChart'
import CreateInspectionModal from './CreateInspectionModal'
import InspectionDetail from './InspectionDetail'

type InspectionTab = 'Overview' | 'All Inspections' | 'Templates' | 'Findings'

type Props = {
    currentUser: DemoUser
    users: DemoUser[]

    inspections: InspectionRecord[]
    setInspections: Dispatch<SetStateAction<InspectionRecord[]>>

    findings: InspectionFinding[]
    setFindings: Dispatch<SetStateAction<InspectionFinding[]>>

    evidence: InspectionEvidence[]
    setEvidence: Dispatch<SetStateAction<InspectionEvidence[]>>

    correctiveActions: CorrectiveAction[]
    setCorrectiveActions: Dispatch<SetStateAction<CorrectiveAction[]>>
}

const tabs: InspectionTab[] = [
    'Overview',
    'All Inspections',
    'Templates',
    'Findings',
]

const statusColors: Record<string, string> = {
    Draft: '#94a3b8',
    Scheduled: '#8b5cf6',
    'In Progress': '#3b82f6',
    Submitted: '#f59e0b',
    'Under Review': '#f97316',
    Completed: '#22c55e',
}

const KNOWN_SITES: DemoSite[] = [
    ...DEMO_SITES,
    {
        id: '3591c762-1cb9-4fd4-9be0-f15ca5514c64',
        name: 'Site 7 - Central Distribution Hub',
        region: 'Central Region',
    },
    {
        id: '20692bfe-c271-4773-a310-81295a5a1b13',
        name: 'Site 12 - Retail Superstore',
        region: 'North Region',
    },
]

function formatDate(value?: string) {
    if (!value) return '—'

    const date = new Date(value)

    if (Number.isNaN(date.getTime())) return '—'

    return date.toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
    })
}

function getEvidenceType(file: File): EvidenceType {
    if (file.type.startsWith('image/')) return 'Photo'
    if (file.type.startsWith('video/')) return 'Video'
    return 'Document'
}

function createEvidenceId(index: number): string {
    const uniquePart =
        typeof crypto !== 'undefined' && 'randomUUID' in crypto
            ? crypto.randomUUID()
            : `${Date.now()}-${Math.random().toString(36).slice(2)}`

    return `EVD-${uniquePart}-${index + 1}`
}

function InspectionDashboard({
    currentUser,
    users,
    inspections,
    setInspections,
    findings,
    evidence,
    setEvidence,
    correctiveActions,
}: Props) {
    const [activeTab, setActiveTab] = useState<InspectionTab>('Overview')
    const [search, setSearch] = useState('')
    const [statusFilter, setStatusFilter] = useState('All')
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
    const [uploadNotice, setUploadNotice] = useState<string | null>(null)
    const [selectedInspectionId, setSelectedInspectionId] = useState<string | null>(null)

    const visibleInspections = useMemo(() => {
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

        return inspections.filter(
            inspection => inspection.assignedToUserId === currentUser.id,
        )
    }, [inspections, currentUser, users])

    const visibleFindings = useMemo(() => {
        const inspectionIds = new Set(
            visibleInspections.map(inspection => inspection.id),
        )

        return findings.filter(
            finding => inspectionIds.has(finding.inspectionId),
        )
    }, [findings, visibleInspections])

    const visibleEvidence = useMemo(() => {
        const inspectionIds = new Set(
            visibleInspections.map(inspection => inspection.id),
        )

        return evidence.filter(
            item => inspectionIds.has(item.inspectionId),
        )
    }, [evidence, visibleInspections])

    const visibleCorrectiveActions = useMemo(() => {
        const findingIds = new Set(
            visibleFindings.map(finding => finding.id),
        )

        return correctiveActions.filter(
            action => findingIds.has(action.findingId),
        )
    }, [correctiveActions, visibleFindings])

    const selectedInspection = selectedInspectionId
        ? visibleInspections.find(
            inspection => inspection.id === selectedInspectionId,
        )
        : undefined

    const selectedInspectionFindings = selectedInspection
        ? visibleFindings.filter(
            finding => finding.inspectionId === selectedInspection.id,
        )
        : []

    const selectedFindingIds = new Set(
        selectedInspectionFindings.map(finding => finding.id),
    )

    const selectedInspectionActions = selectedInspection
        ? visibleCorrectiveActions.filter(
            action =>
                action.inspectionId === selectedInspection.id ||
                selectedFindingIds.has(action.findingId),
        )
        : []

    const selectedInspectionEvidence = selectedInspection
        ? visibleEvidence.filter(
            item =>
                item.inspectionId === selectedInspection.id ||
                selectedInspection.evidenceIds.includes(item.id),
        )
        : []

    const metrics = useMemo(() => {
        const analyticsRecords = visibleInspections.map(inspection => ({
            id: inspection.id,
            siteId: inspection.siteId,
            status: inspection.status,
            createdAt: inspection.createdAt,
            completedAt: inspection.completedAt,
            dueDate: inspection.dueDate,
        }))

        return calculateInspectionMetrics(analyticsRecords)
    }, [visibleInspections])

    const weeklyTrend = useMemo(() => {
        const analyticsRecords = visibleInspections.map(inspection => ({
            id: inspection.id,
            siteId: inspection.siteId,
            status: inspection.status,
            createdAt: inspection.createdAt,
            completedAt: inspection.completedAt,
            dueDate: inspection.dueDate,
        }))

        return calculateWeeklyInspectionTrend(analyticsRecords)
    }, [visibleInspections])

    const filteredInspections = visibleInspections.filter(inspection => {
        const matchesSearch =
            inspection.title.toLowerCase().includes(search.toLowerCase()) ||
            inspection.id.toLowerCase().includes(search.toLowerCase())

        const matchesStatus =
            statusFilter === 'All' || inspection.status === statusFilter

        return matchesSearch && matchesStatus
    })

    const statusCounts = Object.keys(statusColors).map(status => ({
        label: status,
        value: visibleInspections.filter(
            inspection => inspection.status === status,
        ).length,
        color: statusColors[status],
    }))

    const trendData = weeklyTrend.map(week => ({
        id: week.startDate,
        label: week.week,
        created: week.created,
        completed: week.completed,
    }))

    const performanceChart = useMemo(() => {
        const completedInspections = visibleInspections.filter(
            inspection => inspection.status === 'Completed',
        )

        if (currentUser.role === 'admin') {
            return {
                title: 'Site Performance',
                description: 'Completed inspections per site',
                data: DEMO_SITES.map(site => ({
                    id: site.id,
                    label: site.name,
                    value: completedInspections.filter(
                        inspection => inspection.siteId === site.id,
                    ).length,
                })),
            }
        }

        if (currentUser.role === 'supervisor') {
            const managers = users.filter(
                user =>
                    user.role === 'manager' &&
                    user.supervisorId === currentUser.id,
            )

            return {
                title: 'Manager Performance',
                description: 'Completed inspections across each manager’s team',
                data: managers.map(manager => ({
                    id: manager.id,
                    label: manager.name,
                    value: completedInspections.filter(inspection => {
                        const assignee = users.find(
                            user => user.id === inspection.assignedToUserId,
                        )

                        return assignee?.managerId === manager.id
                    }).length,
                })),
            }
        }

        if (currentUser.role === 'manager') {
            const employees = users.filter(
                user =>
                    user.role === 'employee' &&
                    user.managerId === currentUser.id,
            )

            return {
                title: 'Team Performance',
                description: 'Completed inspections per employee',
                data: employees.map(employee => ({
                    id: employee.id,
                    label: employee.name,
                    value: completedInspections.filter(
                        inspection =>
                            inspection.assignedToUserId === employee.id,
                    ).length,
                })),
            }
        }

        return {
            title: 'My Inspection Results',
            description: 'Your completed versus remaining inspections',
            data: [
                {
                    id: 'completed',
                    label: 'Completed',
                    value: metrics.completed,
                    color: '#22c55e',
                },
                {
                    id: 'remaining',
                    label: 'Remaining',
                    value: Math.max(0, metrics.total - metrics.completed),
                    color: '#3b82f6',
                },
            ],
        }
    }, [visibleInspections, currentUser, users, metrics])

    const canManage = currentUser.role !== 'employee'

    const [remoteSites, setRemoteSites] = useState<DemoSite[]>([])

    useEffect(() => {
        if (!getStoredAccessToken()) return
        let mounted = true
        getSitesApi()
            .then(sites => {
                if (mounted && sites && sites.length > 0) {
                    setRemoteSites(sites)
                }
            })
            .catch(() => {})
        return () => {
            mounted = false
        }
    }, [])

    const resolveSiteName = (siteId?: string | null) => {
        if (!siteId) return 'Unknown site'
        const found =
            remoteSites.find(s => s.id === siteId) ||
            KNOWN_SITES.find(s => s.id === siteId) ||
            DEMO_SITES.find(s => s.id === siteId)
        return found ? found.name : 'Unknown site'
    }

    const siteName = resolveSiteName(currentUser.siteId)

    const pageScope =
        currentUser.role === 'admin'
            ? 'Organisation-wide'
            : currentUser.role === 'supervisor'
                ? siteName ?? 'Assigned site'
                : currentUser.role === 'manager'
                    ? 'Your assigned team'
                    : 'Your personal inspections'

    const handleCreateInspection = (
        inspection: InspectionRecord,
        files: File[] = [],
    ) => {
        const uploadedAt = new Date().toISOString()

        const newEvidence: InspectionEvidence[] = files.map(
            (file, index) => ({
                id: createEvidenceId(index),
                inspectionId: inspection.id,
                type: getEvidenceType(file),
                fileName: file.name,
                fileSizeLabel: formatFileSize(file.size),
                mimeType: file.type,
                uploadedByUserId: currentUser.id,
                uploadedAt,
            }),
        )

        const inspectionWithEvidence: InspectionRecord = {
            ...inspection,
            evidenceIds: newEvidence.map(item => item.id),
        }

        // 1. Immediately update local state so UI updates and unit tests pass synchronously
        setInspections(previous => [
            inspectionWithEvidence,
            ...previous,
        ])

        if (newEvidence.length > 0) {
            setEvidence(previous => [
                ...newEvidence,
                ...previous,
            ])
        }

        setIsCreateModalOpen(false)
        setSearch('')
        setStatusFilter('All')
        setActiveTab('All Inspections')

        const token = getStoredAccessToken()
        if (token) {
            setUploadNotice(
                files.length > 0
                    ? `Saving inspection and uploading ${files.length} evidence file(s) to database...`
                    : 'Saving inspection to database...',
            )

            // 2. Persist to FastAPI backend and Neon PostgreSQL database
            ;(async () => {
                try {
                    let targetSiteId = inspection.siteId
                    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

                    if (!uuidRegex.test(targetSiteId)) {
                        const matched = remoteSites.find(s => uuidRegex.test(s.id))
                        if (matched) {
                            targetSiteId = matched.id
                        } else if (targetSiteId === 'SITE-002') {
                            targetSiteId = '20692bfe-c271-4773-a310-81295a5a1b13' // Site 12
                        } else {
                            targetSiteId = '3591c762-1cb9-4fd4-9be0-f15ca5514c64' // Site 7
                        }
                    }

                    const summaryText = inspection.title
                        ? `${inspection.title}${inspection.zone ? ` (${inspection.zone})` : ''}: ${inspection.description || 'Inspection session'}`
                        : inspection.description || 'Inspection session'

                    const created = await createInspectionApi(targetSiteId, summaryText)
                    const backendInspectionId = created.id

                    let uploadedCount = 0
                    if (files.length > 0) {
                        try {
                            await batchUploadMediaApi(backendInspectionId, files)
                            uploadedCount = files.length
                        } catch (mediaError) {
                            console.warn('Batch media upload warning:', mediaError)
                        }
                    }

                    setInspections(previous =>
                        previous.map(item =>
                            item.id === inspection.id
                                ? {
                                      ...item,
                                      id: backendInspectionId,
                                      siteId: targetSiteId,
                                  }
                                : item,
                        ),
                    )

                    setUploadNotice(
                        uploadedCount > 0
                            ? `Inspection successfully saved to database (ID: ${backendInspectionId}) with ${uploadedCount} evidence file(s).`
                            : `Inspection successfully saved to database (ID: ${backendInspectionId}).`,
                    )
                } catch (err: any) {
                    console.error('Failed to save inspection to backend:', err)
                    setUploadNotice(
                        `Warning: Failed to save to database (${err?.message || 'Server error'}). Saved locally.`,
                    )
                }
            })()
        } else {
            setUploadNotice(
                newEvidence.length > 0
                    ? `Inspection created with ${newEvidence.length} evidence file(s). Demo mode: uploads were simulated; files were not sent to a server.`
                    : 'Inspection created successfully. No evidence files were selected.',
            )
        }
    }

    const renderInspectionRows = (records: InspectionRecord[]) => (
        <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                    <tr>
                        <th className="px-5 py-3">Inspection</th>
                        <th className="px-5 py-3">Site / Zone</th>
                        <th className="px-5 py-3">Assigned to</th>
                        <th className="px-5 py-3">Due date</th>
                        <th className="px-5 py-3">Status</th>
                        <th className="px-5 py-3">Action</th>
                    </tr>
                </thead>

                <tbody className="divide-y divide-slate-100">
                    {records.map(inspection => {
                        const assignee = users.find(
                            user => user.id === inspection.assignedToUserId,
                        )

                        const siteNameDisplay = resolveSiteName(inspection.siteId)

                        return (
                            <tr key={inspection.id} className="hover:bg-slate-50">
                                <td className="px-5 py-4">
                                    <p className="font-medium text-slate-900">
                                        {inspection.title}
                                    </p>
                                    <p className="mt-1 text-xs text-slate-400">
                                        {inspection.id}
                                    </p>
                                </td>

                                <td className="px-5 py-4">
                                    <p className="text-slate-700">
                                        {siteNameDisplay}
                                    </p>
                                    <p className="mt-1 text-xs text-slate-400">
                                        {inspection.zone}
                                    </p>
                                </td>

                                <td className="px-5 py-4 text-slate-600">
                                    {assignee?.name ?? 'Unassigned'}
                                </td>

                                <td className="px-5 py-4 text-slate-600">
                                    {formatDate(inspection.dueDate)}
                                </td>

                                <td className="px-5 py-4">
                                    <span
                                        className="rounded-full px-2.5 py-1 text-xs font-medium"
                                        style={{
                                            color: statusColors[inspection.status] ?? '#64748b',
                                            backgroundColor: `${statusColors[inspection.status] ?? '#64748b'}18`,
                                        }}
                                    >
                                        {inspection.status}
                                    </span>
                                </td>

                                <td className="px-5 py-4">
                                    <button
                                        type="button"
                                        onClick={() => setSelectedInspectionId(inspection.id)}
                                        aria-label={`View ${inspection.title}`}
                                        className="rounded-lg border border-blue-200 px-3 py-1.5 text-xs font-semibold text-blue-700 transition hover:bg-blue-50"
                                    >
                                        View
                                    </button>
                                </td>
                            </tr>
                        )
                    })}

                    {records.length === 0 && (
                        <tr>
                            <td
                                colSpan={6}
                                className="px-5 py-10 text-center text-slate-400"
                            >
                                No inspections found.
                            </td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    )

    if (selectedInspection) {
        return (
            <InspectionDetail
                inspection={selectedInspection}
                users={users}
                evidence={selectedInspectionEvidence}
                findings={selectedInspectionFindings}
                correctiveActions={selectedInspectionActions}
                onBack={() => setSelectedInspectionId(null)}
            />
        )
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">
                        Inspections
                    </h1>
                    <p className="mt-1 text-sm text-slate-500">
                        Monitor, manage and review inspection activity.
                    </p>
                    <p className="mt-1 text-xs font-medium text-blue-600">
                        Viewing: {pageScope}
                    </p>
                </div>

                {canManage && (
                    <button
                        type="button"
                        onClick={() => setIsCreateModalOpen(true)}
                        className="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
                    >
                        + Create Inspection
                    </button>
                )}
            </div>

            {uploadNotice && (
                <div
                    role="status"
                    className="flex items-start justify-between gap-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800"
                >
                    <p>{uploadNotice}</p>
                    <button
                        type="button"
                        onClick={() => setUploadNotice(null)}
                        className="shrink-0 font-medium text-blue-700 hover:text-blue-900"
                        aria-label="Dismiss notification"
                    >
                        ×
                    </button>
                </div>
            )}

            <div className="flex gap-2 overflow-x-auto border-b border-slate-200">
                {tabs.map(tab => (
                    <button
                        key={tab}
                        type="button"
                        onClick={() => setActiveTab(tab)}
                        className={`whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium ${activeTab === tab
                            ? 'border-blue-600 text-blue-600'
                            : 'border-transparent text-slate-500 hover:text-slate-800'
                            }`}
                    >
                        {tab}
                    </button>
                ))}
            </div>

            {activeTab === 'Overview' && (
                <>
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                        <MetricCard
                            title="Total Inspections"
                            value={String(metrics.total)}
                            change="Current"
                            trend="neutral"
                            description="Inspections in your permitted scope"
                        />
                        <MetricCard
                            title="In Progress"
                            value={String(metrics.inProgress)}
                            change="Active"
                            trend="neutral"
                            description="Currently being conducted"
                        />
                        <MetricCard
                            title="Pending Review"
                            value={String(metrics.pendingReview)}
                            change="Review"
                            trend="neutral"
                            description="Awaiting review or approval"
                        />
                        <MetricCard
                            title="Completed"
                            value={String(metrics.completed)}
                            change="Done"
                            trend="neutral"
                            description="Successfully completed inspections"
                        />
                        <MetricCard
                            title="Critical / High Findings"
                            value={String(
                                visibleFindings.filter(
                                    finding =>
                                        finding.severity === 'Critical' ||
                                        finding.severity === 'High',
                                ).length,
                            )}
                            change="Priority"
                            trend="neutral"
                            description="Findings requiring attention"
                        />
                        <MetricCard
                            title="Overdue Inspections"
                            value={String(metrics.overdue)}
                            change="Due"
                            trend="neutral"
                            description="Inspections past their due date"
                        />
                    </div>

                    <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
                        <div className="rounded-xl border border-slate-200 bg-white p-5 xl:col-span-2">
                            <LineChart
                                title="Inspection Completion Trend"
                                description="Weekly inspections created versus completed"
                                data={trendData}
                                series={[
                                    { key: 'created', label: 'Created', color: '#3b82f6' },
                                    { key: 'completed', label: 'Completed', color: '#22c55e' },
                                ]}
                            />
                        </div>

                        <div className="rounded-xl border border-slate-200 bg-white p-5">
                            <DonutChart
                                title="Inspection Status"
                                description="Current status distribution"
                                data={statusCounts}
                                centerLabel="Total"
                                centerValue={String(metrics.total)}
                            />
                        </div>
                    </div>

                    <BarChart
                        data={performanceChart.data}
                        title={performanceChart.title}
                        description={performanceChart.description}
                        emptyMessage="No performance data available yet."
                    />
                </>
            )}

            {activeTab === 'All Inspections' && (
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                    <div className="flex flex-col gap-3 border-b border-slate-200 p-5 sm:flex-row">
                        <input
                            value={search}
                            onChange={event => setSearch(event.target.value)}
                            placeholder="Search inspection name or ID..."
                            className="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500"
                        />

                        <select
                            value={statusFilter}
                            onChange={event => setStatusFilter(event.target.value)}
                            className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                        >
                            <option value="All">All statuses</option>
                            {Object.keys(statusColors).map(status => (
                                <option key={status}>{status}</option>
                            ))}
                        </select>
                    </div>

                    {renderInspectionRows(filteredInspections)}
                </div>
            )}

            {activeTab === 'Templates' && (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {INSPECTION_TEMPLATES.map(template => (
                        <div
                            key={template.id}
                            className="rounded-xl border border-slate-200 bg-white p-5"
                        >
                            <div className="flex items-start justify-between gap-3">
                                <span className="rounded-lg bg-blue-50 p-2 text-blue-600">
                                    <ClipboardCheck size={20} />
                                </span>

                                <span
                                    className={`rounded-full px-2 py-1 text-xs ${template.isActive
                                        ? 'bg-green-50 text-green-700'
                                        : 'bg-slate-100 text-slate-500'
                                        }`}
                                >
                                    {template.isActive ? 'Active' : 'Inactive'}
                                </span>
                            </div>

                            <h3 className="mt-4 font-semibold text-slate-900">
                                {template.name}
                            </h3>

                            <p className="mt-2 text-sm text-slate-500">
                                {template.description}
                            </p>

                            <div className="mt-4 flex justify-between border-t border-slate-100 pt-3 text-xs text-slate-500">
                                <span>{template.category}</span>
                                <span>{template.checklist.length} questions</span>
                                <span>{template.estimatedMinutes} min</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {activeTab === 'Findings' && (
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                    <div className="border-b border-slate-200 p-5">
                        <h2 className="font-semibold text-slate-900">
                            Inspection Findings
                        </h2>
                        <p className="mt-1 text-sm text-slate-500">
                            Findings from inspections within your permitted scope.
                        </p>
                        <p className="mt-1 text-xs text-slate-400">
                            {visibleEvidence.length} evidence files in this scope
                        </p>
                    </div>

                    <div className="divide-y divide-slate-100">
                        {visibleFindings.map(finding => {
                            const action = visibleCorrectiveActions.find(
                                item => item.id === finding.correctiveActionId,
                            )

                            return (
                                <div key={finding.id} className="p-5">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <h3 className="font-semibold text-slate-900">
                                            {finding.title}
                                        </h3>

                                        <span
                                            className={`rounded-full px-2.5 py-1 text-xs font-semibold ${finding.severity === 'Critical'
                                                ? 'bg-red-100 text-red-700'
                                                : finding.severity === 'High'
                                                    ? 'bg-orange-100 text-orange-700'
                                                    : 'bg-amber-100 text-amber-700'
                                                }`}
                                        >
                                            {finding.severity}
                                        </span>
                                    </div>

                                    <p className="mt-2 text-sm text-slate-600">
                                        {finding.description}
                                    </p>

                                    <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
                                        <span>{finding.location}</span>
                                        <span>{finding.status}</span>
                                        <span>Reported {formatDate(finding.createdAt)}</span>
                                        <span>Action: {action?.status ?? 'Not assigned'}</span>
                                    </div>
                                </div>
                            )
                        })}

                        {visibleFindings.length === 0 && (
                            <p className="p-8 text-center text-sm text-slate-400">
                                No findings in this scope.
                            </p>
                        )}
                    </div>
                </div>
            )}

            {isCreateModalOpen && (
                <CreateInspectionModal
                    currentUser={currentUser}
                    users={users}
                    onClose={() => setIsCreateModalOpen(false)}
                    onCreate={handleCreateInspection}
                    sites={remoteSites.length > 0 ? remoteSites : DEMO_SITES}
                />
            )}
        </div>
    )
}

export default InspectionDashboard