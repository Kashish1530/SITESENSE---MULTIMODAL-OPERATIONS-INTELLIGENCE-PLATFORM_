
import {
    Activity,
    AlertTriangle,
    CheckCircle2,
    Clock3,
    ListTodo,
    Users,
} from 'lucide-react'
import { type DemoUser } from '../../data/users'
import MetricCard from './MetricCard'

type ManagerDashboardProps = {
    currentUser: DemoUser
    users: DemoUser[]
}

const employeeColors = [
    'bg-blue-100 text-blue-700',
    'bg-violet-100 text-violet-700',
    'bg-emerald-100 text-emerald-700',
    'bg-amber-100 text-amber-700',
]

export default function ManagerDashboard({
    currentUser,
    users,
}: ManagerDashboardProps) {
    const employees = users.filter(
        (user) =>
            user.role === 'employee' &&
            user.managerId === currentUser.id &&
            user.isActive,
    )

    const metrics = [
        {
            title: 'Team Members',
            value: String(employees.length),
            change: 'Active employees',
            trend: 'neutral',
            description: 'Your assigned team',
        },
        {
            title: 'Assigned Tasks',
            value: '18',
            change: '+3 new',
            trend: 'up',
            description: 'Illustrative demo workload',
        },
        {
            title: 'Pending Reviews',
            value: '5',
            change: '2 urgent',
            trend: 'warning',
            description: 'Awaiting your attention',
        },
        {
            title: 'Completed Inspections',
            value: '42',
            change: '+8.5%',
            trend: 'up',
            description: 'Compared to last month',
        },
    ]

    const tasks = [
        {
            id: 'TSK-104',
            title: 'Complete equipment safety check',
            assignee: employees[0]?.name ?? 'Unassigned',
            due: 'Today',
            status: 'In Progress',
        },
        {
            id: 'TSK-105',
            title: 'Upload storage area evidence',
            assignee: employees[1]?.name ?? 'Unassigned',
            due: 'Tomorrow',
            status: 'Pending',
        },
        {
            id: 'TSK-106',
            title: 'Review fire exit inspection',
            assignee: employees[2]?.name ?? employees[0]?.name ?? 'Unassigned',
            due: 'Today',
            status: 'Review',
        },
    ]

    const activities = [
        {
            id: 1,
            title: 'Inspection submitted',
            detail: 'A team member submitted an inspection',
            time: '15 minutes ago',
            type: 'success',
        },
        {
            id: 2,
            title: 'Task needs attention',
            detail: 'An assigned task is awaiting review',
            time: '40 minutes ago',
            type: 'warning',
        },
        {
            id: 3,
            title: 'Evidence uploaded',
            detail: 'New supporting files were added',
            time: '1 hour ago',
            type: 'info',
        },
    ]

    const taskStyles: Record<string, string> = {
        'In Progress': 'bg-blue-50 text-blue-700',
        Pending: 'bg-amber-50 text-amber-700',
        Review: 'bg-violet-50 text-violet-700',
    }

    const activityIcons = {
        success: CheckCircle2,
        warning: AlertTriangle,
        info: Activity,
    }

    return (
        <div className="space-y-7">
            {/* Welcome */}
            <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                <div>
                    <p className="text-sm font-medium text-blue-600">
                        Wednesday, 18 November 2026
                    </p>
                    <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
                        Welcome back, {currentUser.name.split(' ')[0]} 👋
                    </h1>
                    <p className="mt-2 text-sm text-slate-500">
                        Here's what's happening with your team today.
                    </p>
                </div>

                <div className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700">
                    <Users size={17} className="text-blue-600" />
                    {employees.length} assigned employees
                </div>
            </section>

            {/* Demo notice */}
            <div className="flex items-center gap-2 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-800">
                <Activity size={17} className="shrink-0" />
                <span>
                    Demo workspace — task, inspection and activity figures
                    are illustrative. Team membership uses assigned account data.
                </span>
            </div>

            {/* Metrics */}
            <section>
                <div className="mb-4">
                    <h2 className="text-base font-semibold text-slate-900">
                        Team Overview
                    </h2>
                    <p className="mt-1 text-xs text-slate-400">
                        Your team's current workload and performance
                    </p>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    {metrics.map((metric) => (
                        <MetricCard key={metric.title} {...metric} />
                    ))}
                </div>
            </section>

            {/* Employees */}
            <section>
                <div className="mb-4 flex items-center justify-between">
                    <div>
                        <h2 className="text-base font-semibold text-slate-900">
                            My Employees
                        </h2>
                        <p className="mt-1 text-xs text-slate-400">
                            Employees directly assigned to you
                        </p>
                    </div>
                    <span className="text-xs font-medium text-slate-500">
                        {employees.length} members
                    </span>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    {employees.map((employee, index) => (
                        <div
                            key={employee.id}
                            className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                        >
                            <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-sm font-bold ${employeeColors[index % employeeColors.length]}`}>
                                {employee.name
                                    .split(' ')
                                    .map((part) => part[0])
                                    .join('')}
                            </div>

                            <div className="min-w-0 flex-1">
                                <h3 className="truncate text-sm font-semibold text-slate-800">
                                    {employee.name}
                                </h3>
                                <p className="mt-1 text-xs text-slate-400">
                                    {employee.employeeId}
                                </p>
                                <span className="mt-2 inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                                    Active
                                </span>
                            </div>
                        </div>
                    ))}

                    {employees.length === 0 && (
                        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500 sm:col-span-2 xl:col-span-3">
                            No active employees are currently assigned to you.
                        </div>
                    )}
                </div>
            </section>

            {/* Tasks and activity */}
            <section className="grid grid-cols-1 gap-5 xl:grid-cols-3">
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm xl:col-span-2">
                    <div className="flex items-center gap-2 border-b border-slate-100 px-5 py-4">
                        <ListTodo size={18} className="text-blue-600" />
                        <div>
                            <h2 className="font-semibold text-slate-900">
                                Team Tasks
                            </h2>
                            <p className="mt-1 text-xs text-slate-400">
                                Illustrative assigned task list
                            </p>
                        </div>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[570px] text-left text-sm">
                            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-400">
                                <tr>
                                    <th className="px-5 py-3 font-semibold">Task</th>
                                    <th className="px-5 py-3 font-semibold">Assignee</th>
                                    <th className="px-5 py-3 font-semibold">Due</th>
                                    <th className="px-5 py-3 font-semibold">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {tasks.map((task) => (
                                    <tr key={task.id} className="hover:bg-slate-50">
                                        <td className="px-5 py-4">
                                            <p className="font-medium text-slate-800">
                                                {task.title}
                                            </p>
                                            <p className="mt-1 text-xs text-slate-400">
                                                {task.id}
                                            </p>
                                        </td>
                                        <td className="px-5 py-4 text-slate-500">
                                            {task.assignee}
                                        </td>
                                        <td className="px-5 py-4 text-slate-500">
                                            {task.due}
                                        </td>
                                        <td className="px-5 py-4">
                                            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${taskStyles[task.status]}`}>
                                                {task.status}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Activity */}
                <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
                    <div className="border-b border-slate-100 px-5 py-4">
                        <h2 className="font-semibold text-slate-900">
                            Team Activity
                        </h2>
                        <p className="mt-1 text-xs text-slate-400">
                            Recent team updates
                        </p>
                    </div>

                    <div className="divide-y divide-slate-100 px-5">
                        {activities.map((activity) => {
                            const Icon =
                                activityIcons[
                                activity.type as keyof typeof activityIcons
                                ]

                            const iconStyle =
                                activity.type === 'success'
                                    ? 'bg-emerald-50 text-emerald-600'
                                    : activity.type === 'warning'
                                        ? 'bg-amber-50 text-amber-600'
                                        : 'bg-blue-50 text-blue-600'

                            return (
                                <div key={activity.id} className="flex gap-3 py-4">
                                    <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${iconStyle}`}>
                                        <Icon size={17} />
                                    </div>
                                    <div className="min-w-0">
                                        <p className="text-sm font-medium text-slate-800">
                                            {activity.title}
                                        </p>
                                        <p className="mt-1 text-xs leading-5 text-slate-500">
                                            {activity.detail}
                                        </p>
                                        <p className="mt-2 flex items-center gap-1 text-[11px] text-slate-400">
                                            <Clock3 size={11} />
                                            {activity.time}
                                        </p>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            </section>
        </div>
    )
}
