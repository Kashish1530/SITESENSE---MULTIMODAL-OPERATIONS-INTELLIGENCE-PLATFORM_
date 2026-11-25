/**
 * SiteSense API Client and Integration Layer
 * Connects frontend UI to FastAPI backend running on http://localhost:8000/api/v1
 */

import type { DemoRole } from '../data/roles'
import type { DemoUser, DemoSite } from '../data/users'

export const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

const ACCESS_TOKEN_KEY = 'sitesense_access_token'
const REFRESH_TOKEN_KEY = 'sitesense_refresh_token'
const AUTH_USER_KEY = 'sitesense_auth_user'

export type BackendRole = 'admin' | 'manager' | 'field' | 'reviewer'
export type FrontendRole = 'admin' | 'manager' | 'employee' | 'supervisor'

/**
 * Role Mapper:
 * employee   <-> field
 * supervisor <-> reviewer
 * manager    <-> manager
 * admin      <-> admin
 */
export function toFrontendRole(backendRole: string): DemoRole {
  const normalized = (backendRole || '').trim().toLowerCase()
  switch (normalized) {
    case 'field':
      return 'employee'
    case 'reviewer':
      return 'supervisor'
    case 'manager':
      return 'manager'
    case 'admin':
      return 'admin'
    default:
      return 'employee'
  }
}

export function toBackendRole(frontendRole: string): BackendRole {
  const normalized = (frontendRole || '').trim().toLowerCase()
  switch (normalized) {
    case 'employee':
      return 'field'
    case 'supervisor':
      return 'reviewer'
    case 'manager':
      return 'manager'
    case 'admin':
      return 'admin'
    default:
      return 'field'
  }
}

export function getStoredAccessToken(): string | null {
  try {
    return (
      sessionStorage.getItem(ACCESS_TOKEN_KEY) ||
      localStorage.getItem(ACCESS_TOKEN_KEY)
    )
  } catch {
    return null
  }
}

export function getStoredRefreshToken(): string | null {
  try {
    return (
      sessionStorage.getItem(REFRESH_TOKEN_KEY) ||
      localStorage.getItem(REFRESH_TOKEN_KEY)
    )
  } catch {
    return null
  }
}

export function getStoredAuthUser(): DemoUser | null {
  try {
    const raw =
      sessionStorage.getItem(AUTH_USER_KEY) ||
      localStorage.getItem(AUTH_USER_KEY)
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function setStoredSession(
  accessToken: string,
  refreshToken: string,
  user: DemoUser,
) {
  try {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
    sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
    sessionStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
    // Also mirror to localStorage for reliability
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
  } catch {
    // Storage quota or restriction fallback
  }
}

export function clearStoredSession() {
  try {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY)
    sessionStorage.removeItem(REFRESH_TOKEN_KEY)
    sessionStorage.removeItem(AUTH_USER_KEY)
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(AUTH_USER_KEY)
  } catch {
    // ignore
  }
}

export interface ApiError {
  code: string
  message: string
  detail?: any
}

export class ApiException extends Error {
  code: string
  detail?: any
  status: number

  constructor(status: number, message: string, code = 'API_ERROR', detail?: any) {
    super(message)
    this.name = 'ApiException'
    this.status = status
    this.code = code
    this.detail = detail
  }
}

/**
 * Standard fetch wrapper handling Bearer token and JSON responses
 */
export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getStoredAccessToken()
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`

  const headers = new Headers(options.headers || {})
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  // If body is not FormData, default to application/json
  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has('Content-Type')
  ) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  // Handle 401 Unauthorized token refresh attempt if refresh token available
  if (response.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
    const refreshToken = getStoredRefreshToken()
    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })
        if (refreshRes.ok) {
          const tokenData = await refreshRes.json()
          const newAccessToken = tokenData.access_token || tokenData.token
          const newRefreshToken = tokenData.refresh_token
          const currentUser = getStoredAuthUser()
          if (currentUser) {
            setStoredSession(newAccessToken, newRefreshToken, currentUser)
          }
          headers.set('Authorization', `Bearer ${newAccessToken}`)
          const retryRes = await fetch(url, {
            ...options,
            headers,
          })
          if (retryRes.ok) {
            return (await retryRes.json()) as T
          }
        }
      } catch {
        // Fall through to error
      }
    }
  }

  if (!response.ok) {
    let errorCode = 'HTTP_ERROR'
    let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`
    let errorDetail: any = null

    try {
      const data = await response.json()
      if (data?.error) {
        errorCode = data.error.code || errorCode
        errorMessage = data.error.message || errorMessage
        errorDetail = data.error.detail
      } else if (data?.detail) {
        errorMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
        errorDetail = data.detail
      }
    } catch {
      // Non-JSON response
    }

    throw new ApiException(response.status, errorMessage, errorCode, errorDetail)
  }

  // Check if response has content
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return (await response.json()) as T
  }
  return (await response.text()) as unknown as T
}

