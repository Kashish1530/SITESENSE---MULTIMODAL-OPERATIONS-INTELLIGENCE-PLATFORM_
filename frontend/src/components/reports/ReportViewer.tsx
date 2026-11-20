import { useMemo, useState } from 'react'
import { INSPECTION_TEMPLATES } from '../../data/inspectionData'
import type { DemoUser } from '../../data/users'
import type {
    CorrectiveAction,
    InspectionEvidence,
    InspectionFinding,
    InspectionRecord,
} from '../../inspections/types'
import {
    buildInspectionReport,
    getReportCompletionLabel,
    getVisibleReportInspections,
} from '../../reports/reportUtils'

type Props = {
    currentUser: DemoUser
    users: DemoUser[]
    inspections: InspectionRecord[]
    findings: InspectionFinding[]
    evidence: InspectionEvidence[]
    correctiveActions: CorrectiveAction[]
}

function formatDate(value?: string) {
    if (!value) return 'Not recorded'

    const date = new Date(value)

    if (Number.isNaN(date.getTime())) return 'Not recorded'

    return date.toLocaleString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
    })
}

function Section({
    title,
    children,
}: {
    title: string
    children: React.ReactNode
}) {
    return (
        <section className="rounded-xl border border-slate-200 bg-white">
            <div className="border-b border-slate-100 px-5 py-4">
                <h2 className="font-semibold text-slate-900">{title}</h2>
            </div>
            <div className="p-5">{children}</div>
        </section>
    )
}

