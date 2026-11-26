export type UserRole = 'admin' | 'supervisor' | 'manager' | 'employee'
export type DemoRole = UserRole

export type RoleConfig = {
    id: UserRole
    name: string
    title: string
    initials: string
    description: string
    navigation: string[]
}

export const ROLE_CONFIGS: RoleConfig[] = [
    {
        id: 'admin',
        name: 'Admin',
        title: 'Administrator',
        initials: 'AD',
        description: 'Organization-wide access and management.',
        navigation: [
            'Overview',
            'Search',
            'Inspections',
            'Upload',
            'Policies & Knowledge',
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
        name: 'Supervisor',
        title: 'Supervisor',
        initials: 'SV',
        description: 'Oversee assigned sites, managers and teams.',
        navigation: [
            'Overview',
            'Search',
            'Inspections',
            'Upload',
            'Policies & Knowledge',
            'Review Queue',
            'Report Viewer',
            'Sites & Zones',
            'Team',
        ],
    },
    {
        id: 'manager',
        name: 'Manager',
        title: 'Manager',
        initials: 'MG',
        description: 'Manage assigned employees and operations.',
        navigation: [
            'Overview',
            'Search',
            'Inspections',
            'Upload',
            'Policies & Knowledge',
            'Review Queue',
            'Report Viewer',
            'Team',
        ],
    },
    {
        id: 'employee',
        name: 'Employee',
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

export function getRoleConfig(role: UserRole): RoleConfig {
    return ROLE_CONFIGS.find((item) => item.id === role) ?? ROLE_CONFIGS[0]
}

export const DEMO_ROLES = ROLE_CONFIGS
