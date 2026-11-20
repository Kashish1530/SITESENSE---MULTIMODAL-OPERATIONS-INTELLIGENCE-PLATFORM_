import type { ReactNode } from 'react'
import { INSPECTION_TEMPLATES } from '../../data/inspectionData'
import { DEMO_SITES, type DemoUser } from '../../data/users'
import type {
    CorrectiveAction,
    InspectionEvidence,
    InspectionFinding,
    InspectionRecord,
} from '../../inspections/types'

type Props = {
    inspection: InspectionRecord
    users: DemoUser[]
    evidence: InspectionEvidence[]
    findings: InspectionFinding[]
    correctiveActions: CorrectiveAction[]
    onBack: () => void
}

function formatDate(value?: string) {
    if (!value) return '—'

    const date = new Date(value)

    if (Number.isNaN(date.getTime())) return '—'

    return date.toLocaleString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
    })
}

function getUserName(users: DemoUser[], userId?: string) {
    if (!userId) return '—'
    return users.find(user => user.id === userId)?.name ?? 'Unknown user'
}

function Section({
    title,
    description,
    children,
}: {
    title: string
    description?: string
    children: ReactNode
}) {
    return (
        <section className="rounded-xl border border-slate-200 bg-white">
            <div className="border-b border-slate-100 px-5 py-4">
                <h2 className="font-semibold text-slate-900">{title}</h2>
                {description && (
                    <p className="mt-1 text-sm text-slate-500">{description}</p>
                )}
            </div>
            <div className="p-5">{children}</div>
        </section>
    )
}

function EmptyState({ children }: { children: React.ReactNode }) {
    return (
        <p className="rounded-lg bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
            {children}
        </p>
    )
}