export default function ReportViewer({
    currentUser,
    users,
    inspections,
    findings,
    evidence,
    correctiveActions,
}: Props) {
    const visibleInspections = useMemo(
        () => getVisibleReportInspections(currentUser, users, inspections),
        [currentUser, users, inspections],
    )

    const [selectedId, setSelectedId] = useState('')

    const selectedInspection =
        visibleInspections.find(item => item.id === selectedId) ??
        visibleInspections[0]

    const report = selectedInspection
        ? buildInspectionReport(
            selectedInspection,
            users,
            findings,
            evidence,
            correctiveActions,
        )
        : null

    const template = report
        ? INSPECTION_TEMPLATES.find(
            item => item.id === report.inspection.templateId,
        )
        : undefined

    const completionLabel = report
        ? getReportCompletionLabel(report.inspection)
        : ''

    const passedCount =
        report?.inspection.answers.filter(
            answer => answer.result === 'Passed',
        ).length ?? 0

    const failedCount =
        report?.inspection.answers.filter(
            answer => answer.result === 'Failed',
        ).length ?? 0

    const notApplicableCount =
        report?.inspection.answers.filter(
            answer => answer.result === 'Not Applicable',
        ).length ?? 0

    const handlePrint = () => {
        window.print()
    }

    return (
        <div className="space-y-6">
            <div className="report-controls flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">
                        Report Viewer
                    </h1>
                    <p className="mt-1 text-sm text-slate-500">
                        Preview inspection reports and print or save them as PDF.
                    </p>
                </div>

                <button
                    type="button"
                    onClick={handlePrint}
                    disabled={!report}
                    className="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    Print / Save as PDF
                </button>
            </div>

            <div className="report-controls rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                Demo report: information is generated from local in-memory
                inspection data. No backend or database verification is performed.
            </div>

            <div className="report-controls rounded-xl border border-slate-200 bg-white p-5">
                <label
                    htmlFor="report-inspection"
                    className="mb-2 block text-sm font-semibold text-slate-700"
                >
                    Select inspection
                </label>

                <select
                    id="report-inspection"
                    value={selectedInspection?.id ?? ''}
                    onChange={event => setSelectedId(event.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 focus:border-blue-500 focus:outline-none sm:max-w-xl"
                >
                    {visibleInspections.map(inspection => (
                        <option key={inspection.id} value={inspection.id}>
                            {inspection.title} — {inspection.id}
                        </option>
                    ))}
                </select>

                <p className="mt-2 text-xs text-slate-500">
                    {visibleInspections.length} inspection
                    {visibleInspections.length === 1 ? '' : 's'} available
                    under your role permissions.
                </p>
            </div>

            {!report ? (
                <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
                    <h2 className="font-semibold text-slate-800">
                        No reports available
                    </h2>
                    <p className="mt-2 text-sm text-slate-500">
                        No inspections are currently available within your access scope.
                    </p>
                </div>
            ) : (
                <article className="report-document space-y-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
                    <header className="border-b border-slate-200 pb-5">
                        <div className="flex flex-wrap items-start justify-between gap-4">
                            <div>
                                <p className="text-xs font-bold uppercase tracking-widest text-blue-600">
                                    SiteSense · Inspection Report
                                </p>
                                <h1 className="mt-2 text-2xl font-bold text-slate-900">
                                    {report.inspection.title}
                                </h1>
                                <p className="mt-1 text-sm text-slate-500">
                                    Report ID: {report.inspection.id}
                                </p>
                            </div>

                            <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700">
                                {completionLabel}
                            </span>
                        </div>

                        {report.inspection.status !== 'Completed' && (
                            <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                                Draft report — this inspection has not been
                                completed and must not be treated as a final report.
                            </p>
                        )}
                    </header>

                    <Section title="Inspection information">
                        <dl className="grid gap-4 sm:grid-cols-2">
                            <div>
                                <dt className="text-xs text-slate-500">Site</dt>
                                <dd className="mt-1 text-sm font-medium text-slate-800">
                                    {report.siteName}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-500">Zone</dt>
                                <dd className="mt-1 text-sm font-medium text-slate-800">
                                    {report.inspection.zone}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-500">Inspection type</dt>
                                <dd className="mt-1 text-sm font-medium text-slate-800">
                                    {report.inspection.type}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-500">Template</dt>
                                <dd className="mt-1 text-sm font-medium text-slate-800">
                                    {report.templateName}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-500">Assigned employee</dt>
                                <dd className="mt-1 text-sm font-medium text-slate-800">
                                    {report.assignedUserName}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-500">Assigned by</dt>
                                <dd className="mt-1 text-sm font-medium text-slate-800">
                                    {report.assignedByUserName}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-500">Created</dt>
                                <dd className="mt-1 text-sm font-medium text-slate-800">
                                    {formatDate(report.inspection.createdAt)}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-500">Due date</dt>
                                <dd className="mt-1 text-sm font-medium text-slate-800">
                                    {formatDate(report.inspection.dueDate)}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-500">Submitted</dt>
                                <dd className="mt-1 text-sm font-medium text-slate-800">
                                    {formatDate(report.inspection.submittedAt)}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-500">Completed</dt>
                                <dd className="mt-1 text-sm font-medium text-slate-800">
                                    {formatDate(report.inspection.completedAt)}
                                </dd>
                            </div>
                        </dl>
                    </Section>

                    <Section title="Checklist summary">
                        <div className="mb-5 grid grid-cols-3 gap-3">
                            <div className="rounded-lg bg-green-50 p-3">
                                <p className="text-xs text-green-700">Passed</p>
                                <p className="mt-1 text-2xl font-bold text-green-800">
                                    {passedCount}
                                </p>
                            </div>
                            <div className="rounded-lg bg-red-50 p-3">
                                <p className="text-xs text-red-700">Failed</p>
                                <p className="mt-1 text-2xl font-bold text-red-800">
                                    {failedCount}
                                </p>
                            </div>
                            <div className="rounded-lg bg-slate-100 p-3">
                                <p className="text-xs text-slate-600">Not applicable</p>
                                <p className="mt-1 text-2xl font-bold text-slate-800">
                                    {notApplicableCount}
                                </p>
                            </div>
                        </div>

                        {report.inspection.answers.length === 0 ? (
                            <p className="text-sm text-slate-500">
                                No checklist answers recorded.
                            </p>
                        ) : (
                            <div className="space-y-3">
                                {report.inspection.answers.map((answer, index) => {
                                    const question = template?.checklist.find(
                                        item => item.id === answer.questionId,
                                    )

                                    return (
                                        <div
                                            key={answer.questionId}
                                            className="rounded-lg border border-slate-200 p-4"
                                        >
                                            <div className="flex flex-wrap justify-between gap-2">
                                                <p className="text-sm font-medium text-slate-800">
                                                    {index + 1}. {question?.question ?? answer.questionId}
                                                </p>
                                                <span className="text-xs font-semibold text-slate-600">
                                                    {answer.result}
                                                </span>
                                            </div>
                                            <p className="mt-2 text-sm text-slate-600">
                                                Comment: {answer.comment?.trim() || 'No comment recorded'}
                                            </p>
                                            <p className="mt-1 text-xs text-slate-400">
                                                Question ID: {answer.questionId}
                                            </p>
                                        </div>
                                    )
                                })}
                            </div>
                        )}
                    </Section>

                    <Section title={`Findings (${report.findings.length})`}>
                        {report.findings.length === 0 ? (
                            <p className="text-sm text-slate-500">No findings recorded.</p>
                        ) : (
                            <div className="space-y-3">
                                {report.findings.map(finding => (
                                    <div key={finding.id} className="rounded-lg border border-slate-200 p-4">
                                        <div className="flex flex-wrap justify-between gap-2">
                                            <h3 className="font-semibold text-slate-800">
                                                {finding.title}
                                            </h3>
                                            <span className="text-xs font-semibold text-slate-600">
                                                {finding.severity} · {finding.status}
                                            </span>
                                        </div>
                                        <p className="mt-2 text-sm text-slate-600">
                                            {finding.description}
                                        </p>
                                        <p className="mt-2 text-xs text-slate-500">
                                            Location: {finding.location} · Finding ID: {finding.id}
                                        </p>
                                        <p className="mt-1 text-sm text-slate-600">
                                            Recommended action: {finding.recommendedAction}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Section>

                    <Section title={`Corrective actions (${report.correctiveActions.length})`}>
                        {report.correctiveActions.length === 0 ? (
                            <p className="text-sm text-slate-500">
                                No corrective actions recorded.
                            </p>
                        ) : (
                            <div className="space-y-3">
                                {report.correctiveActions.map(action => (
                                    <div key={action.id} className="rounded-lg border border-slate-200 p-4">
                                        <div className="flex flex-wrap justify-between gap-2">
                                            <h3 className="font-semibold text-slate-800">
                                                {action.title}
                                            </h3>
                                            <span className="text-xs font-semibold text-slate-600">
                                                {action.status}
                                            </span>
                                        </div>
                                        <p className="mt-2 text-sm text-slate-600">
                                            {action.description}
                                        </p>
                                        <p className="mt-2 text-xs text-slate-500">
                                            Action ID: {action.id} · Finding ID: {action.findingId}
                                        </p>
                                        <p className="mt-1 text-xs text-slate-500">
                                            Due: {formatDate(action.dueDate)}
                                        </p>
                                        {action.completionNotes && (
                                            <p className="mt-2 text-sm text-slate-600">
                                                Completion notes: {action.completionNotes}
                                            </p>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </Section>

                    <Section title={`Evidence (${report.evidence.length})`}>
                        {report.evidence.length === 0 ? (
                            <p className="text-sm text-slate-500">No evidence linked.</p>
                        ) : (
                            <div className="grid gap-4 sm:grid-cols-2">
                                {report.evidence.map(item => (
                                    <div key={item.id} className="break-inside-avoid rounded-lg border border-slate-200 p-3">
                                        {item.previewUrl && item.type === 'Photo' ? (
                                            <img
                                                src={item.previewUrl}
                                                alt={item.caption || item.fileName}
                                                className="mb-3 max-h-64 w-full rounded-lg object-contain"
                                            />
                                        ) : (
                                            <div className="mb-3 flex min-h-24 items-center justify-center rounded-lg bg-slate-50 text-sm text-slate-500">
                                                {item.type === 'Photo'
                                                    ? 'Photo preview unavailable'
                                                    : `${item.type} preview unavailable`}
                                            </div>
                                        )}
                                        <p className="break-all text-sm font-semibold text-slate-800">
                                            {item.fileName}
                                        </p>
                                        <p className="mt-1 text-xs text-slate-500">
                                            {item.type} · {item.fileSizeLabel} · {item.mimeType}
                                        </p>
                                        {item.caption && (
                                            <p className="mt-2 text-sm text-slate-600">
                                                {item.caption}
                                            </p>
                                        )}
                                        <p className="mt-1 text-xs text-slate-400">
                                            Evidence ID: {item.id}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Section>

                    <Section title="Review information">
                        <dl className="grid gap-4 sm:grid-cols-2">
                            <div>
                                <dt className="text-xs text-slate-500">Review status</dt>
                                <dd className="mt-1 text-sm font-medium text-slate-800">
                                    {report.inspection.reviewStatus ?? 'Not recorded'}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-500">Reviewer</dt>
                                <dd className="mt-1 text-sm font-medium text-slate-800">
                                    {report.reviewerName}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-500">Reviewed at</dt>
                                <dd className="mt-1 text-sm font-medium text-slate-800">
                                    {formatDate(report.inspection.reviewedAt)}
                                </dd>
                            </div>
                        </dl>
                        <div className="mt-4">
                            <p className="text-xs text-slate-500">Review notes</p>
                            <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
                                {report.inspection.reviewNotes?.trim() || 'No review notes recorded.'}
                            </p>
                        </div>
                    </Section>

                    <footer className="border-t border-slate-200 pt-4 text-xs text-slate-400">
                        Generated from SiteSense local demo data · Inspection ID: {report.inspection.id}
                    </footer>
                </article>
            )}
        </div>
    )
}