
import {
    CalendarDays,
    CheckCircle2,
    Clock3,
    ClipboardList,
    FileUp,
    ListTodo,
    MapPin,
} from 'lucide-react'
import type { DemoUser } from '../../data/users'
import type { InspectionRecord } from '../../inspections/types'
import { getActiveTasks, getCompletedTasks, getEmployeeTasks } from '../../inspections/taskUtils'

type Props = {
    currentUser: DemoUser
    inspections: InspectionRecord[]
    onNavigate: (page: string) => void
}

function formatDueDate(value: string) {
    const date = new Date(value)

    if (Number.isNaN(date.getTime())) return 'Date not available'

    return date.toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
    })
}

export default function EmployeeDashboard({
    currentUser,
    inspections,
    onNavigate,
}: Props) {
    const assignedTasks = getEmployeeTasks(inspections, currentUser.id)
    const activeTasks = getActiveTasks(inspections, currentUser.id)
    const completedTasks = getCompletedTasks(inspections, currentUser.id)
    const firstName = currentUser.name.split(' ')[0]

    return (
        <div className="space-y-6">
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                <div>
                    <p className="text-sm text-slate-500">Employee Workspace</p>
                    <h1 className="mt-1 text-2xl font-bold text-slate-900">
                        Welcome back, {firstName}
                    </h1>
                    <p className="mt-1 text-sm text-slate-500">
                        Here is your current task workload.
                    </p>
                </div>

                <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3">
                    <p className="text-xs font-medium text-blue-600">
                        EMPLOYEE ID
                    </p>
                    <p className="mt-1 font-semibold text-blue-900">
                        {currentUser.employeeId}
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <Metric
                    icon={<ListTodo className="h-5 w-5" />}
                    label="Assigned Tasks"
                    value={assignedTasks.length}
                    color="blue"
                />
                <Metric
                    icon={<Clock3 className="h-5 w-5" />}
                    label="Active Tasks"
                    value={activeTasks.length}
                    color="amber"
                />
                <Metric
                    icon={<CheckCircle2 className="h-5 w-5" />}
                    label="Completed"
                    value={completedTasks.length}
                    color="green"
                />
            </div>

            <section className="rounded-2xl border border-slate-200 bg-white">
                <div className="flex items-center justify-between border-b border-slate-100 p-5">
                    <div>
                        <h2 className="font-semibold text-slate-900">
                            Your Active Tasks
                        </h2>
                        <p className="mt-1 text-sm text-slate-500">
                            Your assigned work that still needs completion.
                        </p>
                    </div>
                    <ClipboardList className="h-5 w-5 text-slate-400" />
                </div>

                {activeTasks.length === 0 ? (
                    <p className="p-6 text-sm text-slate-500">
                        You have no active tasks right now.
                    </p>
                ) : (
                    <div className="divide-y divide-slate-100">
                        {activeTasks.slice(0, 4).map(task => {
                            const site = { name: task.siteName || task.siteId || 'Site' }

                            return (
                                <div key={task.id} className="p-5">
                                    <div className="flex flex-col justify-between gap-2 sm:flex-row">
                                        <div>
                                            <h3 className="text-sm font-semibold text-slate-800">
                                                {task.title}
                                            </h3>
                                            <p className="mt-1 text-sm text-slate-500">
                                                {task.description}
                                            </p>
                                        </div>
                                        <span className="h-fit w-fit rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700">
                                            {task.status}
                                        </span>
                                    </div>

                                    <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
                                        <span className="flex items-center gap-1">
                                            <MapPin className="h-3.5 w-3.5" />
                                            {site?.name ?? task.siteId} · {task.zone}
                                        </span>
                                        <span className="flex items-center gap-1">
                                            <CalendarDays className="h-3.5 w-3.5" />
                                            Due {formatDueDate(task.dueDate)}
                                        </span>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                )}

                <div className="border-t border-slate-100 p-4">
                    <button
                        type="button"
                        onClick={() => onNavigate('My Tasks')}
                        className="text-sm font-semibold text-blue-700 hover:text-blue-800"
                    >
                        View all my tasks →
                    </button>
                </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5">
                <h2 className="font-semibold text-slate-900">Quick Actions</h2>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <QuickAction
                        icon={<ClipboardList className="h-5 w-5" />}
                        label="My Tasks"
                        onClick={() => onNavigate('My Tasks')}
                    />
                    <QuickAction
                        icon={<FileUp className="h-5 w-5" />}
                        label="Upload Task Photos"
                        onClick={() => onNavigate('Upload')}
                    />
                </div>
            </section>
        </div>
    )
}

type MetricProps = {
    icon: React.ReactNode
    label: string
    value: number
    color: 'blue' | 'amber' | 'green'
}

function Metric({ icon, label, value, color }: MetricProps) {
    const colors = {
        blue: 'bg-blue-50 text-blue-600',
        amber: 'bg-amber-50 text-amber-600',
        green: 'bg-green-50 text-green-600',
    }

    return (
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-500">
                    {label}
                </span>
                <div className={`rounded-xl p-2.5 ${colors[color]}`}>
                    {icon}
                </div>
            </div>
            <p className="mt-4 text-2xl font-bold text-slate-900">{value}</p>
        </div>
    )
}

type QuickActionProps = {
    icon: React.ReactNode
    label: string
    onClick: () => void
}

function QuickAction({ icon, label, onClick }: QuickActionProps) {
    return (
        <button
            type="button"
            onClick={onClick}
            className="flex items-center gap-3 rounded-xl border border-slate-200 p-3 text-left transition-colors hover:bg-slate-50"
        >
            <span className="rounded-lg bg-blue-50 p-2 text-blue-600">
                {icon}
            </span>
            <span className="text-sm font-semibold text-slate-800">
                {label}
            </span>
        </button>
    )
}