function InspectionDetail({
    inspection,
    users,
    evidence,
    findings,
    correctiveActions,
    onBack,
}: Props) {
    const template = INSPECTION_TEMPLATES.find(
        item => item.id === inspection.templateId,
    )

    const site = DEMO_SITES.find(item => item.id === inspection.siteId)

    const inspectionEvidence = evidence.filter(
        item =>
            item.inspectionId === inspection.id ||
            inspection.evidenceIds.includes(item.id),
    )

    const inspectionFindings = findings.filter(
        finding =>
            finding.inspectionId === inspection.id ||
            inspection.findingIds.includes(finding.id),
    )

    const findingIds = new Set(inspectionFindings.map(item => item.id))

    const inspectionActions = correctiveActions.filter(
        action =>
            action.inspectionId === inspection.id ||
            findingIds.has(action.findingId),
    )

    const evidenceById = new Map(
        inspectionEvidence.map(item => [item.id, item]),
    )

    const passedCount = inspection.answers.filter(
        answer => answer.result === 'Passed',
    ).length

    const failedCount = inspection.answers.filter(
        answer => answer.result === 'Failed',
    ).length

    const notApplicableCount = inspection.answers.filter(
        answer => answer.result === 'Not Applicable',
    ).length

    const statusClass =
        inspection.status === 'Completed'
            ? 'bg-green-100 text-green-700'
            : inspection.status === 'In Progress'
                ? 'bg-blue-100 text-blue-700'
                : inspection.status === 'Under Review'
                    ? 'bg-orange-100 text-orange-700'
                    : inspection.status === 'Submitted'
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-slate-100 text-slate-700'

    const resultClass = (result: string) => {
        if (result === 'Passed') return 'bg-green-100 text-green-700'
        if (result === 'Failed') return 'bg-red-100 text-red-700'
        return 'bg-slate-100 text-slate-700'
    }

    const renderEvidenceList = (ids: string[]) => {
        const linkedEvidence = ids
            .map(id => evidenceById.get(id))
            .filter((item): item is InspectionEvidence => Boolean(item))

        if (linkedEvidence.length === 0) {
            return <p className="text-xs text-slate-400">No linked evidence.</p>
        }

        return (
            <ul className="mt-2 space-y-2">
                {linkedEvidence.map(item => (
                    <li
                        key={item.id}
                        className="flex flex-wrap items-center gap-2 text-sm"
                    >
                        <span className="font-medium text-slate-700">
                            {item.fileName}
                        </span>
                        <span className="text-xs text-slate-400">
                            {item.type} · {item.fileSizeLabel}
                        </span>
                        {item.previewUrl && (
                            <a
                                href={item.previewUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs font-medium text-blue-600 hover:underline"
                            >
                                Open preview
                            </a>
                        )}
                    </li>
                ))}
            </ul>
        )
    }

    return (
        <div className="space-y-6">
            <div>
                <button
                    type="button"
                    onClick={onBack}
                    className="mb-4 inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800"
                >
                    <span aria-hidden="true">←</span>
                    Back to inspections
                </button>

                <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                    <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                            Inspection detail
                        </p>
                        <h1 className="mt-1 text-2xl font-bold text-slate-900">
                            {inspection.title}
                        </h1>
                        <p className="mt-1 text-sm text-slate-500">
                            {inspection.id}
                        </p>
                    </div>

                    <span
                        className={`w-fit rounded-full px-3 py-1.5 text-sm font-semibold ${statusClass}`}
                    >
                        {inspection.status}
                    </span>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="rounded-xl border border-green-200 bg-green-50 p-5">
                    <p className="text-sm font-medium text-green-700">Passed</p>
                    <p className="mt-2 text-3xl font-bold text-green-800">
                        {passedCount}
                    </p>
                </div>
                <div className="rounded-xl border border-red-200 bg-red-50 p-5">
                    <p className="text-sm font-medium text-red-700">Failed</p>
                    <p className="mt-2 text-3xl font-bold text-red-800">
                        {failedCount}
                    </p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
                    <p className="text-sm font-medium text-slate-600">
                        Not Applicable
                    </p>
                    <p className="mt-2 text-3xl font-bold text-slate-800">
                        {notApplicableCount}
                    </p>
                </div>
            </div>

            <Section title="Inspection information">
                <div className="grid grid-cols-1 gap-x-8 gap-y-5 sm:grid-cols-2">
                    <div>
                        <p className="text-xs text-slate-400">Description</p>
                        <p className="mt-1 text-sm text-slate-700">
                            {inspection.description || 'No description provided.'}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-400">Inspection type</p>
                        <p className="mt-1 text-sm text-slate-700">
                            {inspection.type}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-400">Site / Zone</p>
                        <p className="mt-1 text-sm text-slate-700">
                            {site?.name ?? 'Unknown site'} / {inspection.zone || '—'}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-400">Template</p>
                        <p className="mt-1 text-sm text-slate-700">
                            {template?.name ?? 'Template unavailable'}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-400">Assigned inspector</p>
                        <p className="mt-1 text-sm text-slate-700">
                            {getUserName(users, inspection.assignedToUserId)}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-400">Assigned by</p>
                        <p className="mt-1 text-sm text-slate-700">
                            {getUserName(users, inspection.assignedByUserId)}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-400">Reviewer</p>
                        <p className="mt-1 text-sm text-slate-700">
                            {getUserName(users, inspection.reviewerUserId)}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-400">Created</p>
                        <p className="mt-1 text-sm text-slate-700">
                            {formatDate(inspection.createdAt)}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-400">Scheduled</p>
                        <p className="mt-1 text-sm text-slate-700">
                            {formatDate(inspection.scheduledAt)}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-400">Due date</p>
                        <p className="mt-1 text-sm text-slate-700">
                            {formatDate(inspection.dueDate)}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-400">Started</p>
                        <p className="mt-1 text-sm text-slate-700">
                            {formatDate(inspection.startedAt)}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-400">Submitted</p>
                        <p className="mt-1 text-sm text-slate-700">
                            {formatDate(inspection.submittedAt)}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-400">Completed</p>
                        <p className="mt-1 text-sm text-slate-700">
                            {formatDate(inspection.completedAt)}
                        </p>
                    </div>
                </div>

                {inspection.reviewNotes && (
                    <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4">
                        <p className="text-xs font-semibold text-amber-800">
                            Review notes
                        </p>
                        <p className="mt-1 text-sm text-amber-900">
                            {inspection.reviewNotes}
                        </p>
                    </div>
                )}
            </Section>

            <Section
                title="Checklist results"
                description={`${inspection.answers.length} recorded answer(s)`}
            >
                {inspection.answers.length === 0 ? (
                    <EmptyState>No checklist answers have been recorded.</EmptyState>
                ) : (
                    <div className="space-y-4">
                        {inspection.answers.map((answer, index) => {
                            const question = template?.checklist.find(
                                item => item.id === answer.questionId,
                            )

                            return (
                                <article
                                    key={`${answer.questionId}-${index}`}
                                    className="rounded-lg border border-slate-100 p-4"
                                >
                                    <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
                                        <div>
                                            <p className="text-xs text-slate-400">
                                                {answer.questionId}
                                            </p>
                                            <h3 className="mt-1 font-medium text-slate-900">
                                                {question?.question ?? 'Question details unavailable'}
                                            </h3>
                                            {question?.description && (
                                                <p className="mt-1 text-sm text-slate-500">
                                                    {question.description}
                                                </p>
                                            )}
                                        </div>
                                        <span
                                            className={`w-fit rounded-full px-2.5 py-1 text-xs font-semibold ${resultClass(answer.result)}`}
                                        >
                                            {answer.result}
                                        </span>
                                    </div>

                                    <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
                                        {question && (
                                            <span>
                                                {question.required ? 'Required' : 'Optional'}
                                            </span>
                                        )}
                                        {question?.requiresEvidenceOnFail && (
                                            <span>Evidence required on failure</span>
                                        )}
                                    </div>

                                    {answer.comment && (
                                        <p className="mt-3 rounded-md bg-slate-50 p-3 text-sm text-slate-600">
                                            {answer.comment}
                                        </p>
                                    )}

                                    {renderEvidenceList(answer.evidenceIds ?? [])}
                                </article>
                            )
                        })}
                    </div>
                )}
            </Section>

            <Section
                title="Evidence"
                description={`${inspectionEvidence.length} evidence record(s) linked to this inspection`}
            >
                {inspectionEvidence.length === 0 ? (
                    <EmptyState>
                        No evidence metadata is linked to this inspection.
                    </EmptyState>
                ) : (
                    <div className="divide-y divide-slate-100">
                        {inspectionEvidence.map(item => (
                            <div
                                key={item.id}
                                className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between"
                            >
                                <div className="min-w-0">
                                    <p className="break-words font-medium text-slate-800">
                                        {item.fileName}
                                    </p>
                                    <p className="mt-1 text-xs text-slate-500">
                                        {item.type} · {item.mimeType} · {item.fileSizeLabel}
                                    </p>
                                    {item.caption && (
                                        <p className="mt-1 text-sm text-slate-600">
                                            {item.caption}
                                        </p>
                                    )}
                                    <p className="mt-1 text-xs text-slate-400">
                                        Uploaded by {getUserName(users, item.uploadedByUserId)}
                                        {' · '}
                                        {formatDate(item.uploadedAt)}
                                    </p>
                                </div>
                                {item.previewUrl ? (
                                    <a
                                        href={item.previewUrl}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="text-sm font-medium text-blue-600 hover:underline"
                                    >
                                        Open preview
                                    </a>
                                ) : (
                                    <span className="text-xs text-slate-400">
                                        Metadata only · preview unavailable
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </Section>

            <Section title="Findings">
                {inspectionFindings.length === 0 ? (
                    <EmptyState>No findings are linked to this inspection.</EmptyState>
                ) : (
                    <div className="space-y-4">
                        {inspectionFindings.map(finding => {
                            const findingEvidence = inspectionEvidence
                                .filter(item => item.findingId === finding.id)
                                .map(item => item.id)

                            return (
                                <article
                                    key={finding.id}
                                    className="rounded-lg border border-slate-100 p-4"
                                >
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <h3 className="font-semibold text-slate-900">
                                            {finding.title}
                                        </h3>
                                        <div className="flex gap-2">
                                            <span className="rounded-full bg-orange-50 px-2.5 py-1 text-xs font-medium text-orange-700">
                                                {finding.severity}
                                            </span>
                                            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                                                {finding.status}
                                            </span>
                                        </div>
                                    </div>
                                    <p className="mt-2 text-sm text-slate-600">
                                        {finding.description}
                                    </p>
                                    <div className="mt-3 text-xs text-slate-500">
                                        <p>Location: {finding.location || '—'}</p>
                                        <p className="mt-1">
                                            Reported by {getUserName(users, finding.reportedByUserId)}
                                            {' · '}
                                            {formatDate(finding.createdAt)}
                                        </p>
                                        <p className="mt-1">
                                            Recommended action: {finding.recommendedAction || '—'}
                                        </p>
                                        {finding.verifiedByUserId && (
                                            <p className="mt-1">
                                                Verified by {getUserName(users, finding.verifiedByUserId)}
                                                {finding.verifiedAt
                                                    ? ` · ${formatDate(finding.verifiedAt)}`
                                                    : ''}
                                            </p>
                                        )}
                                    </div>
                                    {renderEvidenceList(findingEvidence)}
                                </article>
                            )
                        })}
                    </div>
                )}
            </Section>

            <Section title="Corrective actions">
                {inspectionActions.length === 0 ? (
                    <EmptyState>
                        No corrective actions are linked to this inspection.
                    </EmptyState>
                ) : (
                    <div className="space-y-4">
                        {inspectionActions.map(action => (
                            <article
                                key={action.id}
                                className="rounded-lg border border-slate-100 p-4"
                            >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <h3 className="font-semibold text-slate-900">
                                        {action.title}
                                    </h3>
                                    <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700">
                                        {action.status}
                                    </span>
                                </div>
                                <p className="mt-2 text-sm text-slate-600">
                                    {action.description}
                                </p>
                                <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-500 sm:grid-cols-2">
                                    <p>Assigned to: {getUserName(users, action.assignedToUserId)}</p>
                                    <p>Assigned by: {getUserName(users, action.assignedByUserId)}</p>
                                    <p>Due: {formatDate(action.dueDate)}</p>
                                    <p>Completed: {formatDate(action.completedAt)}</p>
                                </div>
                                {action.completionNotes && (
                                    <p className="mt-3 rounded-md bg-slate-50 p-3 text-sm text-slate-600">
                                        {action.completionNotes}
                                    </p>
                                )}
                                {action.verifiedByUserId && (
                                    <p className="mt-2 text-xs text-slate-500">
                                        Verified by {getUserName(users, action.verifiedByUserId)}
                                        {action.verifiedAt
                                            ? ` · ${formatDate(action.verifiedAt)}`
                                            : ''}
                                    </p>
                                )}
                                {renderEvidenceList(action.evidenceIds ?? [])}
                            </article>
                        ))}
                    </div>
                )}
            </Section>

            <Section
                title="Observations"
                description={`${inspection.observations.length} observation(s) recorded`}
            >
                {inspection.observations.length === 0 ? (
                    <EmptyState>No observations were recorded.</EmptyState>
                ) : (
                    <div className="space-y-3">
                        {inspection.observations.map(observation => (
                            <article
                                key={observation.id}
                                className="rounded-lg border border-slate-100 p-4"
                            >
                                <p className="text-sm text-slate-700">
                                    {observation.description}
                                </p>
                                <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
                                    <span>{observation.location || 'Location not specified'}</span>
                                    <span>
                                        Reported by {getUserName(users, observation.reportedByUserId)}
                                    </span>
                                    <span>{formatDate(observation.createdAt)}</span>
                                </div>
                                {renderEvidenceList(observation.evidenceIds ?? [])}
                            </article>
                        ))}
                    </div>
                )}
            </Section>
        </div>
    )
}

export default InspectionDetail