// ==========================================
// AUTH API
// ==========================================

export async function loginApi(
  identifier: string,
  password: string,
): Promise<{ user: DemoUser; token: string }> {
  const payload = {
    email: identifier.trim(),
    password: password.trim(),
  }

  const data = await apiFetch<{
    token: string
    access_token: string
    refresh_token: string
    user: {
      id: string
      name: string
      email: string
      role: string
    }
  }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

  const frontendRole = toFrontendRole(data.user.role)
  const mappedUser: DemoUser = {
    id: data.user.id,
    employeeId: `EMP-${data.user.id.slice(0, 6).toUpperCase()}`,
    name: data.user.name,
    email: data.user.email,
    password: '',
    role: frontendRole,
    siteId: null,
    supervisorId: null,
    managerId: null,
    isActive: true,
  }

  setStoredSession(data.access_token || data.token, data.refresh_token, mappedUser)
  return { user: mappedUser, token: data.access_token || data.token }
}

export async function logoutApi(): Promise<void> {
  try {
    await apiFetch('/auth/logout', { method: 'POST' })
  } catch {
    // Ignore backend failure on logout
  } finally {
    clearStoredSession()
  }
}

export async function getCurrentUserApi(): Promise<DemoUser | null> {
  try {
    const data = await apiFetch<{
      id: string
      name: string
      email: string
      role: string
      sites?: Array<{ id: string; name: string }>
    }>('/auth/me')

    const frontendRole = toFrontendRole(data.role)
    const stored = getStoredAuthUser()
    const mappedUser: DemoUser = {
      id: data.id,
      employeeId: stored?.employeeId || `EMP-${data.id.slice(0, 6).toUpperCase()}`,
      name: data.name,
      email: data.email,
      password: '',
      role: frontendRole,
      siteId: data.sites?.[0]?.id || stored?.siteId || null,
      supervisorId: stored?.supervisorId || null,
      managerId: stored?.managerId || null,
      isActive: true,
    }
    return mappedUser
  } catch {
    return null
  }
}

// ==========================================
// SITES API
// ==========================================

export interface ApiSite {
  id: string
  name: string
  type: string
  location: string
  active: boolean
  total_inspections?: number
}

export async function getSitesApi(): Promise<DemoSite[]> {
  const data = await apiFetch<any>('/sites')
  const list: ApiSite[] = Array.isArray(data) ? data : (data?.items || [])
  return list.map(s => ({
    id: s.id,
    name: s.name,
    region: s.location || '',
    type: s.type,
    location: s.location,
    active: s.active,
  }))
}

