
import { CalendarDays, ClipboardList, MapPin } from 'lucide-react'
import type { DemoUser } from '../../data/users'
import type { InspectionRecord } from '../../inspections/types'
import { getActiveTasks } from '../../inspections/taskUtils'
import TaskPhotoSubmission from './TaskPhotoSubmission'


type Props = {
    currentUser: DemoUser
    inspections: InspectionRecord[]
    onSubmitTaskPhotos: (
        task: InspectionRecord,
        files: File[],
        onProgress: (progress: number) => void,
    ) => Promise<boolean>
}

function formatDueDate(value: string) {
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

export default function MyTasks({
    currentUser,
    inspections,
    onSubmitTaskPhotos,
}: Props) {
    const tasks = getActiveTasks(inspections, currentUser.id)

    return (
        <div className="space-y-6">
            <div>
                <p className="text-sm text-slate-500">Employee Workspace</p>
                <h1 className="mt-1 text-2xl font-bold text-slate-900">
                    My Tasks
                </h1>
                <p className="mt-1 text-sm text-slate-500">
                    Complete your assigned work and submit photo evidence.
                </p>
            </div>

            <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4">
                <div className="rounded-lg bg-blue-50 p-2 text-blue-600">
                    <ClipboardList className="h-5 w-5" />
                </div>
                <div>
                    <p className="text-sm text-slate-500">Active tasks</p>
                    <p className="text-xl font-semibold text-slate-900">
                        {tasks.length}
                    </p>
                </div>
            </div>

            {tasks.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
                    <ClipboardList className="mx-auto h-8 w-8 text-slate-400" />
                    <h2 className="mt-3 font-semibold text-slate-800">
                        No active tasks
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                        You currently have no unfinished tasks assigned to you.
                    </p>
                </div>
            ) : (
                <div className="space-y-4">
                    {tasks.map(task => {
                        const site = { name: task.siteName || task.siteId || 'Site' }

                        return (
                            <article
                                key={task.id}
                                className="rounded-xl border border-slate-200 bg-white p-5"
                            >
                                <div className="flex flex-col justify-between gap-3 sm:flex-row">
                                    <div>
                                        <span className="text-xs font-medium text-blue-700">
                                            {task.type}
                                        </span>
                                        <h2 className="mt-1 font-semibold text-slate-900">
                                            {task.title}
                                        </h2>
                                        <p className="mt-1 text-sm text-slate-600">
                                            {task.description}
                                        </p>
                                    </div>

                                    <span className="h-fit w-fit rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                                        {task.status}
                                    </span>
                                </div>

                                <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-500">
                                    <span className="flex items-center gap-1.5">
                                        <MapPin className="h-4 w-4" />
                                        {site?.name ?? task.siteId} · {task.zone}
                                    </span>
                                    <span className="flex items-center gap-1.5">
                                        <CalendarDays className="h-4 w-4" />
                                        Due {formatDueDate(task.dueDate)}
                                    </span>
                                </div>

                                <TaskPhotoSubmission
                                    onSubmit={(files, onProgress) =>
                                        onSubmitTaskPhotos(task, files, onProgress)
                                    }
                                />
                            </article>
                        )
                    })}
                </div>
            )}
        </div>
    )
}
