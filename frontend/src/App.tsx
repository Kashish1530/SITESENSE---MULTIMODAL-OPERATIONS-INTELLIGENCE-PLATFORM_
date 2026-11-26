import ReportViewer from './components/reports/ReportViewer'
import { useEffect, useRef, useState } from 'react'
import AppLayout from './components/layout/AppLayout'
import Overview from './components/dashboard/Overview'
import SupervisorDashboard from './components/dashboard/SupervisorDashboard'
import ManagerDashboard from './components/dashboard/ManagerDashboard'
import EmployeeDashboard from './components/dashboard/EmployeeDashboard'
import TeamManagement from './components/dashboard/TeamManagement'
import EmployeeSearch from './components/search/EmployeeSearch'
import InspectionDashboard from './components/inspections/InspectionDashboard'
import MyTasks from './components/inspections/MyTasks'
import UploadPage from './components/upload/UploadPage'
import MyHistory from './components/inspections/MyHistory'
import ReviewQueue from './components/inspections/ReviewQueue'
import ChatPage from './components/chat/ChatPage'
import SitesZonesPage from './components/zones/SitesZonesPage'
import Login from './components/auth/Login'
import { useOrganizationUsers } from './hooks/useOrganizationUsers'
import type { DemoUser } from './data/users'
import { getRoleConfig } from './data/roles'

import {
  INSPECTIONS,
  INSPECTION_FINDINGS,
  INSPECTION_EVIDENCE,
  CORRECTIVE_ACTIONS,
} from './data/inspectionData'

import type {
  InspectionRecord,
  InspectionFinding,
  InspectionEvidence,
  CorrectiveAction,
} from './inspections/types'

import {
  formatFileSize,
} from './inspections/taskPhotoAdapter'

import {
  loginApi,
  logoutApi,
  getCurrentUserApi,
  getInspectionsApi,
  batchUploadMediaApi,
  createAdminUserApi,
  getAdminUsersApi,
  getUsersDirectoryApi,
  updateAdminUserApi,
  toFrontendRole,
  getStoredAccessToken,
  getStoredAuthUser,
  clearStoredSession,
} from './api/client'

const SESSION_KEY = 'sitesense_demo_session'
const ACTIVE_TASK_STATUSES = ['Draft', 'Scheduled', 'In Progress']

function getInitialUserId(): string | null {
  try {
    return sessionStorage.getItem(SESSION_KEY)
  } catch {
    return null
  }
}

function getDefaultPage(user: DemoUser): string {
  return user.role === 'employee' ? 'My Dashboard' : 'Overview'
}

function getNextNumber(
  users: DemoUser[],
  field: 'id' | 'employeeId',
  prefix: string,
): number {
  const highestNumber = users.reduce((highest, user) => {
    const value = user[field]

    if (!value.startsWith(prefix)) return highest

    const number = Number(value.slice(prefix.length))

    return Number.isFinite(number)
      ? Math.max(number, highest)
      : highest
  }, 0)

  return highestNumber + 1
}

