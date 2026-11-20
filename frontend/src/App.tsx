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
import TaskUpload from './components/inspections/TaskUpload'
import MyHistory from './components/inspections/MyHistory'
import ReviewQueue from './components/inspections/ReviewQueue'
import ChatPage from './components/chat/ChatPage'
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
  createTaskPhotoFormData,
  mockTaskPhotoUpload,
  formatFileSize,
} from './inspections/taskPhotoAdapter'

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

  const [currentUserId, setCurrentUserId] =
    useState<string | null>(getInitialUserId)

  const currentUser = currentUserId
    ? users.find(
      user => user.id === currentUserId && user.isActive,
    ) ?? null
    : null

  const [previewUserId, setPreviewUserId] = useState<string | null>(null)
  const [loginError, setLoginError] = useState('')
  const [selectedPage, setSelectedPage] = useState('Overview')

  const previewUser = previewUserId
    ? users.find(
      user => user.id === previewUserId && user.isActive,
    ) ?? null
    : null

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

    const user = users.find(
      item =>
        item.isActive &&
        (
          item.email.toLowerCase() === normalizedIdentifier ||
          item.employeeId.toLowerCase() === normalizedIdentifier
        ),
    )

    if (!user || user.password !== password) {
      setLoginError('Invalid email, employee ID or password.')
      return
    }

    try {
      sessionStorage.setItem(SESSION_KEY, user.id)
    } catch {
      setLoginError(
        'Unable to create a session. Please check browser settings.',
      )
      return
    }

    setLoginError('')
    setPreviewUserId(null)
    setSelectedPage(getDefaultPage(user))
    setCurrentUserId(user.id)
  }

  function handleLogout() {
    try {
      sessionStorage.removeItem(SESSION_KEY)
    } catch {
      // Return to login even if storage is unavailable.
    }

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
      const formData = createTaskPhotoFormData(task.id, files)

      const result = await mockTaskPhotoUpload(
        formData,
        onProgress,
      )

      if (result.uploadedCount !== files.length) {
        return false
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

    if (!manager || !manager.supervisorId || !manager.siteId) {
      return null
    }

    const employeeNumber = getNextNumber(users, 'employeeId', 'EMP-')
    const userNumber = getNextNumber(users, 'id', 'USER-')
    const employeeCode = String(employeeNumber).padStart(3, '0')

    const newEmployee: DemoUser = {
      id: `USER-${String(userNumber).padStart(3, '0')}`,
      employeeId: `EMP-${employeeCode}`,
      name: input.name.trim(),
      email: normalizedEmail,
      password: `SiteDemo#EMP${employeeCode}`,
      role: 'employee',
      siteId: manager.siteId,
      supervisorId: manager.supervisorId,
      managerId: manager.id,
      isActive: true,
    }

    setUsers(previousUsers => [...previousUsers, newEmployee])

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
  }

  function renderDashboard(user: DemoUser) {
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

    if (activePage === 'Upload' && user.role === 'employee') {
      return (
        <TaskUpload
          currentUser={user}
          inspections={inspections}
          evidence={evidence}
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
