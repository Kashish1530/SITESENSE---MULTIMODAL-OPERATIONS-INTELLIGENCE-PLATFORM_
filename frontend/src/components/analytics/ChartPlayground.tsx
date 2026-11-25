
import { useMemo } from 'react'
import {
    calculateInspectionMetrics,
    calculateWeeklyInspectionTrend,
    calculateSitePerformance,
} from '../../analytics/calculations'
import type { AnalyticsInspection, InspectionStatus } from '../../analytics/types'
import type { DemoUser } from '../../data/users'
import LineChart from './LineChart'
import BarChart from './BarChart'
import DonutChart from './DonutChart'

type ChartPlaygroundProps = {
    currentUser: DemoUser
    users: DemoUser[]
}

type PlaygroundInspection = AnalyticsInspection & {
    assignedToUserId: string
}

const STATUSES: InspectionStatus[] = [
    'Completed',
    'Completed',
    'In Progress',
    'Scheduled',
    'Under Review',
    'Submitted',
]

function createMockInspections(
    employees: DemoUser[],
): PlaygroundInspection[] {
    const now = new Date()

    return employees.flatMap((employee, employeeIndex) =>
        Array.from({ length: 6 }, (_, index) => {
            const createdAt = new Date(now)
            createdAt.setDate(
                createdAt.getDate() -
                (8 + employeeIndex * 2 + index * 4),
            )

            const status =
                STATUSES[(employeeIndex + index) % STATUSES.length]

            const completedAt = new Date(createdAt)
            completedAt.setHours(
                completedAt.getHours() + 2 + index,
            )

            const dueDate = new Date(createdAt)
            dueDate.setDate(dueDate.getDate() + 3)

            return {
                id: `DEMO-INS-${employee.id}-${index}`,
                siteId: employee.siteId ?? '',
                assignedToUserId: employee.id,
                status,
                result: status === 'Completed'
                    ? (index % 3 === 0 ? 'Failed' : 'Passed')
                    : undefined,
                createdAt: createdAt.toISOString(),
                completedAt: status === 'Completed'
                    ? completedAt.toISOString()
                    : null,
                dueDate: dueDate.toISOString(),
                durationMinutes: status === 'Completed'
                    ? 90 + index * 15
                    : null,
            }
        }),
    )
}

