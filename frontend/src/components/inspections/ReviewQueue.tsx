
import { useMemo, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import { DEMO_SITES, type DemoUser } from '../../data/users'
import type {
    CorrectiveAction,
    InspectionEvidence,
    InspectionFinding,
    InspectionRecord,
} from '../../inspections/types'
import {
    approveInspection,
    getReviewQueue,
    getReviewStatus,
    requestInspectionChanges,
    startInspectionReview,
} from '../../inspections/reviewUtils'
import InspectionDetail from './InspectionDetail'

type Props = {
    currentUser: DemoUser
    users: DemoUser[]
    inspections: InspectionRecord[]
    setInspections: Dispatch<SetStateAction<InspectionRecord[]>>
    evidence: InspectionEvidence[]
    findings: InspectionFinding[]
    correctiveActions: CorrectiveAction[]
}

type QueueFilter = 'All' | 'Pending' | 'Under Review'

function formatDate(value?: string) {
    if (!value) return 'Date unavailable'

    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return 'Date unavailable'

    return date.toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
    })
}

function getPriority(dueDate: string): 'Overdue' | 'Normal' {
    const due = new Date(dueDate)
    if (Number.isNaN(due.getTime())) return 'Normal'

    const today = new Date()
    today.setHours(0, 0, 0, 0)
    due.setHours(0, 0, 0, 0)

    return due < today ? 'Overdue' : 'Normal'
}

