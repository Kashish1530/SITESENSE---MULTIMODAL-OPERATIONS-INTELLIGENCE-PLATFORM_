
import {
    Activity,
    AlertTriangle,
    Building2,
    CheckCircle2,
    Clock3,
} from 'lucide-react'
import {
    getDemoSite,
    type DemoUser,
} from '../../data/users'
import MetricCard from './MetricCard'

type SupervisorDashboardProps = {
    currentUser: DemoUser
    users: DemoUser[]
}

const teamColors = [
    'bg-blue-100 text-blue-700',
    'bg-violet-100 text-violet-700',
    'bg-emerald-100 text-emerald-700',
    'bg-amber-100 text-amber-700',
]

export default function SupervisorDashboard({
    currentUser,
    users,
}: SupervisorDashboardProps) {
    const site = getDemoSite(currentUser.siteId)

    const managers = users.filter(
        (user) =>
            user.role === 'manager' &&
            user.supervisorId === currentUser.id &&
            user.isActive,
    )

    const employees = users.filter(
        (user) =>
            user.role === 'employee' &&
            user.supervisorId === currentUser.id &&
            user.isActive,
    )

    const teamSize = managers.length + employees.length

    // Illustrative site-level demo figures.
    const siteMetrics = [
        {
            title: 'Total Inspections',
            value: '486',
            change: '+10.4%',
            trend: 'up',
            description: 'Compared to last month',
        },
        {
            title: 'Pass Rate',
            value: '95%',
            change: '+2.1%',
            trend: 'up',
            description: 'Site inspection pass rate',
        },
        {
            title: 'Pending Reviews',
            value: '8',
            change: '3 urgent',
            trend: 'warning',
            description: 'Awaiting review',
        },
        {
            title: 'Team Members',
            value: String(teamSize),
            change: `${managers.length} managers`,
            trend: 'neutral',
            description: 'Active assigned team',
        },
    ]

    const siteInspections = [
        {
            id: 'INS-2048',
            type: 'Safety Inspection',
            date: '18 Nov 2026',
            status: 'Passed',
        },
        {
            id: 'INS-2047',
            type: 'Equipment Check',
            date: '18 Nov 2026',
            status: 'Review',
        },
        {
            id: 'INS-2045',
            type: 'Facility Inspection',
            date: '17 Nov 2026',
            status: 'Passed',
        },
        {
            id: 'INS-2044',
            type: 'Storage Compliance',
            date: '16 Nov 2026',
            status: 'Review',
        },
    ]

    const activities = [
        {
            id: 1,
            title: 'Inspection completed',
            detail: 'Safety inspection submitted by the site team',
            time: '12 minutes ago',
            type: 'success',
        },
        {
            id: 2,
            title: 'Review required',
            detail: 'Three findings need supervisor attention',
            time: '35 minutes ago',
            type: 'warning',
        },
        {
            id: 3,
            title: 'Evidence uploaded',
            detail: 'New inspection evidence submitted',
            time: '1 hour ago',
            type: 'info',
        },
    ]

    const statusStyles: Record<string, string> = {
        Passed: 'bg-emerald-50 text-emerald-700',
        Failed: 'bg-red-50 text-red-700',
        Review: 'bg-amber-50 text-amber-700',
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
                        Here's your assigned site's operational overview.
                    </p>
                </div>

                <div className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700">
                    <Building2 size={17} className="text-blue-600" />
                    {site?.name ?? 'Unassigned site'}
                </div>
            </section>

            {/* Demo notice */}
            <div className="flex items-center gap-2 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-800">
                <Activity size={17} className="shrink-0" />
                <span>
                    Demo workspace — operational metrics are illustrative.
                    Team membership is based on your assigned organization data.
                </span>
            </div>

            {/* Metrics */}
            <section>
                <div className="mb-4">
                    <h2 className="text-base font-semibold text-slate-900">
                        Site Performance
                    </h2>
                    <p className="mt-1 text-xs text-slate-400">
                        Overview of your assigned operations
                    </p>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    {siteMetrics.map((metric) => (
                        <MetricCard key={metric.title} {...metric} />
                    ))}
                </div>
            </section>

            {/* Team */}
            <section>
                <div className="mb-4 flex items-center justify-between">
                    <div>
                        <h2 className="text-base font-semibold text-slate-900">
                            Your Management Team
                        </h2>
                        <p className="mt-1 text-xs text-slate-400">
                            Managers and employees assigned to your site
                        </p>
                    </div>
                    <span className="text-xs font-medium text-slate-500">
                        {teamSize} members
                    </span>
                </div>

                <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                    {managers.map((manager, index) => {
                        const directReports = employees.filter(
                            (employee) => employee.managerId === manager.id,
                        )

                        return (
                            <div
                                key={manager.id}
                                className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold ${teamColors[index % teamColors.length]}`}>
                                            {manager.name
                                                .split(' ')
                                                .map((part) => part[0])
                                                .join('')}
                                        </div>
                                        <div>
                                            <h3 className="text-sm font-semibold text-slate-900">
                                                {manager.name}
                                            </h3>
                                            <p className="text-xs text-slate-400">
                                                Manager · {manager.employeeId}
                                            </p>
                                        </div>
                                    </div>
                                    <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">
                                        Active
                                    </span>
                                </div>

                                <div className="mt-4 border-t border-slate-100 pt-3">
                                    <div className="mb-3 flex items-center justify-between">
                                        <span className="text-xs font-medium text-slate-500">
                                            Assigned employees
                                        </span>
                                        <span className="text-sm font-semibold text-slate-800">
                                            {directReports.length}
                                        </span>
                                    </div>

                                    <div className="flex flex-wrap gap-2">
                                        {directReports.length > 0 ? (
                                            directReports.map((employee) => (
                                                <span
                                                    key={employee.id}
                                                    className="rounded-full bg-slate-100 px-3 py-1.5 text-xs text-slate-600"
                                                >
                                                    {employee.name}
                                                </span>
                                            ))
                                        ) : (
                                            <span className="text-xs text-slate-400">
                                                No employees assigned
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )
                    })}
                </div>
            </section>

            {/* Site inspections and activity */}
            <section className="grid grid-cols-1 gap-5 xl:grid-cols-3">
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm xl:col-span-2">
                    <div className="border-b border-slate-100 px-5 py-4">
                        <h2 className="font-semibold text-slate-900">
                            Recent Site Inspections
                        </h2>
                        <p className="mt-1 text-xs text-slate-400">
                            Latest inspection records for your site
                        </p>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[550px] text-left text-sm">
                            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-400">
                                <tr>
                                    <th className="px-5 py-3 font-semibold">Inspection</th>
                                    <th className="px-5 py-3 font-semibold">Date</th>
                                    <th className="px-5 py-3 font-semibold">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {siteInspections.map((inspection) => (
                                    <tr key={inspection.id} className="hover:bg-slate-50">
                                        <td className="px-5 py-4">
                                            <p className="font-medium text-slate-800">
                                                {inspection.type}
                                            </p>
                                            <p className="mt-1 text-xs text-slate-400">
                                                {inspection.id}
                                            </p>
                                        </td>
                                        <td className="px-5 py-4 text-slate-500">
                                            {inspection.date}
                                        </td>
                                        <td className="px-5 py-4">
                                            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusStyles[inspection.status]}`}>
                                                {inspection.status}
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
                            Site Activity
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
