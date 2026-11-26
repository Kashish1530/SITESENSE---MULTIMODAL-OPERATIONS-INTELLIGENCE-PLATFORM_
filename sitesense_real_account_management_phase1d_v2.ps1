$ErrorActionPreference = "Stop"

$root = (Get-Location).Path
$frontend = Join-Path $root "_integration_staging\gargi_backend\SITESENSE---MULTIMODAL-OPERATIONS-INTELLIGENCE-PLATFORM_-Gargi_backend\frontend"
$app = Join-Path $frontend "src\App.tsx"
$client = Join-Path $frontend "src\api\client.ts"
$team = Join-Path $frontend "src\components\dashboard\TeamManagement.tsx"

foreach ($file in @($app, $client, $team)) {
  if (-not (Test-Path -LiteralPath $file)) { throw "Required file not found: $file" }
}

$appText = (Get-Content -LiteralPath $app -Raw) -replace "`r`n", "`n"
$clientText = (Get-Content -LiteralPath $client -Raw) -replace "`r`n", "`n"
$teamText = (Get-Content -LiteralPath $team -Raw) -replace "`r`n", "`n"

if ($appText -notmatch 'function handleAddEmployee\(input: \{') { throw "Expected handleAddEmployee function not found." }
if ($appText -notmatch 'onAddEmployee=\{handleAddEmployee\}') { throw "Expected TeamManagement callback binding not found." }
if ($clientText -notmatch "password: input\.password \|\| 'SiteSense@2026'") { throw "Expected hardcoded password fallback not found; client.ts was not patched." }
if ($teamText -notmatch "import \{ DEMO_SITES, type DemoUser \} from '../../data/users'") { throw "Expected original TeamManagement demo import not found." }

