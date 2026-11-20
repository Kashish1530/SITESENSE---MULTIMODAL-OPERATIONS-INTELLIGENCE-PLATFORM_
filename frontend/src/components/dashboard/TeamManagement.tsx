
import { useMemo, useState } from 'react'
import {
    UserPlus, Search, Users, UserCheck, UserX, Building2,
    ShieldCheck, Mail, X, CheckCircle2, AlertCircle,
    ArrowRightLeft, Eye,
} from 'lucide-react'
import { DEMO_SITES, type DemoUser } from '../../data/users'

type NewEmployeeInput = {
    name: string
    email: string
    managerId: string
}

type TeamManagementProps = {
    users: DemoUser[]
    onAddEmployee: (input: NewEmployeeInput) => DemoUser | null
    onReassignEmployee: (userId: string, managerId: string) => void
    onDeactivateEmployee: (userId: string) => void
    onPreviewUser: (user: DemoUser) => void
}

type RoleFilter = 'all' | 'supervisor' | 'manager' | 'employee'
type StatusFilter = 'all' | 'active' | 'inactive'

export default function TeamManagement({
    users,
    onAddEmployee,
    onReassignEmployee,
    onDeactivateEmployee,
    onPreviewUser,
}: TeamManagementProps) {
    const [search, setSearch] = useState('')
    const [roleFilter, setRoleFilter] = useState<RoleFilter>('all')
    const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
    const [showAddForm, setShowAddForm] = useState(false)
    const [name, setName] = useState('')
    const [email, setEmail] = useState('')
    const [managerId, setManagerId] = useState('')
    const [formError, setFormError] = useState('')
    const [createdEmployee, setCreatedEmployee] = useState<DemoUser | null>(null)
    const [reassignments, setReassignments] = useState<Record<string, string>>({})

    const managers = useMemo(
        () => users.filter(user => user.role === 'manager' && user.isActive),
        [users],
    )

    const employees = users.filter(user => user.role === 'employee')
    const activeEmployees = employees.filter(user => user.isActive)
    const activeManagers = users.filter(user => user.role === 'manager' && user.isActive)
    const activeSupervisors = users.filter(user => user.role === 'supervisor' && user.isActive)

    const filteredUsers = users.filter(user => {
        const term = search.trim().toLowerCase()

        const matchesSearch =
            !term ||
            user.name.toLowerCase().includes(term) ||
            user.email.toLowerCase().includes(term) ||
            user.employeeId.toLowerCase().includes(term)

        const matchesRole = roleFilter === 'all' || user.role === roleFilter

        const matchesStatus =
            statusFilter === 'all' ||
            (statusFilter === 'active' && user.isActive) ||
            (statusFilter === 'inactive' && !user.isActive)

        return matchesSearch && matchesRole && matchesStatus
    })

    function getManagerName(user: DemoUser) {
        if (!user.managerId) return '—'
        return users.find(item => item.id === user.managerId)?.name ?? 'Unassigned'
    }

    function getSiteName(user: DemoUser) {
        if (!user.siteId) return 'Organization-wide'
        return DEMO_SITES.find(site => site.id === user.siteId)?.name ?? 'Unknown site'
    }

    function handleAddEmployee(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault()
        setFormError('')
        setCreatedEmployee(null)

        const normalizedEmail = email.trim().toLowerCase()
        const normalizedName = name.trim()

        if (!normalizedName || !normalizedEmail || !managerId) {
            setFormError('Please complete all fields.')
            return
        }

        if (users.some(user => user.email.toLowerCase() === normalizedEmail)) {
            setFormError('An account with this email already exists.')
            return
        }

        const created = onAddEmployee({
            name: normalizedName,
            email: normalizedEmail,
            managerId,
        })

        if (!created) {
            setFormError('Unable to create the employee account.')
            return
        }

        setCreatedEmployee(created)
        setName('')
        setEmail('')
        setManagerId('')
    }

    function handleReassignment(user: DemoUser) {
        const selectedManagerId = reassignments[user.id]

        if (!selectedManagerId || selectedManagerId === user.managerId) return

        onReassignEmployee(user.id, selectedManagerId)

        setReassignments(previous => {
            const next = { ...previous }
            delete next[user.id]
            return next
        })
    }

    function handleDeactivate(user: DemoUser) {
        if (window.confirm(`Deactivate ${user.name}'s account? They will no longer be able to log in.`)) {
            onDeactivateEmployee(user.id)
        }
    }

    const inputClass =
        'w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100'

    return (
        <div className="space-y-7">
            <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                <div>
                    <p className="text-sm font-medium text-blue-600">Organization Management</p>
                    <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
                        Team Management
                    </h1>
                    <p className="mt-2 text-sm text-slate-500">
                        Manage accounts, reporting relationships and team assignments.
                    </p>
                </div>

                <button
                    type="button"
                    onClick={() => {
                        setShowAddForm(!showAddForm)
                        setCreatedEmployee(null)
                        setFormError('')
                    }}
                    className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
                >
                    {showAddForm ? <X size={17} /> : <UserPlus size={17} />}
                    {showAddForm ? 'Close Form' : 'Add Employee'}
                </button>
            </section>

            <div className="flex items-center gap-2 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-800">
                <ShieldCheck size={17} className="shrink-0" />
                Demo organization — changes are stored for this browser session only.
            </div>

            <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {[
                    { label: 'Total Accounts', value: users.length, icon: Users, style: 'bg-blue-50 text-blue-600' },
                    { label: 'Active Employees', value: activeEmployees.length, icon: UserCheck, style: 'bg-emerald-50 text-emerald-600' },
                    { label: 'Active Managers', value: activeManagers.length, icon: ShieldCheck, style: 'bg-violet-50 text-violet-600' },
                    { label: 'Active Supervisors', value: activeSupervisors.length, icon: Building2, style: 'bg-amber-50 text-amber-600' },
                ].map(metric => {
                    const Icon = metric.icon
                    return (
                        <div key={metric.label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                            <div className="flex items-center justify-between">
                                <p className="text-sm font-medium text-slate-500">{metric.label}</p>
                                <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${metric.style}`}>
                                    <Icon size={19} />
                                </div>
                            </div>
                            <p className="mt-3 text-2xl font-bold text-slate-900">{metric.value}</p>
                        </div>
                    )
                })}
            </section>

            {showAddForm && (
                <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                    <h2 className="text-lg font-semibold text-slate-900">Create Employee Account</h2>
                    <p className="mt-1 text-sm text-slate-500">Assign the employee to an active manager.</p>

                    {createdEmployee && (
                        <div className="mt-5 rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                            <div className="flex items-center gap-2 text-sm font-semibold text-emerald-800">
                                <CheckCircle2 size={18} /> Employee account created
                            </div>
                            <div className="mt-3 grid gap-2 text-sm text-emerald-900 sm:grid-cols-2">
                                <p><strong>Name:</strong> {createdEmployee.name}</p>
                                <p><strong>Employee ID:</strong> {createdEmployee.employeeId}</p>
                                <p><strong>Email:</strong> {createdEmployee.email}</p>
                                <p><strong>Demo password:</strong> {createdEmployee.password}</p>
                            </div>
                        </div>
                    )}

                    {formError && (
                        <div className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-700">
                            <AlertCircle size={17} /> {formError}
                        </div>
                    )}

                    <form onSubmit={handleAddEmployee} className="mt-5 space-y-4">
                        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                            <label className="block">
                                <span className="mb-1.5 block text-sm font-medium text-slate-700">Employee name</span>
                                <input value={name} onChange={event => setName(event.target.value)} className={inputClass} placeholder="e.g. Jordan Smith" required />
                            </label>
                            <label className="block">
                                <span className="mb-1.5 block text-sm font-medium text-slate-700">Email address</span>
                                <input type="email" value={email} onChange={event => setEmail(event.target.value)} className={inputClass} placeholder="employee@sitesense.demo" required />
                            </label>
                            <label className="block md:col-span-2">
                                <span className="mb-1.5 block text-sm font-medium text-slate-700">Assign manager</span>
                                <select value={managerId} onChange={event => setManagerId(event.target.value)} className={inputClass} required>
                                    <option value="">Select an active manager</option>
                                    {managers.map(manager => (
                                        <option key={manager.id} value={manager.id}>
                                            {manager.name} — {getSiteName(manager)}
                                        </option>
                                    ))}
                                </select>
                            </label>
                        </div>
                        <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4">
                            <button type="submit" disabled={!managers.length} className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
                                Create Account
                            </button>
                            <p className="text-xs text-slate-400">Site and supervisor are inherited from the selected manager.</p>
                        </div>
                    </form>
                </section>
            )}

            <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-100 p-5">
                    <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
                        <div>
                            <h2 className="font-semibold text-slate-900">Organization Directory</h2>
                            <p className="mt-1 text-xs text-slate-400">{filteredUsers.length} accounts displayed</p>
                        </div>
                        <div className="flex flex-col gap-3 sm:flex-row">
                            <div className="relative">
                                <Search size={17} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                                <input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search name, ID or email" className="w-full rounded-lg border border-slate-200 py-2.5 pl-9 pr-3 text-sm outline-none focus:border-blue-500 sm:w-64" />
                            </div>
                            <select value={roleFilter} onChange={event => setRoleFilter(event.target.value as RoleFilter)} className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700">
                                <option value="all">All roles</option>
                                <option value="supervisor">Supervisors</option>
                                <option value="manager">Managers</option>
                                <option value="employee">Employees</option>
                                <option value="admin">Admins</option>
                            </select>
                            <select value={statusFilter} onChange={event => setStatusFilter(event.target.value as StatusFilter)} className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700">
                                <option value="all">All statuses</option>
                                <option value="active">Active</option>
                                <option value="inactive">Inactive</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full min-w-[1050px] text-left text-sm">
                        <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-400">
                            <tr>
                                <th className="px-5 py-3 font-semibold">Account</th>
                                <th className="px-5 py-3 font-semibold">Role / ID</th>
                                <th className="px-5 py-3 font-semibold">Site</th>
                                <th className="px-5 py-3 font-semibold">Reports to</th>
                                <th className="px-5 py-3 font-semibold">Status</th>
                                <th className="px-5 py-3 font-semibold">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {filteredUsers.map(user => (
                                <tr key={user.id} className="hover:bg-slate-50">
                                    <td className="px-5 py-4">
                                        <div className="flex items-center gap-3">
                                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-600">
                                                {user.name.split(' ').map(part => part[0]).join('')}
                                            </div>
                                            <div>
                                                <p className="font-medium text-slate-800">{user.name}</p>
                                                <p className="mt-1 flex items-center gap-1 text-xs text-slate-400"><Mail size={11} />{user.email}</p>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-5 py-4">
                                        <p className="font-medium capitalize text-slate-700">{user.role}</p>
                                        <p className="mt-1 text-xs text-slate-400">{user.employeeId}</p>
                                    </td>
                                    <td className="px-5 py-4 text-slate-600">{getSiteName(user)}</td>
                                    <td className="px-5 py-4">
                                        {user.role === 'employee' ? (
                                            <div className="space-y-2">
                                                <p className="text-xs text-slate-500">{getManagerName(user)}</p>
                                                {user.isActive && (
                                                    <div className="flex items-center gap-2">
                                                        <select aria-label={`Reassign ${user.name}`} value={reassignments[user.id] ?? user.managerId ?? ''} onChange={event => setReassignments(previous => ({ ...previous, [user.id]: event.target.value }))} className="max-w-40 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs">
                                                            {managers.map(manager => <option key={manager.id} value={manager.id}>{manager.name}</option>)}
                                                        </select>
                                                        {reassignments[user.id] && reassignments[user.id] !== user.managerId && (
                                                            <button type="button" onClick={() => handleReassignment(user)} title="Save reassignment" className="rounded-md bg-blue-50 p-1.5 text-blue-700 hover:bg-blue-100">
                                                                <ArrowRightLeft size={14} />
                                                            </button>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        ) : user.role === 'manager' ? (
                                            users.find(item => item.id === user.supervisorId)?.name ?? '—'
                                        ) : '—'}
                                    </td>
                                    <td className="px-5 py-4">
                                        <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${user.isActive ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                                            {user.isActive ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td className="px-5 py-4">
                                        <div className="flex items-center gap-1">
                                            {user.isActive && user.role !== 'admin' && (
                                                <button type="button" onClick={() => onPreviewUser(user)} className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-xs font-medium text-blue-700 hover:bg-blue-50">
                                                    <Eye size={14} /> Preview
                                                </button>
                                            )}
                                            {user.role === 'employee' && user.isActive && (
                                                <button type="button" onClick={() => handleDeactivate(user)} className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-xs font-medium text-red-600 hover:bg-red-50">
                                                    <UserX size={14} /> Deactivate
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {filteredUsers.length === 0 && (
                                <tr><td colSpan={6} className="px-5 py-12 text-center text-sm text-slate-400">No accounts match your search or filters.</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    )
}