export default function ChartPlayground({
    currentUser,
    users,
}: ChartPlaygroundProps) {
    const allEmployees = users.filter(
        user => user.role === 'employee' && user.isActive,
    )

    const allInspections = useMemo(
        () => createMockInspections(allEmployees),
        [allEmployees],
    )

    const visibleInspections = useMemo(() => {
        if (currentUser.role === 'admin') {
            return allInspections
        }

        if (currentUser.role === 'supervisor') {
            return allInspections.filter(
                item => item.siteId === currentUser.siteId,
            )
        }

        if (currentUser.role === 'manager') {
            return allInspections.filter(
                item => item.assignedToUserId &&
                    users.some(
                        user =>
                            user.id === item.assignedToUserId &&
                            user.managerId === currentUser.id,
                    ),
            )
        }

        return allInspections.filter(
            item => item.assignedToUserId === currentUser.id,
        )
    }, [allInspections, currentUser, users])

    const metrics = calculateInspectionMetrics(visibleInspections)

    const trend = calculateWeeklyInspectionTrend(
        visibleInspections,
        8,
    )

    const sitePerformance = calculateSitePerformance(
        visibleInspections,
    )

    const statusOrder: InspectionStatus[] = [
        'Scheduled',
        'In Progress',
        'Submitted',
        'Under Review',
        'Completed',
    ]

    const statusData = statusOrder.map((status, index) => ({
        label: status,
        value: visibleInspections.filter(
            item => item.status === status,
        ).length,
        color: [
            '#94a3b8',
            '#3b82f6',
            '#f59e0b',
            '#8b5cf6',
            '#16a34a',
        ][index],
    }))


    const completedByPerson = currentUser.role === 'admin'
        ? sitePerformance.map(site => ({
            id: site.siteId,
            label: users.find(user => user.siteId === site.siteId)?.name
                ?? site.siteId,
            value: site.completed,
        }))
        : currentUser.role === 'supervisor'
            ? users
                .filter(
                    user =>
                        user.role === 'manager' &&
                        user.supervisorId === currentUser.id,
                )
                .map(manager => ({
                    id: manager.id,
                    label: manager.name,
                    value: visibleInspections.filter(
                        item =>
                            users.find(
                                user => user.id === item.assignedToUserId,
                            )?.managerId === manager.id &&
                            item.status === 'Completed',
                    ).length,
                }))
            : currentUser.role === 'manager'
                ? users
                    .filter(
                        user =>
                            user.role === 'employee' &&
                            user.managerId === currentUser.id,
                    )
                    .map(employee => ({
                        id: employee.id,
                        label: employee.name,
                        value: visibleInspections.filter(
                            item =>
                                item.assignedToUserId === employee.id &&
                                item.status === 'Completed',
                        ).length,
                    }))
                : [
                    {
                        id: 'completed',
                        label: 'Completed inspections',
                        value: metrics.completed,
                    },
                    {
                        id: 'remaining',
                        label: 'Remaining inspections',
                        value: metrics.total - metrics.completed,
                    },
                ]

    const heading = currentUser.role === 'admin'
        ? 'Organisation Analytics'
        : currentUser.role === 'supervisor'
            ? 'Site Analytics'
            : currentUser.role === 'manager'
                ? 'Team Analytics'
                : 'My Inspection Progress'

    const description = currentUser.role === 'admin'
        ? 'Performance across all organisational sites'
        : currentUser.role === 'supervisor'
            ? 'Performance for your assigned site only'
            : currentUser.role === 'manager'
                ? 'Performance for your assigned team only'
                : 'Your personal inspection activity'

    const cards = [
        { label: 'Total Inspections', value: metrics.total },
        { label: 'Completed', value: metrics.completed },
        { label: 'Completion Rate', value: `${metrics.completionRate}%` },
        { label: 'Pending Review', value: metrics.pendingReview },
        { label: 'Overdue', value: metrics.overdue },
    ]

    return (
        <div className="space-y-6">
            <div>
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">
                            {heading}
                        </h1>
                        <p className="mt-1 text-sm text-slate-500">
                            {description}
                        </p>
                    </div>

                    <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
                        Demo analytics
                    </span>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
                {cards.map(card => (
                    <div
                        key={card.label}
                        className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
                    >
                        <p className="text-sm text-slate-500">
                            {card.label}
                        </p>
                        <p className="mt-2 text-2xl font-bold text-slate-900">
                            {card.value}
                        </p>
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                <LineChart
                    title="Inspection Completion Trend"
                    description="Inspections created and completed each week"
                    data={trend.map(item => ({
                        id: item.startDate,
                        label: item.week,
                        created: item.created,
                        completed: item.completed,
                    }))}

                    series={[
                        {
                            key: 'created',
                            label: 'Created',
                            color: '#3b82f6',
                        },
                        {
                            key: 'completed',
                            label: 'Completed',
                            color: '#16a34a',
                        },
                    ]}
                />

                <DonutChart
                    title="Inspection Status Distribution"
                    description="Current distribution of inspection statuses"
                    data={statusData}
                    centerLabel="Total"
                />
            </div>

            <BarChart
                title={
                    currentUser.role === 'admin'
                        ? 'Site Performance'
                        : currentUser.role === 'supervisor'
                            ? 'Manager Performance'
                            : currentUser.role === 'manager'
                                ? 'Team Performance'
                                : 'My Inspection Results'
                }
                description="Completed inspections within your permitted scope"
                data={completedByPerson}
            />
        </div>
    )
}