function ReviewQueue({
    currentUser,
    users,
    inspections,
    setInspections,
    evidence,
    findings,
    correctiveActions,
}: Props) {
    const [filter, setFilter] = useState<QueueFilter>('All')
    const [selectedId, setSelectedId] = useState<string | null>(null)
    const [notes, setNotes] = useState('')
    const [error, setError] = useState('')
    const [notice, setNotice] = useState('')

    const queue = useMemo(
        () => getReviewQueue(inspections, currentUser),
        [inspections, currentUser],
    )

    const visibleQueue = queue.filter(inspection => {
        if (filter === 'All') return true
        return getReviewStatus(inspection) === filter
    })

    const selectedInspection = selectedId
        ? inspections.find(item => item.id === selectedId)
        : undefined

    const selectedReviewStatus = selectedInspection
        ? getReviewStatus(selectedInspection)
        : undefined

    function openInspection(inspection: InspectionRecord) {
        setInspections(previous =>
            previous.map(item =>
                item.id === inspection.id
                    ? startInspectionReview(item, currentUser.id)
                    : item,
            ),
        )

        setSelectedId(inspection.id)
        setNotes('')
        setError('')
        setNotice('')
    }

    function handleApprove() {
        if (!selectedInspection) return

        setInspections(previous =>
            previous.map(item =>
                item.id === selectedInspection.id
                    ? approveInspection(item, currentUser.id, notes)
                    : item,
            ),
        )

        setNotice('Inspection approved successfully.')
        setNotes('')
        setError('')
    }

    function handleRequestChanges() {
        if (!selectedInspection) return

        if (!notes.trim()) {
            setError('Please provide review notes before requesting changes.')
            return
        }

        setInspections(previous =>
            previous.map(item =>
                item.id === selectedInspection.id
                    ? requestInspectionChanges(
                        item,
                        currentUser.id,
                        notes,
                    )
                    : item,
            ),
        )

        setNotice('Changes requested. The inspection has returned to the employee.')
        setNotes('')
        setError('')
    }

    function handleBack() {
        setSelectedId(null)
        setNotes('')
        setError('')
        setNotice('')
    }

    if (selectedInspection) {
        const canReview =
            selectedReviewStatus === 'Pending' ||
            selectedReviewStatus === 'Under Review'

        return (
            <div className="space-y-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                            Human review
                        </p>
                        <h1 className="mt-1 text-2xl font-bold text-slate-900">
                            Review inspection
                        </h1>
                    </div>
                    <span className="rounded-full bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800">
                        Mock review workflow
                    </span>
                </div>

                <InspectionDetail
                    inspection={selectedInspection}
                    users={users}
                    evidence={evidence}
                    findings={findings}
                    correctiveActions={correctiveActions}
                    onBack={handleBack}
                />

                {notice && (
                    <div
                        role="status"
                        className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800"
                    >
                        {notice}
                    </div>
                )}

                {canReview ? (
                    <section className="rounded-xl border border-slate-200 bg-white p-5">
                        <h2 className="font-semibold text-slate-900">
                            Review decision
                        </h2>
                        <p className="mt-1 text-sm text-slate-500">
                            Approve this inspection or request corrections from the employee.
                        </p>

                        <label
                            htmlFor="review-notes"
                            className="mt-4 block text-sm font-medium text-slate-700"
                        >
                            Review notes
                        </label>
                        <textarea
                            id="review-notes"
                            value={notes}
                            onChange={event => {
                                setNotes(event.target.value)
                                setError('')
                            }}
                            rows={4}
                            placeholder="Add feedback or explain what needs correction..."
                            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                        />

                        {error && (
                            <p role="alert" className="mt-2 text-sm text-red-600">
                                {error}
                            </p>
                        )}

                        <div className="mt-4 flex flex-wrap gap-3">
                            <button
                                type="button"
                                onClick={handleApprove}
                                className="rounded-lg bg-green-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-green-700"
                            >
                                Approve inspection
                            </button>
                            <button
                                type="button"
                                onClick={handleRequestChanges}
                                className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-2.5 text-sm font-semibold text-amber-800 hover:bg-amber-100"
                            >
                                Request changes
                            </button>
                        </div>
                    </section>
                ) : (
                    <section className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                        <p className="text-sm font-medium text-slate-700">
                            Review decision: {selectedReviewStatus ?? 'Unavailable'}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                            This inspection is no longer awaiting a review decision.
                        </p>
                    </section>
                )}
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                        Operations
                    </p>
                    <h1 className="mt-1 text-2xl font-bold text-slate-900">
                        Human Review Queue
                    </h1>
                    <p className="mt-1 text-sm text-slate-500">
                        Review submitted inspections and provide employee feedback.
                    </p>
                </div>

                <span className="w-fit rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800">
                    Demo mode · Changes are temporary
                </span>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                    <p className="text-sm text-slate-500">Awaiting review</p>
                    <p className="mt-1 text-2xl font-bold text-slate-900">
                        {queue.filter(item => getReviewStatus(item) === 'Pending').length}
                    </p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                    <p className="text-sm text-slate-500">Under review</p>
                    <p className="mt-1 text-2xl font-bold text-slate-900">
                        {queue.filter(item => getReviewStatus(item) === 'Under Review').length}
                    </p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                    <p className="text-sm text-slate-500">Total in queue</p>
                    <p className="mt-1 text-2xl font-bold text-slate-900">
                        {queue.length}
                    </p>
                </div>
            </div>

            <div className="flex flex-wrap gap-2">
                {(['All', 'Pending', 'Under Review'] as QueueFilter[]).map(item => (
                    <button
                        key={item}
                        type="button"
                        onClick={() => setFilter(item)}
                        aria-pressed={filter === item}
                        className={`rounded-lg px-4 py-2 text-sm font-medium transition ${filter === item
                                ? 'bg-slate-900 text-white'
                                : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                            }`}
                    >
                        {item}
                    </button>
                ))}
            </div>

            {visibleQueue.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
                    <h2 className="font-semibold text-slate-800">
                        No inspections to review
                    </h2>
                    <p className="mt-2 text-sm text-slate-500">
                        There are no inspections matching this filter.
                    </p>
                </div>
            ) : (
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                    <div className="divide-y divide-slate-100">
                        {visibleQueue.map(inspection => {
                            const employee = users.find(
                                user => user.id === inspection.assignedToUserId,
                            )
                            const site = DEMO_SITES.find(
                                item => item.id === inspection.siteId,
                            )
                            const priority = getPriority(inspection.dueDate)
                            const status = getReviewStatus(inspection)

                            return (
                                <article
                                    key={inspection.id}
                                    className="flex flex-col justify-between gap-4 p-5 sm:flex-row sm:items-center"
                                >
                                    <div className="min-w-0">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <h2 className="font-semibold text-slate-900">
                                                {inspection.title}
                                            </h2>
                                            <span className="text-xs text-slate-400">
                                                {inspection.id}
                                            </span>
                                        </div>

                                        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
                                            <span>{site?.name ?? 'Unknown site'}</span>
                                            <span>{employee?.name ?? 'Unknown employee'}</span>
                                            <span>
                                                Submitted: {formatDate(inspection.submittedAt ?? inspection.createdAt)}
                                            </span>
                                        </div>

                                        <div className="mt-3 flex flex-wrap items-center gap-2">
                                            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${status === 'Pending'
                                                    ? 'bg-amber-100 text-amber-800'
                                                    : 'bg-blue-100 text-blue-800'
                                                }`}>
                                                {status}
                                            </span>

                                            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${priority === 'Overdue'
                                                    ? 'bg-red-100 text-red-700'
                                                    : 'bg-slate-100 text-slate-600'
                                                }`}>
                                                {priority}
                                            </span>

                                            <span className="text-xs text-slate-400">
                                                Due {formatDate(inspection.dueDate)}
                                            </span>
                                        </div>
                                    </div>

                                    <button
                                        type="button"
                                        onClick={() => openInspection(inspection)}
                                        className="shrink-0 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
                                    >
                                        Review inspection
                                    </button>
                                </article>
                            )
                        })}
                    </div>
                </div>
            )}
        </div>
    )
}

export default ReviewQueue
