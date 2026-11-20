
import {
    Activity,
    Building2,
    ClipboardCheck,
    FileText,
    LayoutDashboard,
    MessageSquare,
    Settings,
    ShieldCheck,
    Users,
    Upload,
    Search,
    PanelLeftClose,
    PanelLeftOpen,
    X,
} from 'lucide-react'
import type { DemoUser } from '../../data/users'
import { getRoleConfig } from '../../data/roles'

type SidebarProps = {
    collapsed: boolean
    onToggle: () => void
    mobileOpen: boolean
    onMobileClose: () => void
    activePage: string
    onNavigate: (page: string) => void
    currentUser: DemoUser
}

const iconMap = {
    Overview: LayoutDashboard,
    'My Dashboard': LayoutDashboard,
    Search,
    Inspections: ClipboardCheck,
    Upload,
    'Review Queue': ShieldCheck,
    'Intelligence Chat': MessageSquare,
    'Agent Trace Viewer': Activity,
    'Report Viewer': FileText,
    'Sites & Zones': Building2,
    Team: Users,
    Settings,
    'My Tasks': ClipboardCheck,
    'My History': FileText,
}

const sectionMap: Record<string, string> = {
    Overview: 'WORKSPACE',
    'My Dashboard': 'WORKSPACE',
    Search: 'WORKSPACE',
    Inspections: 'WORKSPACE',
    Upload: 'WORKSPACE',
    'My Tasks': 'WORKSPACE',
    'My History': 'WORKSPACE',
    'Review Queue': 'OPERATIONS',
    'Intelligence Chat': 'INTELLIGENCE',
    'Agent Trace Viewer': 'INTELLIGENCE',
    'Report Viewer': 'REPORTS',
    'Sites & Zones': 'MANAGEMENT',
    Team: 'MANAGEMENT',
    Settings: 'MANAGEMENT',
}

function getInitials(name: string) {
    return name
        .split(' ')
        .map((part) => part[0])
        .join('')
        .slice(0, 2)
        .toUpperCase()
}

export default function Sidebar({
    collapsed,
    onToggle,
    mobileOpen,
    onMobileClose,
    activePage,
    onNavigate,
    currentUser,
}: SidebarProps) {
    const roleConfig = getRoleConfig(currentUser.role)

    const visibleSections = [
        'WORKSPACE',
        'OPERATIONS',
        'INTELLIGENCE',
        'REPORTS',
        'MANAGEMENT',
    ]

    const groupedNavigation = visibleSections
        .map((section) => ({
            section,
            items: roleConfig.navigation.filter(
                (item) => sectionMap[item] === section,
            ),
        }))
        .filter((group) => group.items.length > 0)

    return (
        <>
            {mobileOpen && (
                <button
                    className="fixed inset-0 z-40 bg-slate-950/40 lg:hidden"
                    onClick={onMobileClose}
                    aria-label="Close navigation"
                />
            )}

            <aside
                className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-slate-200 bg-white transition-all duration-200 lg:static lg:z-auto ${collapsed ? 'lg:w-[76px]' : 'lg:w-64'
                    } ${mobileOpen
                        ? 'translate-x-0'
                        : '-translate-x-full lg:translate-x-0'
                    }`}
            >
                <div className="flex h-[72px] items-center justify-between border-b border-slate-100 px-5">
                    <div className="flex items-center gap-3 overflow-hidden">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white">
                            <Activity size={21} />
                        </div>

                        <div className={collapsed ? 'lg:hidden' : ''}>
                            <h1 className="whitespace-nowrap text-lg font-bold tracking-tight text-slate-900">
                                SiteSense
                            </h1>
                            <p className="whitespace-nowrap text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                                Operations Intelligence
                            </p>
                        </div>
                    </div>

                    <button
                        onClick={onMobileClose}
                        className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
                        aria-label="Close sidebar"
                    >
                        <X size={19} />
                    </button>

                    <button
                        onClick={onToggle}
                        className={`hidden rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-900 lg:block ${collapsed ? 'lg:hidden' : ''
                            }`}
                        aria-label="Collapse sidebar"
                        title="Collapse sidebar"
                    >
                        <PanelLeftClose size={18} />
                    </button>
                </div>

                {collapsed && (
                    <button
                        onClick={onToggle}
                        className="hidden self-center rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:block"
                        aria-label="Expand sidebar"
                        title="Expand sidebar"
                    >
                        <PanelLeftOpen size={18} />
                    </button>
                )}

                <nav className="flex-1 space-y-7 overflow-y-auto px-3 py-6">
                    {groupedNavigation.map((group) => (
                        <div key={group.section}>
                            <p
                                className={`mb-2 px-3 text-[10px] font-bold tracking-[0.14em] text-slate-400 ${collapsed ? 'lg:hidden' : ''
                                    }`}
                            >
                                {group.section}
                            </p>

                            <div className="space-y-1">
                                {group.items.map((item) => {
                                    const Icon =
                                        iconMap[item as keyof typeof iconMap] ??
                                        LayoutDashboard

                                    const active = activePage === item

                                    return (
                                        <button
                                            key={item}
                                            onClick={() => {
                                                onNavigate(item)
                                                onMobileClose()
                                            }}
                                            title={collapsed ? item : undefined}
                                            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors ${active
                                                    ? 'bg-blue-50 text-blue-700'
                                                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                                                } ${collapsed
                                                    ? 'lg:justify-center lg:px-2'
                                                    : ''
                                                }`}
                                        >
                                            <Icon size={19} className="shrink-0" />
                                            <span className={collapsed ? 'lg:hidden' : ''}>
                                                {item}
                                            </span>
                                        </button>
                                    )
                                })}
                            </div>
                        </div>
                    ))}
                </nav>

                <div className="border-t border-slate-100 p-4">
                    <div
                        className={`flex items-center gap-3 ${collapsed ? 'lg:justify-center' : ''
                            }`}
                    >
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-700">
                            {getInitials(currentUser.name)}
                        </div>

                        <div className={`min-w-0 ${collapsed ? 'lg:hidden' : ''}`}>
                            <p className="truncate text-sm font-semibold text-slate-800">
                                {currentUser.name}
                            </p>
                            <p className="text-xs capitalize text-slate-400">
                                {currentUser.role}
                            </p>
                        </div>
                    </div>
                </div>
            </aside>
        </>
    )
}
