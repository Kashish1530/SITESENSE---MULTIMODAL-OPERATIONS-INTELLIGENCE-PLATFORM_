export type ProductCategory =
    | 'PPE'
    | 'Fall Protection'
    | 'Hazardous Materials'
    | 'First Aid'
    | 'Fire Safety'
    | 'Tools'

export type PolicyCategory =
    | 'Personal Protective Equipment'
    | 'Hazard Communication'
    | 'Emergency Response'
    | 'Facility Safety'
    | 'Equipment Operations'

export type ProductRecord = {
    id: string
    sku: string
    name: string
    barcode: string
    category: ProductCategory | string
    complianceStatus?: 'compliant' | 'review_required' | 'non_compliant'
    status: string
    assignedSiteId?: string
    assignedSiteName?: string
    location: string
    specifications?: string
    description: string
    standards?: string[]
    lastInspected?: string
    safetyRating?: string
    notes?: string
}

export type PolicyRecord = {
    id: string
    policyNumber?: string
    title: string
    category: PolicyCategory | string
    siteId?: string | 'all'
    siteName?: string
    version?: string
    sourceFile?: string
    effectiveDate?: string | null
    reviewDate?: string
    status?: string
    description?: string
    scope?: string
    summary: string
    reference: string
    mandatoryRequirements?: string[]
    enforcementLevel?: 'Mandatory' | 'Recommended' | 'Advisory'
    regulatoryReference?: string
    lastUpdated?: string
    chunksCount?: number
}

export type ComplianceRuleRecord = {
    id: string
    name: string
    description: string
    ruleType: string
    policyRef: string
    severity: string
    isActive: boolean
}

export const PRODUCT_CATEGORIES: ProductCategory[] = [
    'PPE',
    'Fall Protection',
    'Hazardous Materials',
    'First Aid',
    'Fire Safety',
    'Tools',
]

export const POLICY_CATEGORIES: PolicyCategory[] = [
    'Personal Protective Equipment',
    'Hazard Communication',
    'Emergency Response',
    'Facility Safety',
    'Equipment Operations',
]

// Real records are queried dynamically from the backend API
export const DEMO_PRODUCTS: ProductRecord[] = []
export const DEMO_POLICIES: PolicyRecord[] = []
