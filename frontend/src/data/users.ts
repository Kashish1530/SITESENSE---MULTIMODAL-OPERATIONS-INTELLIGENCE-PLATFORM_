
import type { DemoRole } from './roles'

export type DemoSite = {
    id: string
    name: string
    region: string
}

export type DemoUser = {
    id: string
    employeeId: string
    name: string
    email: string
    password: string
    role: DemoRole
    siteId: string | null
    supervisorId: string | null
    managerId: string | null
    isActive: boolean
}

export const DEMO_SITES: DemoSite[] = [
    {
        id: 'SITE-001',
        name: 'North Warehouse',
        region: 'North Region',
    },
    {
        id: 'SITE-002',
        name: 'South Warehouse',
        region: 'South Region',
    },
    {
        id: 'SITE-003',
        name: 'Central Distribution Centre',
        region: 'Central Region',
    },
]

export const DEMO_USERS: DemoUser[] = [
    // ADMIN
    {
        id: 'USER-001',
        employeeId: 'ADM-001',
        name: 'Alex Morgan',
        email: 'admin@sitesense.demo',
        password: 'SiteDemo#ADM001',
        role: 'admin',
        siteId: null,
        supervisorId: null,
        managerId: null,
        isActive: true,
    },

    // SUPERVISORS
    {
        id: 'USER-002',
        employeeId: 'SUP-001',
        name: 'Sarah Mitchell',
        email: 'sarah.mitchell@sitesense.demo',
        password: 'SiteDemo#SUP001',
        role: 'supervisor',
        siteId: 'SITE-001',
        supervisorId: null,
        managerId: null,
        isActive: true,
    },
    {
        id: 'USER-003',
        employeeId: 'SUP-002',
        name: 'Daniel Carter',
        email: 'daniel.carter@sitesense.demo',
        password: 'SiteDemo#SUP002',
        role: 'supervisor',
        siteId: 'SITE-002',
        supervisorId: null,
        managerId: null,
        isActive: true,
    },
    {
        id: 'USER-004',
        employeeId: 'SUP-003',
        name: 'Olivia Bennett',
        email: 'olivia.bennett@sitesense.demo',
        password: 'SiteDemo#SUP003',
        role: 'supervisor',
        siteId: 'SITE-003',
        supervisorId: null,
        managerId: null,
        isActive: true,
    },

    // MANAGERS — SUPERVISOR 1
    {
        id: 'USER-005',
        employeeId: 'MGR-001',
        name: 'James Wilson',
        email: 'james.wilson@sitesense.demo',
        password: 'SiteDemo#MGR001',
        role: 'manager',
        siteId: 'SITE-001',
        supervisorId: 'USER-002',
        managerId: null,
        isActive: true,
    },
    {
        id: 'USER-006',
        employeeId: 'MGR-002',
        name: 'Emily Davis',
        email: 'emily.davis@sitesense.demo',
        password: 'SiteDemo#MGR002',
        role: 'manager',
        siteId: 'SITE-001',
        supervisorId: 'USER-002',
        managerId: null,
        isActive: true,
    },

    // MANAGERS — SUPERVISOR 2
    {
        id: 'USER-007',
        employeeId: 'MGR-003',
        name: 'Michael Brown',
        email: 'michael.brown@sitesense.demo',
        password: 'SiteDemo#MGR003',
        role: 'manager',
        siteId: 'SITE-002',
        supervisorId: 'USER-003',
        managerId: null,
        isActive: true,
    },
    {
        id: 'USER-008',
        employeeId: 'MGR-004',
        name: 'Sophia Taylor',
        email: 'sophia.taylor@sitesense.demo',
        password: 'SiteDemo#MGR004',
        role: 'manager',
        siteId: 'SITE-002',
        supervisorId: 'USER-003',
        managerId: null,
        isActive: true,
    },

    // MANAGERS — SUPERVISOR 3
    {
        id: 'USER-009',
        employeeId: 'MGR-005',
        name: 'William Anderson',
        email: 'william.anderson@sitesense.demo',
        password: 'SiteDemo#MGR005',
        role: 'manager',
        siteId: 'SITE-003',
        supervisorId: 'USER-004',
        managerId: null,
        isActive: true,
    },
    {
        id: 'USER-010',
        employeeId: 'MGR-006',
        name: 'Ava Thomas',
        email: 'ava.thomas@sitesense.demo',
        password: 'SiteDemo#MGR006',
        role: 'manager',
        siteId: 'SITE-003',
        supervisorId: 'USER-004',
        managerId: null,
        isActive: true,
    },

    // EMPLOYEES — MANAGER 1
    {
        id: 'USER-011',
        employeeId: 'EMP-001',
        name: 'Noah Martin',
        email: 'noah.martin@sitesense.demo',
        password: 'SiteDemo#EMP001',
        role: 'employee',
        siteId: 'SITE-001',
        supervisorId: 'USER-002',
        managerId: 'USER-005',
        isActive: true,
    },
    {
        id: 'USER-012',
        employeeId: 'EMP-002',
        name: 'Isabella Lee',
        email: 'isabella.lee@sitesense.demo',
        password: 'SiteDemo#EMP002',
        role: 'employee',
        siteId: 'SITE-001',
        supervisorId: 'USER-002',
        managerId: 'USER-005',
        isActive: true,
    },
    {
        id: 'USER-013',
        employeeId: 'EMP-003',
        name: 'Ethan Clark',
        email: 'ethan.clark@sitesense.demo',
        password: 'SiteDemo#EMP003',
        role: 'employee',
        siteId: 'SITE-001',
        supervisorId: 'USER-002',
        managerId: 'USER-005',
        isActive: true,
    },

    // EMPLOYEES — MANAGER 2
    {
        id: 'USER-014',
        employeeId: 'EMP-004',
        name: 'Mia Rodriguez',
        email: 'mia.rodriguez@sitesense.demo',
        password: 'SiteDemo#EMP004',
        role: 'employee',
        siteId: 'SITE-001',
        supervisorId: 'USER-002',
        managerId: 'USER-006',
        isActive: true,
    },
    {
        id: 'USER-015',
        employeeId: 'EMP-005',
        name: 'Lucas Lewis',
        email: 'lucas.lewis@sitesense.demo',
        password: 'SiteDemo#EMP005',
        role: 'employee',
        siteId: 'SITE-001',
        supervisorId: 'USER-002',
        managerId: 'USER-006',
        isActive: true,
    },

    // EMPLOYEES — MANAGER 3
    {
        id: 'USER-016',
        employeeId: 'EMP-006',
        name: 'Charlotte Walker',
        email: 'charlotte.walker@sitesense.demo',
        password: 'SiteDemo#EMP006',
        role: 'employee',
        siteId: 'SITE-002',
        supervisorId: 'USER-003',
        managerId: 'USER-007',
        isActive: true,
    },
    {
        id: 'USER-017',
        employeeId: 'EMP-007',
        name: 'Benjamin Hall',
        email: 'benjamin.hall@sitesense.demo',
        password: 'SiteDemo#EMP007',
        role: 'employee',
        siteId: 'SITE-002',
        supervisorId: 'USER-003',
        managerId: 'USER-007',
        isActive: true,
    },

    // EMPLOYEES — MANAGER 4
    {
        id: 'USER-018',
        employeeId: 'EMP-008',
        name: 'Amelia Young',
        email: 'amelia.young@sitesense.demo',
        password: 'SiteDemo#EMP008',
        role: 'employee',
        siteId: 'SITE-002',
        supervisorId: 'USER-003',
        managerId: 'USER-008',
        isActive: true,
    },

    // EMPLOYEES — MANAGER 5
    {
        id: 'USER-019',
        employeeId: 'EMP-009',
        name: 'Henry Allen',
        email: 'henry.allen@sitesense.demo',
        password: 'SiteDemo#EMP009',
        role: 'employee',
        siteId: 'SITE-003',
        supervisorId: 'USER-004',
        managerId: 'USER-009',
        isActive: true,
    },

    // EMPLOYEES — MANAGER 6
    {
        id: 'USER-020',
        employeeId: 'EMP-010',
        name: 'Harper King',
        email: 'harper.king@sitesense.demo',
        password: 'SiteDemo#EMP010',
        role: 'employee',
        siteId: 'SITE-003',
        supervisorId: 'USER-004',
        managerId: 'USER-010',
        isActive: true,
    },
]

export function findDemoUser(identifier: string): DemoUser | undefined {
    const normalized = identifier.trim().toLowerCase()

    return DEMO_USERS.find(
        (user) =>
            user.email.toLowerCase() === normalized ||
            user.employeeId.toLowerCase() === normalized,
    )
}

export function getDemoSite(siteId: string | null): DemoSite | undefined {
    if (!siteId) return undefined

    return DEMO_SITES.find((site) => site.id === siteId)
}

export function getDirectReports(userId: string): DemoUser[] {
    return DEMO_USERS.filter(
        (user) =>
            user.supervisorId === userId ||
            user.managerId === userId,
    )
}