export async function createSiteApi(payload: {
  name: string
  type: string
  location: string
  active?: boolean
}): Promise<DemoSite> {
  const s = await apiFetch<ApiSite>('/sites', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  return {
    id: s.id,
    name: s.name,
    region: s.location || '',
    type: s.type,
    location: s.location,
    active: s.active,
  }
}

// ==========================================
// INSPECTIONS API
// ==========================================

export interface BackendInspectionItem {
  id: string
  site_id: string
  site_name?: string
  user_id?: string
  status: string
  job_id?: string
  pass_rate?: number
  created_at: string
}

export async function getInspectionsApi(siteId?: string): Promise<BackendInspectionItem[]> {
  const query = siteId ? `?site_id=${siteId}` : ''
  const data = await apiFetch<any>(`/inspections${query}`)
  return Array.isArray(data) ? data : (data?.items || [])
}

export async function getInspectionDetailApi(id: string): Promise<any> {
  return await apiFetch<any>(`/inspections/${id}`)
}

export async function createInspectionApi(
  siteId: string,
  summary?: string,
): Promise<BackendInspectionItem> {
  return await apiFetch<BackendInspectionItem>('/inspections', {
    method: 'POST',
    body: JSON.stringify({ site_id: siteId, summary }),
  })
}

// ==========================================
// MEDIA & UPLOAD API
// ==========================================

export async function uploadMediaFileApi(
  inspectionId: string,
  file: File,
  onProgress?: (progress: number) => void,
): Promise<any> {
  const formData = new FormData()
  formData.append('inspection_id', inspectionId)
  formData.append('file', file, file.name)

  if (onProgress) onProgress(20)
  const result = await apiFetch<any>('/media/upload', {
    method: 'POST',
    body: formData,
  })
  if (onProgress) onProgress(100)
  return result
}

export async function batchUploadMediaApi(
  inspectionId: string,
  files: File[],
  onProgress?: (progress: number) => void,
): Promise<any> {
  const formData = new FormData()
  formData.append('inspection_id', inspectionId)
  files.forEach(f => formData.append('files', f, f.name))

  if (onProgress) onProgress(30)
  const result = await apiFetch<any>('/media/batch-upload', {
    method: 'POST',
    body: formData,
  })
  if (onProgress) onProgress(100)
  return result
}

// ==========================================
// REVIEWS API
// ==========================================

export interface BackendReviewQueueItem {
  id: string
  item_type: string
  inspection_id?: string
  site_id?: string
  title: string
  description?: string
  severity?: string
  confidence_score?: number
  original_payload?: any
  flagged_reason: string
  created_at?: string
}

export async function getReviewQueueApi(siteId?: string): Promise<BackendReviewQueueItem[]> {
  const query = siteId ? `?site_id=${siteId}` : ''
  const data = await apiFetch<any>(`/reviews/queue${query}`)
  return Array.isArray(data) ? data : (data?.items || [])
}

export async function submitReviewDecisionApi(
  itemId: string,
  action: 'accepted' | 'corrected' | 'rejected',
  reviewerNotes?: string,
  correctedValue?: any,
  itemType = 'finding',
): Promise<any> {
  return await apiFetch<any>('/reviews', {
    method: 'POST',
    body: JSON.stringify({
      item_type: itemType,
      item_id: itemId,
      action,
      reviewer_notes: reviewerNotes,
      corrected_value: correctedValue,
      original_value: {},
    }),
  })
}

// ==========================================
// CHAT API
// ==========================================

export async function createChatSessionApi(
  title?: string,
  siteId?: string,
): Promise<{ id: string; title: string }> {
  return await apiFetch<{ id: string; title: string }>('/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({
      title: title || 'New Conversation',
      site_id: siteId || undefined,
    }),
  })
}

