
import type { InspectionRecord } from './types'

const ACTIVE_STATUSES = ['Draft', 'Scheduled', 'In Progress']

export function getEmployeeTasks(
    inspections: InspectionRecord[],
    userId: string,
): InspectionRecord[] {
    return inspections
        .filter(task => task.assignedToUserId === userId)
        .sort(
            (a, b) =>
                new Date(a.dueDate).getTime() -
                new Date(b.dueDate).getTime(),
        )
}

export function getActiveTasks(
    inspections: InspectionRecord[],
    userId: string,
): InspectionRecord[] {
    return getEmployeeTasks(inspections, userId).filter(task =>
        ACTIVE_STATUSES.includes(task.status),
    )
}

export function getCompletedTasks(
    inspections: InspectionRecord[],
    userId: string,
): InspectionRecord[] {
    return getEmployeeTasks(inspections, userId).filter(
        task => task.status === 'Completed',
    )
}
