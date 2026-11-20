
import { useEffect, useState } from 'react'
import { DEMO_USERS, type DemoUser } from '../data/users'

const ORGANIZATION_STORAGE_KEY = 'sitesense_demo_organization'

function isDemoUser(value: unknown): value is DemoUser {
    if (!value || typeof value !== 'object') return false

    const user = value as Record<string, unknown>

    return (
        typeof user.id === 'string' &&
        typeof user.employeeId === 'string' &&
        typeof user.name === 'string' &&
        typeof user.email === 'string' &&
        typeof user.password === 'string' &&
        ['admin', 'supervisor', 'manager', 'employee'].includes(
            String(user.role),
        ) &&
        (typeof user.siteId === 'string' || user.siteId === null) &&
        (typeof user.supervisorId === 'string' ||
            user.supervisorId === null) &&
        (typeof user.managerId === 'string' ||
            user.managerId === null) &&
        typeof user.isActive === 'boolean'
    )
}

function loadOrganizationUsers(): DemoUser[] {
    try {
        const storedUsers = sessionStorage.getItem(
            ORGANIZATION_STORAGE_KEY,
        )

        if (!storedUsers) return DEMO_USERS

        const parsed: unknown = JSON.parse(storedUsers)

        if (
            Array.isArray(parsed) &&
            parsed.every(isDemoUser)
        ) {
            return parsed
        }

        return DEMO_USERS
    } catch {
        return DEMO_USERS
    }
}

export function useOrganizationUsers() {
    const [users, setUsers] = useState<DemoUser[]>(
        loadOrganizationUsers,
    )

    useEffect(() => {
        try {
            sessionStorage.setItem(
                ORGANIZATION_STORAGE_KEY,
                JSON.stringify(users),
            )
        } catch {
            // Keep the current organization state in memory.
        }
    }, [users])

    return {
        users,
        setUsers,
    }
}
