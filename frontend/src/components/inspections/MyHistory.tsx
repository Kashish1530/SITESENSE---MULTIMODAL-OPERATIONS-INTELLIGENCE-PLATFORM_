
import { CalendarCheck, ClipboardList, MapPin } from 'lucide-react'
import type { DemoUser } from '../../data/users'
import type {
    InspectionEvidence,
    InspectionRecord,
} from '../../inspections/types'
import { getCompletedTasks } from '../../inspections/taskUtils'

type Props = {
    currentUser: DemoUser
    inspections: InspectionRecord[]
    evidence: InspectionEvidence[]
}

function formatDate(value?: string) {
    if (!value) return 'Date not available'

    const date = new Date(value)

    if (Number.isNaN(date.getTime())) return 'Date not available'

    return date.toLocaleString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
    })
}

export default function MyHistory({
    currentUser,
    inspections,
    evidence,
}: Props) {
    const completedTasks = getCompletedTasks(
        inspections,
        currentUser.id,
    )

    return (
        <div className="space-y-6">
            <div>
                <p className="text-sm text-slate-500">Employee Workspace</p>
                <h1 className="mt-1 text-2xl font-bold text-slate-900">
                    My History
                </h1>
                <p className="mt-1 text-sm text-slate-500">
                    Your completed tasks and submitted photo evidence.
                </p>
            </div>

            <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4">
                <div className="rounded-lg bg-green-50 p-2 text-green-600">
                    <CalendarCheck className="h-5 w-5" />
                </div>
                <div>
                    <p className="text-sm text-slate-500">Completed tasks</p>
                    <p className="text-xl font-semibold text-slate-900">
                        {completedTasks.length}
                    </p>
                </div>
            </div>

            {completedTasks.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
                    <ClipboardList className="mx-auto h-8 w-8 text-slate-400" />
                    <h2 className="mt-3 font-semibold text-slate-800">
                        No completed tasks yet
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                        Tasks you complete will appear here with their submitted photos.
                    </p>
                </div>
            ) : (
                <div className="space-y-4">
                    {completedTasks.map(task => {
                        const site = { name: task.siteName || task.siteId || 'Site' }

                        const taskEvidence = evidence.filter(
                            item =>
                                item.inspectionId === task.id &&
                                item.type === 'Photo',
                        )

                        return (
                            <article
                                key={task.id}
                                className="rounded-xl border border-slate-200 bg-white p-5"
                            >
                                <div className="flex flex-col justify-between gap-2 sm:flex-row">
                                    <div>
                                        <p className="text-xs font-medium text-green-700">
                                            {task.type}
                                        </p>
                                        <h2 className="mt-1 font-semibold text-slate-900">
                                            {task.title}
                                        </h2>
                                        <p className="mt-1 text-sm text-slate-600">
                                            {task.description}
                                        </p>
                                    </div>
                                    <span className="h-fit w-fit rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-700">
                                        Completed
                                    </span>
                                </div>

                                <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-500">
                                    <span className="flex items-center gap-1.5">
                                        <MapPin className="h-4 w-4" />
                                        {site?.name ?? task.siteId} · {task.zone}
                                    </span>
                                    <span className="flex items-center gap-1.5">
                                        <CalendarCheck className="h-4 w-4" />
                                        Completed {formatDate(task.completedAt)}
                                    </span>
                                </div>

                                <div className="mt-4 border-t border-slate-100 pt-4">
                                    <h3 className="text-sm font-semibold text-slate-800">
                                        Submitted photo evidence ({taskEvidence.length})
                                    </h3>

                                    {taskEvidence.length === 0 ? (
                                        <p className="mt-2 text-sm text-slate-500">
                                            No task photo previews are available for this record.
                                        </p>
                                    ) : (
                                        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
                                            {taskEvidence.map(item => (
                                                <div
                                                    key={item.id}
                                                    className="overflow-hidden rounded-lg border border-slate-200"
                                                >
                                                    {item.previewUrl ? (
                                                        <img
                                                            src={item.previewUrl}
                                                            alt={`Submitted evidence: ${item.fileName}`}
                                                            className="h-32 w-full object-cover"
                                                        />
                                                    ) : (
                                                        <div className="flex h-32 items-center justify-center bg-slate-50 text-xs text-slate-400">
                                                            Preview unavailable
                                                        </div>
                                                    )}
                                                    <div className="p-2">
                                                        <p className="truncate text-xs font-medium text-slate-700">
                                                            {item.fileName}
                                                        </p>
                                                        <p className="text-xs text-slate-500">
                                                            {item.fileSizeLabel}
                                                        </p>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </article>
                        )
                    })}
                </div>
            )}

            <p className="text-xs text-slate-400">
                Demo history is stored in app memory and resets when the app is reloaded.
            </p>
        </div>
    )
}
