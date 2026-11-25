
export type DemoRole = 'admin' | 'supervisor' | 'manager' | 'employee'

export type RoleConfig = {
    id: DemoRole
    name: string
    title: string
    initials: string
    description: string
    navigation: string[]
}

export const DEMO_ROLES: RoleConfig[] = [
    {
        id: 'admin',
        name: 'Demo Admin',
        title: 'Administrator',
        initials: 'AD',
        description: 'Organization-wide access and management.',
        navigation: [
            'Overview',
            'Search',
            'Inspections',
            'Upload',
            'Review Queue',
            'Intelligence Chat',
            'Agent Trace Viewer',
            'Report Viewer',
            'Sites & Zones',
            'Team',
            'Settings',
        ],
    },
    {
        id: 'supervisor',
        name: 'Demo Supervisor',
        title: 'Supervisor',
        initials: 'SV',
        description: 'Oversee assigned sites, managers and teams.',
        navigation: [
            'Overview',
            'Search',
            'Inspections',
            'Upload',
            'Review Queue',
            'Report Viewer',
            'Sites & Zones',
            'Team',
        ],
    },
    {
        id: 'manager',
        name: 'Demo Manager',
        title: 'Manager',
        initials: 'MG',
        description: 'Manage assigned employees and operations.',
        navigation: [
            'Overview',
            'Search',
            'Inspections',
            'Upload',
            'Review Queue',
            'Report Viewer',
            'Team',
        ],
    },
    {
        id: 'employee',
        name: 'Demo Employee',
        title: 'Employee',
        initials: 'EM',
        description: 'Manage assigned tasks and field inspections.',
        navigation: [
            'My Dashboard',
            'My Tasks',
            'Search',
            'Inspections',
            'Upload',
            'My History',
        ],
    },
]

export function getRoleConfig(role: DemoRole): RoleConfig {
    return DEMO_ROLES.find((item) => item.id === role) ?? DEMO_ROLES[0]
}