export async function sendChatMessageApi(
  sessionId: string,
  content: string,
  attachedMediaId?: string,
  attachments?: Array<{
    id?: string
    name: string
    type: string
    size?: number
    preview_url?: string
    storage_path?: string
  }>,
): Promise<{
  session_id: string
  assistant_message: {
    id: string
    role: string
    content: string
    citations?: any[]
  }
  route?: string
  citations: any[]
}> {
  return await apiFetch<any>(`/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({
      content,
      attached_media_id: attachedMediaId,
      attachments: attachments && attachments.length > 0 ? attachments : undefined,
    }),
  })
}

export async function uploadChatAttachmentApi(
  file: File,
  sessionId?: string,
): Promise<{
  id: string
  name: string
  type: string
  mime_type: string
  size: number
  path: string
  download_url: string
}> {
  const formData = new FormData()
  formData.append('file', file)
  if (sessionId) {
    formData.append('session_id', sessionId)
  }
  return await apiFetch<any>('/chat/upload-attachment', {
    method: 'POST',
    body: formData,
  })
}

// ==========================================
// REPORTS API
// ==========================================

export async function generateReportApi(
  inspectionId: string,
  format = 'pdf',
  summary?: string,
): Promise<any> {
  return await apiFetch<any>('/reports/generate', {
    method: 'POST',
    body: JSON.stringify({
      inspection_id: inspectionId,
      format,
      summary,
    }),
  })
}

export function getReportDownloadUrl(reportId: string): string {
  const token = getStoredAccessToken()
  return `${API_BASE_URL}/reports/${reportId}/download?token=${encodeURIComponent(token || '')}`
}

// ==========================================
// ADMIN USER MANAGEMENT API
// ==========================================

export interface CreateAdminUserInput {
  name: string
  email: string
  password?: string
  role?: string
  site_id?: string | null
}

export async function createAdminUserApi(input: CreateAdminUserInput): Promise<any> {
  const backendRole = input.role ? toBackendRole(input.role as any) : 'field'
  const isUuid = input.site_id && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(input.site_id)

  return await apiFetch<any>('/admin/users', {
    method: 'POST',
    body: JSON.stringify({
      name: input.name.trim(),
      email: input.email.trim().toLowerCase(),
      password: input.password || 'SiteSense@2026',
      role: backendRole,
      site_id: isUuid ? input.site_id : undefined,
    }),
  })
}

export async function getAdminUsersApi(): Promise<any[]> {
  const data = await apiFetch<any>('/admin/users')
  return Array.isArray(data) ? data : (data?.items || [])
}

export async function getUsersDirectoryApi(): Promise<any[]> {
  const data = await apiFetch<any>('/admin/directory')
  return Array.isArray(data) ? data : (data?.items || [])
}

export async function getAdminStatsApi(): Promise<{
  total_users: number
  total_sites: number
  total_inspections: number
  total_findings: number
  total_tickets: number
  pass_rate: number
}> {
  return await apiFetch<any>('/admin/stats')
}

export async function getFindingsApi(inspectionId?: string): Promise<any[]> {
  const query = inspectionId ? `?inspection_id=${inspectionId}` : ''
  const data = await apiFetch<any>(`/findings${query}`)
  return Array.isArray(data) ? data : (data?.items || [])
}

export async function getTicketsApi(inspectionId?: string): Promise<any[]> {
  const query = inspectionId ? `?inspection_id=${inspectionId}` : ''
  const data = await apiFetch<any>(`/tickets${query}`)
  return Array.isArray(data) ? data : (data?.items || [])
}

export async function getReportsApi(inspectionId?: string): Promise<any[]> {
  const query = inspectionId ? `?inspection_id=${inspectionId}` : ''
  const data = await apiFetch<any>(`/reports${query}`)
  return Array.isArray(data) ? data : (data?.items || [])
}

export async function getPoliciesApi(q?: string): Promise<any[]> {
  const query = q ? `?q=${encodeURIComponent(q)}` : ''
  const data = await apiFetch<any>(`/policies${query}`)
  return Array.isArray(data) ? data : (data?.items || [])
}

export async function getRulesApi(): Promise<any[]> {
  const data = await apiFetch<any>('/rules')
  return Array.isArray(data) ? data : (data?.items || [])
}

export async function getZonesApi(siteId: string): Promise<{
  site_id: string
  zones: any[]
  lines: any[]
}> {
  return await apiFetch<any>(`/zones?site_id=${encodeURIComponent(siteId)}`)
}

export async function saveZoneApi(payload: {
  site_id: string
  camera_id?: string
  name: string
  zone_type: 'polygon' | 'counting_line'
  coordinates: number[][]
  applicable_classes?: string[]
  rules_config?: Record<string, any>
  is_active?: boolean
}): Promise<any> {
  return await apiFetch<any>('/zones', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function runInspectionDetectionApi(
  inspectionId: string,
  confidenceThreshold = 0.25,
): Promise<any> {
  return await apiFetch<any>(`/inspections/${inspectionId}/detect`, {
    method: 'POST',
    body: JSON.stringify({ confidence_threshold: confidenceThreshold }),
  })
}

export async function getReviewHistoryApi(): Promise<any[]> {
  const data = await apiFetch<any>('/reviews/history')
  return Array.isArray(data) ? data : (data?.items || [])
}

export async function updateAdminUserApi(
  userId: string,
  payload: { is_active?: boolean; role?: string; site_id?: string },
): Promise<any> {
  const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(userId)
  if (!isUuid) return null

  return await apiFetch<any>(`/admin/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}
