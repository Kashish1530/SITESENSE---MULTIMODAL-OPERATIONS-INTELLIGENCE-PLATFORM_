export interface SitePerformance {
    siteId: string
    siteName: string
    complianceScore: number
    openFindings: number
    criticalFindings: number
    activeEmployees: number
    inspectionsThisMonth: number
    trend: 'up' | 'down' | 'stable'
}

// Live database provides active performance data
export const sitePerformance: SitePerformance[] = []