function createEvidenceId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `EVD-${crypto.randomUUID()}`
  }

  return `EVD-TASK-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function AppContent() {
  const { users, setUsers } = useOrganizationUsers()

  const [inspections, setInspections] =
    useState<InspectionRecord[]>(INSPECTIONS)

  const [findings, setFindings] =
    useState<InspectionFinding[]>(INSPECTION_FINDINGS)

  const [evidence, setEvidence] =
    useState<InspectionEvidence[]>(INSPECTION_EVIDENCE)

  const [correctiveActions, setCorrectiveActions] =
    useState<CorrectiveAction[]>(CORRECTIVE_ACTIONS)

  const inspectionsRef = useRef(inspections)

  useEffect(() => {
    inspectionsRef.current = inspections
  }, [inspections])

  const submittingTaskIds = useRef(new Set<string>())
  const evidencePreviewUrls = useRef<string[]>([])

  const [apiUser, setApiUser] = useState<DemoUser | null>(getStoredAuthUser)
  const [currentUserId, setCurrentUserId] =
    useState<string | null>(getInitialUserId)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [previewUserId, setPreviewUserId] = useState<string | null>(null)
  const [loginError, setLoginError] = useState('')
  const [selectedPage, setSelectedPage] = useState('Overview')

  const previewUser = previewUserId
    ? users.find(
      user => user.id === previewUserId && user.isActive,
    ) ?? null
    : null

  const currentUser = currentUserId
    ? users.find(user => user.id === currentUserId && user.isActive) ?? apiUser
    : apiUser

  const effectiveUser = previewUser ?? currentUser

  const allowedPages = effectiveUser
    ? getRoleConfig(effectiveUser.role).navigation
    : []

  const activePage =
    effectiveUser && allowedPages.includes(selectedPage)
      ? selectedPage
      : effectiveUser
        ? getDefaultPage(effectiveUser)
        : 'Overview'

  // Attempt token verification & restore user on mount
  useEffect(() => {
    const token = getStoredAccessToken()
    if (token && !apiUser) {
      getCurrentUserApi()
        .then(user => {
          if (user) {
            setApiUser(user)
            setCurrentUserId(user.id)
            setUsers(prev => {
              const idx = prev.findIndex(u => u.id === user.id || u.email === user.email)
              if (idx >= 0) {
                const clone = [...prev]
                clone[idx] = { ...clone[idx], ...user }
                return clone
              }
              return [user, ...prev]
            })
          }
        })
        .catch(() => {
          clearStoredSession()
        })
    }
  }, [])

  // Sync inspections from backend when logged in
  useEffect(() => {
    if (!effectiveUser || !getStoredAccessToken()) return
    getInspectionsApi()
      .then(remoteItems => {
        if (!remoteItems || remoteItems.length === 0) return
        const mapped: InspectionRecord[] = remoteItems.map(item => ({
          id: item.id,
          title: `Inspection ${item.id.slice(0, 8)}`,
          description: 'Synchronized from backend database',
          type: 'Safety',
          templateId: 'TMPL-001',
          siteId: item.site_id,
          zone: 'Zone A',
          status: (item.status === 'completed'
            ? 'Completed'
            : item.status === 'in_progress'
              ? 'In Progress'
              : 'Scheduled') as any,
          assignedToUserId: item.user_id || effectiveUser.id,
          assignedByUserId: effectiveUser.id,
          createdAt: item.created_at || new Date().toISOString(),
          scheduledAt: item.created_at || new Date().toISOString(),
          dueDate: item.created_at ? item.created_at.slice(0, 10) : new Date().toISOString().slice(0, 10),
          answers: [],
          observations: [],
          findingIds: [],
          evidenceIds: [],
          reviewStatus: (item.status === 'completed' ? 'Approved' : 'Pending') as any,
        }))

        setInspections(prev => {
          const remoteIds = new Set(mapped.map(m => m.id))
          return [...mapped, ...prev.filter(p => !remoteIds.has(p.id))]
        })
      })
      .catch(err => {
        console.warn('Could not fetch remote inspections:', err)
      })
  }, [effectiveUser?.id])

  // Sync users from backend database
  useEffect(() => {
    if (!effectiveUser || !getStoredAccessToken()) return
    const fetchUsers = effectiveUser.role === 'admin' ? getAdminUsersApi : getUsersDirectoryApi
    fetchUsers()
      .then((remoteUsers: any[]) => {
        if (!remoteUsers || remoteUsers.length === 0) return
        const globalReviewer = remoteUsers.find((r: any) => r.role === 'reviewer' || r.role === 'supervisor')
        const globalManager = remoteUsers.find((r: any) => r.role === 'manager')

        const mappedUsers: DemoUser[] = remoteUsers.map((ru: any) => {
          const feRole = toFrontendRole(ru.role)
          const assignedSiteId = ru.site_ids?.[0] || ru.site_id || null
          const siteReviewer = remoteUsers.find(
            (r: any) => (r.role === 'reviewer' || r.role === 'supervisor') && (r.site_ids?.[0] === assignedSiteId || r.site_id === assignedSiteId)
          ) || globalReviewer
          const siteManager = remoteUsers.find(
            (r: any) => r.role === 'manager' && (r.site_ids?.[0] === assignedSiteId || r.site_id === assignedSiteId)
          ) || globalManager

          return {
            id: ru.id,
            employeeId: `EMP-${ru.id.slice(0, 6).toUpperCase()}`,
            name: ru.name,
            email: ru.email,
            password: 'SiteSense@2026',
            role: feRole,
            siteId: assignedSiteId,
            supervisorId: feRole === 'employee' || feRole === 'manager' ? (siteReviewer?.id || null) : null,
            managerId: feRole === 'employee' ? (siteManager?.id || null) : null,
            isActive: ru.is_active ?? true,
          }
        })

        // Keep strictly the database users, without appending mock fixture users
        setUsers(mappedUsers)
      })
      .catch((err: any) => {
        console.warn('Could not sync users from backend database:', err)
      })
  }, [effectiveUser?.id, effectiveUser?.role])

  useEffect(() => {
    const previewUrls = evidencePreviewUrls.current

    return () => {
      previewUrls.forEach(url => URL.revokeObjectURL(url))
    }
  }, [])

  useEffect(() => {
    if (!currentUserId || currentUser) return

    try {
      sessionStorage.removeItem(SESSION_KEY)
    } catch {
      // Keep the login screen available if storage cleanup fails.
    }
  }, [currentUserId, currentUser])

  function handleNavigate(page: string) {
    if (!effectiveUser) return

    if (!getRoleConfig(effectiveUser.role).navigation.includes(page)) {
      return
    }

    setSelectedPage(page)
  }

  function handleLogin(identifier: string, password: string) {
    const normalizedIdentifier = identifier.trim().toLowerCase()

    // 1. Check local users first (for instant synchronous resolution in UI and testing)
    const localUser = users.find(
      item =>
        item.isActive &&
        (
          item.email.toLowerCase() === normalizedIdentifier ||
          item.employeeId.toLowerCase() === normalizedIdentifier
        ),
    )

    if (localUser && localUser.password === password) {
      try {
        sessionStorage.setItem(SESSION_KEY, localUser.id)
      } catch {}
      setLoginError('')
      setPreviewUserId(null)
      setApiUser(localUser)
      setCurrentUserId(localUser.id)
      setSelectedPage(getDefaultPage(localUser))

      // Trigger backend token acquisition in background if backend is online
      const backendEmail = localUser.email.endsWith('.demo') ? 'admin@sitesense.io' : localUser.email
      loginApi(backendEmail, 'SiteSense@2026').catch(() => {})
      return
    }

    if (localUser && localUser.password !== password) {
      setLoginError('Invalid email, employee ID or password.')
      return
    }

    // 2. Try live REST API for backend users
    setIsLoggingIn(true)
    setLoginError('')
    loginApi(identifier, password)
      .then(({ user }) => {
        setApiUser(user)
        setCurrentUserId(user.id)
        setPreviewUserId(null)
        setSelectedPage(getDefaultPage(user))
        setLoginError('')
        setUsers(prev => {
          const idx = prev.findIndex(u => u.email.toLowerCase() === user.email.toLowerCase() || u.id === user.id)
          if (idx >= 0) {
            const clone = [...prev]
            clone[idx] = { ...clone[idx], ...user }
            return clone
          }
          return [user, ...prev]
        })
      })
      .catch((apiErr: any) => {
        setLoginError(apiErr.message || 'Invalid email, employee ID or password.')
      })
      .finally(() => {
        setIsLoggingIn(false)
      })
  }

  function handleLogout() {
    logoutApi().catch(() => {})
    try {
      sessionStorage.removeItem(SESSION_KEY)
    } catch {}
    clearStoredSession()
    setApiUser(null)
    setCurrentUserId(null)
    setPreviewUserId(null)
    setLoginError('')
    setSelectedPage('Overview')
  }

  function handlePreviewUser(user: DemoUser) {
    if (
      currentUser?.role !== 'admin' ||
      !user.isActive ||
      user.role === 'admin'
    ) {
      return
    }

    setPreviewUserId(user.id)
    setSelectedPage(getDefaultPage(user))
  }

  function handleExitPreview() {
    setPreviewUserId(null)

    if (currentUser) {
      setSelectedPage(getDefaultPage(currentUser))
    }
  }

  async function handleSubmitTaskPhotos(
    task: InspectionRecord,
    files: File[],
    onProgress: (progress: number) => void,
  ): Promise<boolean> {
    const user = effectiveUser

    if (
      !user ||
      user.role !== 'employee' ||
      task.assignedToUserId !== user.id ||
      files.length === 0 ||
      submittingTaskIds.current.has(task.id)
    ) {
      return false
    }

    const currentTask = inspectionsRef.current.find(
      item => item.id === task.id,
    )

    if (
      !currentTask ||
      currentTask.assignedToUserId !== user.id ||
      !ACTIVE_TASK_STATUSES.includes(currentTask.status)
    ) {
      return false
    }

    submittingTaskIds.current.add(task.id)

    try {
      let uploadSuccessful = false
      const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(task.id)

      if (isUuid && getStoredAccessToken()) {
        try {
          await batchUploadMediaApi(task.id, files, onProgress)
          uploadSuccessful = true
        } catch (uploadErr) {
          console.warn('Backend media upload error, using local adapter:', uploadErr)
        }
      }

      if (!uploadSuccessful) {
        onProgress(100)
      }

      const latestTask = inspectionsRef.current.find(
        item => item.id === task.id,
      )

      if (
        !latestTask ||
        latestTask.assignedToUserId !== user.id ||
        !ACTIVE_TASK_STATUSES.includes(latestTask.status)
      ) {
        return false
      }

      const uploadedAt = new Date().toISOString()

      const newEvidence: InspectionEvidence[] = files.map(file => {
        const previewUrl = URL.createObjectURL(file)
        evidencePreviewUrls.current.push(previewUrl)

        return {
          id: createEvidenceId(),
          inspectionId: task.id,
          type: 'Photo',
          fileName: file.name,
          fileSizeLabel: formatFileSize(file.size),
          mimeType: file.type,
          uploadedByUserId: user.id,
          uploadedAt,
          previewUrl,
        }
      })

      const updatedInspections = inspectionsRef.current.map(
        inspection =>
          inspection.id === task.id
            ? {
              ...inspection,
              status: 'Completed' as const,
              reviewStatus: 'Pending' as const,
              submittedAt: uploadedAt,
              completedAt: uploadedAt,
              evidenceIds: [
                ...inspection.evidenceIds,
                ...newEvidence.map(item => item.id),
              ],
            }
            : inspection,
      )

      inspectionsRef.current = updatedInspections
      setInspections(updatedInspections)
      setEvidence(previous => [...previous, ...newEvidence])

      return true
    } catch {
      return false
    } finally {
      submittingTaskIds.current.delete(task.id)
    }
  }

  function handleAddEmployee(input: {
    name: string
    email: string
    managerId: string
  }): DemoUser | null {
    const normalizedEmail = input.email.trim().toLowerCase()

    const emailExists = users.some(
      user => user.email.toLowerCase() === normalizedEmail,
    )

    if (emailExists) return null

    const manager = users.find(
      user =>
        user.id === input.managerId &&
        user.role === 'manager' &&
        user.isActive,
    )

    if (!manager) {
      return null
    }

    const fallbackSupervisor = users.find(u => u.role === 'supervisor')
    const supervisorId = manager.supervisorId || fallbackSupervisor?.id || null
    const siteId = manager.siteId || '3591c762-1cb9-4fd4-9be0-f15ca5514c64'

    const employeeNumber = getNextNumber(users, 'employeeId', 'EMP-')
    const userNumber = getNextNumber(users, 'id', 'USER-')
    const employeeCode = String(employeeNumber || users.length + 1).padStart(3, '0')

    const initialPassword = `SiteSense@2026`

    const newEmployee: DemoUser = {
      id: `USER-${String(userNumber || users.length + 1).padStart(3, '0')}`,
      employeeId: `EMP-${employeeCode}`,
      name: input.name.trim(),
      email: normalizedEmail,
      password: initialPassword,
      role: 'employee',
      siteId: siteId,
      supervisorId: supervisorId,
      managerId: manager.id,
      isActive: true,
    }

    setUsers(previousUsers => [...previousUsers, newEmployee])

    // Persist to backend Neon PostgreSQL database via POST /api/v1/admin/users
    if (getStoredAccessToken()) {
      createAdminUserApi({
        name: newEmployee.name,
        email: newEmployee.email,
        password: initialPassword,
        role: 'field', // employee ➔ field
        site_id: manager.siteId,
      })
        .then(created => {
          if (created?.id) {
            setUsers(prev =>
              prev.map(u =>
                u.email.toLowerCase() === normalizedEmail
                  ? { ...u, id: created.id }
                  : u,
              ),
            )
          }
        })
        .catch(err => {
          console.warn('Could not store new employee in backend database:', err)
        })
    }

    return newEmployee
  }

  function handleReassignEmployee(userId: string, managerId: string) {
    const manager = users.find(
      user =>
        user.id === managerId &&
        user.role === 'manager' &&
        user.isActive,
    )

    if (!manager || !manager.supervisorId || !manager.siteId) {
      return
    }

    setUsers(previousUsers =>
      previousUsers.map(user =>
        user.id === userId &&
          user.role === 'employee' &&
          user.isActive
          ? {
            ...user,
            managerId: manager.id,
            supervisorId: manager.supervisorId,
            siteId: manager.siteId,
          }
          : user,
      ),
    )

    if (getStoredAccessToken()) {
      updateAdminUserApi(userId, { site_id: manager.siteId }).catch(err => {
        console.warn('Backend reassign error:', err)
      })
    }
  }

  function handleDeactivateEmployee(userId: string) {
    if (previewUserId === userId) {
      setPreviewUserId(null)
      setSelectedPage('Overview')
    }

    if (currentUserId === userId) {
      handleLogout()
    }

    setUsers(previousUsers =>
      previousUsers.map(user =>
        user.id === userId && user.role === 'employee'
          ? { ...user, isActive: false }
          : user,
      ),
    )

    if (getStoredAccessToken()) {
      updateAdminUserApi(userId, { is_active: false }).catch(err => {
        console.warn('Backend deactivate error:', err)
      })
    }
  }

  function renderDashboard(user: DemoUser) {
    if (
      activePage === 'Sites & Zones' &&
      ['admin', 'supervisor'].includes(user.role)
    ) {
      return <SitesZonesPage currentUser={user} />
    }
    if (
      activePage === 'Team' &&
      currentUser?.role === 'admin' &&
      !previewUser
    ) {
      return (
        <TeamManagement
          users={users}
          onAddEmployee={handleAddEmployee}
          onReassignEmployee={handleReassignEmployee}
          onDeactivateEmployee={handleDeactivateEmployee}
          onPreviewUser={handlePreviewUser}
        />
      )
    }

    if (activePage === 'Search') {
      return <EmployeeSearch />
    }

    if (activePage === 'My Tasks' && user.role === 'employee') {
      return (
        <MyTasks
          currentUser={user}
          inspections={inspections}
          onSubmitTaskPhotos={handleSubmitTaskPhotos}
        />
      )
    }

    if (activePage === 'Upload') {
      return (
        <UploadPage
          currentUser={user}
          inspections={inspections}
          evidence={evidence}
          onInspect={() => handleNavigate('Inspections')}
          onNavigate={handleNavigate}
          onSubmitTaskPhotos={handleSubmitTaskPhotos}
        />
      )
    }

    if (activePage === 'My History' && user.role === 'employee') {
      return (
        <MyHistory
          currentUser={user}
          inspections={inspections}
          evidence={evidence}
        />
      )
    }

    if (activePage === 'Inspections') {
      return (
        <InspectionDashboard
          currentUser={user}
          users={users}
          inspections={inspections}
          setInspections={setInspections}
          findings={findings}
          setFindings={setFindings}
          evidence={evidence}
          setEvidence={setEvidence}
          correctiveActions={correctiveActions}
          setCorrectiveActions={setCorrectiveActions}
        />
      )
    }

    if (activePage === 'Review Queue') {
      return (
        <ReviewQueue
          currentUser={user}
          users={users}
          inspections={inspections}
          setInspections={setInspections}
          evidence={evidence}
          findings={findings}
          correctiveActions={correctiveActions}
        />
      )
    }
    if (
      activePage === 'Report Viewer' &&
      ['admin', 'supervisor', 'manager'].includes(user.role)
    ) {
      return (
        <ReportViewer
          currentUser={user}
          users={users}
          inspections={inspections}
          findings={findings}
          evidence={evidence}
          correctiveActions={correctiveActions}
        />
      )
    }
    if (activePage === 'Intelligence Chat') {
      return <ChatPage />
    }

    if (
      activePage === 'Overview' ||
      activePage === 'My Dashboard'
    ) {
      switch (user.role) {
        case 'admin':
          return <Overview inspections={inspections} />

        case 'supervisor':
          return (
            <SupervisorDashboard
              currentUser={user}
              users={users}
            />
          )

        case 'manager':
          return (
            <ManagerDashboard
              currentUser={user}
              users={users}
            />
          )

        case 'employee':
          return (
            <EmployeeDashboard
              currentUser={user}
              inspections={inspections}
              onNavigate={handleNavigate}
            />
          )
      }
    }

    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white text-center">
        <h2 className="text-xl font-semibold text-slate-800">
          {activePage}
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          This workspace module is coming soon.
        </p>
      </div>
    )
  }

  if (!currentUser || !effectiveUser) {
    return (
      <Login
        onLogin={handleLogin}
        error={loginError}
        isLoading={isLoggingIn}
      />
    )
  }

  return (
    <AppLayout
      activePage={activePage}
      onNavigate={handleNavigate}
      currentUser={effectiveUser}
      actualUser={currentUser}
      isPreviewMode={Boolean(previewUser)}
      onExitPreview={handleExitPreview}
      onLogout={handleLogout}
    >
      {renderDashboard(effectiveUser)}
    </AppLayout>
  )
}

export default function App() {
  return <AppContent />
}