$backup = Join-Path $root ("_integration_backups\real_team_management_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
Copy-Item -LiteralPath $app -Destination (Join-Path $backup "App.tsx")
Copy-Item -LiteralPath $client -Destination (Join-Path $backup "client.ts")
Copy-Item -LiteralPath $team -Destination (Join-Path $backup "TeamManagement.tsx")

try {
  # harsh changes starts
  # Fix the photo upload handler's comment/return line if it was joined during the prior patch.
  $appText = $appText.Replace(
    "// Keep inspection status unchanged until a dedicated backend submission workflow exists.      return true",
    "// Keep inspection status unchanged until a dedicated backend submission workflow exists.`n      return true"
  )


  # Replace optimistic/demo employee creation with an awaited backend create.
  $newHandler = @'
  // harsh changes starts
  async function handleAddEmployee(input: {
    name: string
    email: string
    password: string
    role: string
    siteId: string
  }): Promise<DemoUser | null> {
    if (!getStoredAccessToken()) return null

    try {
      const created = await createAdminUserApi({
        name: input.name,
        email: input.email,
        password: input.password,
        role: input.role,
        site_id: input.siteId,
      })

      if (!created?.id) {
        throw new Error('Backend did not return the created account ID.')
      }

      const newUser: DemoUser = {
        id: created.id,
        employeeId: '',
        name: created.name,
        email: created.email,
        password: '',
        role: toFrontendRole(created.role),
        siteId: created.site_ids?.[0] ?? input.siteId ?? null,
        supervisorId: null,
        managerId: null,
        isActive: created.is_active ?? true,
      }

      setUsers(previousUsers => [
        ...previousUsers.filter(user => user.id !== newUser.id),
        newUser,
      ])
      return newUser
    } catch (error) {
      console.error('Backend account creation failed:', error)
      return null
    }
  }
  // harsh changes end

'@
  $appText = [regex]::Replace(
    $appText,
    '(?s)  function handleAddEmployee\(input: \{.*?(?=  function handleReassignEmployee\()',
    $newHandler,
    1
  )
  if ($appText -notmatch 'async function handleAddEmployee') { throw "Async account handler replacement failed." }

  # harsh changes starts
  # Remove obsolete client-only hierarchy handlers; backend schema has no manager relationship.
  $appText = [regex]::Replace(
    $appText,
    '(?s)  function handleReassignEmployee\(.*?(?=  function renderDashboard\()',
    "  // harsh changes starts`n  // Manager reassignment is not supported by the current backend account schema.`n  // harsh changes end`n`n",
    1
  )
  # Remove props for the removed hierarchy and preview actions.
  $appText = [regex]::Replace(
    $appText,
    '\s+onReassignEmployee=\{handleReassignEmployee\}\s+onDeactivateEmployee=\{handleDeactivateEmployee\}\s+onPreviewUser=\{handlePreviewUser\}',
    '',
    1
  )
  # harsh changes end

  # harsh changes starts
  # Remove invalid synthetic employee-number generation from the admin user mapping.
  $appText = [regex]::Replace(
    $appText,
    'employeeId: `EMP-\$\{ru\.id\.slice\(0, 6\)\.toUpperCase\(\)\}`,',
    "employeeId: '', // harsh changes starts`n          // No employee number is supplied by the backend.`n          // harsh changes end",
    1
  )
  # harsh changes end

  # Make password mandatory and remove the fallback credential.
  $clientText = [regex]::Replace(
    $clientText,
    'password\?: string',
    'password: string',
    1
  )
  $clientText = $clientText.Replace(
    "password: input.password || 'SiteSense@2026',",
    "password: input.password,"
  )
  # Repair a previously observed joined UUID guard if present.
  $clientText = [regex]::Replace(
    $clientText,
    '(test\(userId\))\s+if \(!isUuid\) return null',
    '$1' + "`n  if (!isUuid) return null",
    1
  )
  if ($clientText -match "SiteSense@2026|password\?: string") { throw "Hardcoded password or optional password remains in client.ts." }

  # Replace TeamManagement with a backend-backed directory and create form.
  $newTeam = @'
import { useEffect, useMemo, useState } from 'react'
import { AlertCircle, Building2, CheckCircle2, Mail, Search, ShieldCheck, UserPlus, Users, X } from 'lucide-react'
import { getSitesApi } from '../../api/client'
import type { DemoUser } from '../../data/users'

type NewAccountInput = {
  name: string
  email: string
  password: string
  role: string
  siteId: string
}

type TeamManagementProps = {
  users: DemoUser[]
  onAddEmployee: (input: NewAccountInput) => Promise<DemoUser | null>
}

type RoleFilter = 'all' | 'supervisor' | 'manager' | 'employee' | 'admin'
type StatusFilter = 'all' | 'active' | 'inactive'

export default function TeamManagement({ users, onAddEmployee }: TeamManagementProps) {
  const [sites, setSites] = useState<Awaited<ReturnType<typeof getSitesApi>>>([])
  const [sitesLoading, setSitesLoading] = useState(true)
  const [sitesError, setSitesError] = useState('')
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [showAddForm, setShowAddForm] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('employee')
  const [siteId, setSiteId] = useState('')
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [createdEmployee, setCreatedEmployee] = useState<DemoUser | null>(null)

  useEffect(() => {
    let active = true
    getSitesApi()
      .then(result => {
        if (active) setSites(result)
      })
      .catch(error => {
        if (active) setSitesError(error instanceof Error ? error.message : 'Could not load sites.')
      })
      .finally(() => {
        if (active) setSitesLoading(false)
      })
    return () => { active = false }
  }, [])

  const activeUsers = useMemo(
    () => users.filter(user => user.isActive),
    [users],
  )
  const filteredUsers = users.filter(user => {
    const term = search.trim().toLowerCase()
    const matchesSearch = !term ||
      user.name.toLowerCase().includes(term) ||
      user.email.toLowerCase().includes(term) ||
      user.id.toLowerCase().includes(term)
    const matchesRole = roleFilter === 'all' || user.role === roleFilter
    const matchesStatus = statusFilter === 'all' ||
      (statusFilter === 'active' && user.isActive) ||
      (statusFilter === 'inactive' && !user.isActive)
    return matchesSearch && matchesRole && matchesStatus
  })

  function siteName(id: string | null) {
    if (!id) return 'No site assigned'
    return sites.find(site => site.id === id)?.name ?? 'Site unavailable'
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError('')
    setCreatedEmployee(null)

    if (name.trim().length < 2 || password.length < 6 || !email.trim()) {
      setFormError('Enter a name, valid email, and password of at least 6 characters.')
      return
    }
    if (!siteId) {
      setFormError('Select a real site for this account.')
      return
    }

    setSubmitting(true)
    try {
      const created = await onAddEmployee({
        name: name.trim(),
        email: email.trim().toLowerCase(),
        password,
        role,
        siteId,
      })
      if (!created) {
        setFormError('The backend did not create this account. Check the email and try again.')
        return
      }
      setCreatedEmployee(created)
      setName('')
      setEmail('')
      setPassword('')
      setRole('employee')
      setSiteId('')
    } finally {
      setSubmitting(false)
    }
  }

  const inputClass = 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100'

  return (
    <div className="space-y-7">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <p className="text-sm font-medium text-blue-600">Organization Management</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Team Management</h1>
          <p className="mt-2 text-sm text-slate-500">Manage real accounts and their site memberships.</p>
        </div>
        <button type="button" onClick={() => { setShowAddForm(!showAddForm); setCreatedEmployee(null); setFormError('') }} className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700">
          {showAddForm ? <X size={17} /> : <UserPlus size={17} />}
          {showAddForm ? 'Close Form' : 'Add Account'}
        </button>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          { label: 'Total Accounts', value: users.length, icon: Users },
          { label: 'Active Accounts', value: activeUsers.length, icon: ShieldCheck },
          { label: 'Available Sites', value: sites.length, icon: Building2 },
        ].map(metric => {
          const Icon = metric.icon
          return <div key={metric.label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-slate-500">{metric.label}</p>
              <Icon size={19} className="text-blue-600" />
            </div>
            <p className="mt-3 text-2xl font-bold text-slate-900">{metric.value}</p>
          </div>
        })}
      </section>

      {showAddForm && <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <h2 className="text-lg font-semibold text-slate-900">Create Account</h2>
        <p className="mt-1 text-sm text-slate-500">The account will be saved by the backend and assigned to the selected site.</p>
        {createdEmployee && <div className="mt-5 rounded-lg border border-emerald-200 bg-emerald-50 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-emerald-800"><CheckCircle2 size={18} /> Account created in the backend</div>
          <div className="mt-3 grid gap-2 text-sm text-emerald-900 sm:grid-cols-2">
            <p><strong>Name:</strong> {createdEmployee.name}</p>
            <p><strong>Account ID:</strong> {createdEmployee.id}</p>
            <p><strong>Email:</strong> {createdEmployee.email}</p>
            <p><strong>Site:</strong> {siteName(createdEmployee.siteId)}</p>
          </div>
        </div>}
        {formError && <div className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-700"><AlertCircle size={17} /> {formError}</div>}
        {sitesError && <div className="mt-4 text-sm text-red-600">{sitesError}</div>}
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-slate-700">Full name</span>
              <input value={name} onChange={event => setName(event.target.value)} className={inputClass} autoComplete="name" required minLength={2} />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-slate-700">Email address</span>
              <input type="email" value={email} onChange={event => setEmail(event.target.value)} className={inputClass} autoComplete="email" required />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-slate-700">Initial password (minimum 6 characters)</span>
              <input type="password" value={password} onChange={event => setPassword(event.target.value)} className={inputClass} autoComplete="new-password" minLength={6} required />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-slate-700">Role</span>
              <select value={role} onChange={event => setRole(event.target.value)} className={inputClass}>
                <option value="employee">Employee</option>
                <option value="manager">Manager</option>
                <option value="supervisor">Supervisor</option>
                <option value="admin">Admin</option>
              </select>
            </label>
            <label className="block md:col-span-2">
              <span className="mb-1.5 block text-sm font-medium text-slate-700">Site</span>
              <select value={siteId} onChange={event => setSiteId(event.target.value)} className={inputClass} required disabled={sitesLoading || sites.length === 0}>
                <option value="">{sitesLoading ? 'Loading sites…' : 'Select a real site'}</option>
                {sites.map(site => <option key={site.id} value={site.id}>{site.name} — {site.region}</option>)}
              </select>
              {!sitesLoading && sites.length === 0 && <span className="mt-1 block text-xs text-slate-500">No accessible sites are available. Create or assign a site before creating this account.</span>}
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4">
            <button type="submit" disabled={submitting || sitesLoading || sites.length === 0} className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
              {submitting ? 'Creating…' : 'Create Account'}
            </button>
            <p className="text-xs text-slate-400">Success appears only after the backend returns the account ID.</p>
          </div>
        </form>
      </section>}

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 p-5">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
            <div>
              <h2 className="font-semibold text-slate-900">Account Directory</h2>
              <p className="mt-1 text-xs text-slate-400">{filteredUsers.length} accounts displayed</p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <div className="relative">
                <Search size={17} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search name, UUID or email" className="w-full rounded-lg border border-slate-200 py-2.5 pl-9 pr-3 text-sm outline-none focus:border-blue-500 sm:w-64" />
              </div>
              <select value={roleFilter} onChange={event => setRoleFilter(event.target.value as RoleFilter)} className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700">
                <option value="all">All roles</option><option value="supervisor">Supervisors</option><option value="manager">Managers</option><option value="employee">Employees</option><option value="admin">Admins</option>
              </select>
              <select value={statusFilter} onChange={event => setStatusFilter(event.target.value as StatusFilter)} className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700">
                <option value="all">All statuses</option><option value="active">Active</option><option value="inactive">Inactive</option>
              </select>
            </div>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-400">
              <tr><th className="px-5 py-3 font-semibold">Account</th><th className="px-5 py-3 font-semibold">Role</th><th className="px-5 py-3 font-semibold">Site</th><th className="px-5 py-3 font-semibold">Status</th><th className="px-5 py-3 font-semibold">Account UUID</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredUsers.map(user => <tr key={user.id} className="hover:bg-slate-50">
                <td className="px-5 py-4"><p className="font-medium text-slate-800">{user.name}</p><p className="mt-1 flex items-center gap-1 text-xs text-slate-400"><Mail size={11} />{user.email}</p></td>
                <td className="px-5 py-4 font-medium capitalize text-slate-700">{user.role}</td>
                <td className="px-5 py-4 text-slate-600">{siteName(user.siteId)}</td>
                <td className="px-5 py-4"><span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${user.isActive ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>{user.isActive ? 'Active' : 'Inactive'}</span></td>
                <td className="px-5 py-4 font-mono text-xs text-slate-500">{user.id}</td>
              </tr>)}
              {filteredUsers.length === 0 && <tr><td colSpan={5} className="px-5 py-12 text-center text-sm text-slate-400">No real accounts match your search or filters.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
'@
  $teamText = "// harsh changes starts`n// Team directory now displays backend accounts and real site memberships only.`n// harsh changes end`n" + $newTeam
  # harsh changes end

  # Validate key transformations before writing.
  if ($appText -match 'SiteSense@2026|EMP-\$\{ru\.id|const employeeNumber = getNextNumber|const initialPassword') { throw "PHASE1D_V2_VALIDATION: App.tsx still contains fake account-generation logic." }
  if ($teamText -match 'DEMO_SITES|Demo organization|Demo password|managerId|supervisorId|onReassignEmployee|onDeactivateEmployee|onPreviewUser') { throw "PHASE1D_V2_VALIDATION: TeamManagement replacement still contains an unsupported legacy reference." }
  if ($clientText -match 'SiteSense@2026|password\?: string') { throw "client.ts still contains a password fallback." }

  Set-Content -LiteralPath $app -Value $appText -Encoding utf8
  Set-Content -LiteralPath $client -Value $clientText -Encoding utf8
  Set-Content -LiteralPath $team -Value $teamText -Encoding utf8

  Write-Host "PHASE1D_V2: Real account-management patch applied."
  Write-Host "Backups: $backup"
  Write-Host "PHASE1D_V2 Changed: App.tsx, api/client.ts, components/dashboard/TeamManagement.tsx"
}
catch {
  Copy-Item -LiteralPath (Join-Path $backup "App.tsx") -Destination $app -Force
  Copy-Item -LiteralPath (Join-Path $backup "client.ts") -Destination $client -Force
  Copy-Item -LiteralPath (Join-Path $backup "TeamManagement.tsx") -Destination $team -Force
  throw "Patch failed. All original files restored. Backup: $backup. Details: $($_.Exception.Message)"
}
