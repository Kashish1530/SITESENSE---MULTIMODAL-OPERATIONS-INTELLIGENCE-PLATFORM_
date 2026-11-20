
import { ClipboardList, MapPin } from 'lucide-react'
import type { DemoUser } from '../../data/users'
import { sitePerformance } from '../../data/mockData'
import type {
    InspectionEvidence,
    InspectionRecord,
} from '../../inspections/types'
import { getActiveTasks } from '../../inspections/taskUtils'
import TaskPhotoSubmission from './TaskPhotoSubmission'

type Props = {
    currentUser: DemoUser
    inspections: InspectionRecord[]
    evidence: InspectionEvidence[]
    onSubmitTaskPhotos: (
        task: InspectionRecord,
        files: File[],
        onProgress: (progress: number) => void,
    ) => Promise<boolean>
}

export default function TaskUpload({
    currentUser,
    inspections,
    evidence,
    onSubmitTaskPhotos,
}: Props) {
    const activeTasks = getActiveTasks(inspections, currentUser.id)

    const eligibleTasks = activeTasks.filter(task => {
        const hasPhotoEvidence = evidence.some(
            item =>
                item.inspectionId === task.id &&
                item.type === 'Photo',
        )

        return !hasPhotoEvidence
    })

    return (
        <div className="space-y-6">
            <div>
                <p className="text-sm text-slate-500">Employee Workspace</p>
                <h1 className="mt-1 text-2xl font-bold text-slate-900">
                    Upload Task Photos
                </h1>
                <p className="mt-1 text-sm text-slate-500">
                    Choose the task these photos belong to, then capture or select your evidence.
                </p>
            </div>

            {eligibleTasks.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
                    <ClipboardList className="mx-auto h-8 w-8 text-slate-400" />
                    <h2 className="mt-3 font-semibold text-slate-800">
                        No tasks need photo evidence
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                        You have no active assigned tasks awaiting photo submission.
                    </p>
                </div>
            ) : (
                <div className="space-y-4">
                    {eligibleTasks.map(task => {
                        const site = sitePerformance.find(
                            item => item.id === task.siteId,
                        )

                        return (
                            <article
                                key={task.id}
                                className="rounded-xl border border-slate-200 bg-white p-5"
                            >
                                <div className="flex flex-col justify-between gap-2 sm:flex-row">
                                    <div>
                                        <p className="text-xs font-medium text-blue-700">
                                            {task.type}
                                        </p>
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

                                <div className="mt-3 flex items-center gap-2 text-sm text-slate-500">
                                    <MapPin className="h-4 w-4 shrink-0" />
                                    <span>
                                        {site?.name ?? task.siteId} · {task.zone}
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

            <p className="text-xs text-slate-400">
                Demo mode: submitted photos are held in the current app session only.
            </p>
        </div>
    )
}
