
export type ProductRecord = {
    id: string
    name: string
    sku: string
    barcode: string
    category: string
    description: string
    location: string
    status: 'Available' | 'Low Stock' | 'Out of Stock'
}

export type PolicyRecord = {
    id: string
    title: string
    category: string
    reference: string
    summary: string
    lastUpdated: string
}

export const DEMO_PRODUCTS: ProductRecord[] = [
    {
        id: 'PROD-001',
        name: 'Industrial Safety Helmet',
        sku: 'SAFE-HELM-001',
        barcode: '8901000000011',
        category: 'Safety Equipment',
        description: 'Protective helmet for warehouse and industrial operations.',
        location: 'North Warehouse',
        status: 'Available',
    },
    {
        id: 'PROD-002',
        name: 'High Visibility Safety Vest',
        sku: 'SAFE-VEST-002',
        barcode: '8901000000028',
        category: 'Safety Equipment',
        description: 'Reflective high-visibility vest for site personnel.',
        location: 'South Warehouse',
        status: 'Low Stock',
    },
    {
        id: 'PROD-003',
        name: 'Industrial Safety Gloves',
        sku: 'SAFE-GLOVE-003',
        barcode: '8901000000035',
        category: 'Personal Protective Equipment',
        description: 'Protective gloves for routine material handling.',
        location: 'Central Distribution Centre',
        status: 'Available',
    },
    {
        id: 'PROD-004',
        name: 'Fire Extinguisher 5kg',
        sku: 'FIRE-EXT-004',
        barcode: '8901000000042',
        category: 'Fire Safety',
        description: 'Portable fire extinguisher for designated safety zones.',
        location: 'North Warehouse',
        status: 'Available',
    },
    {
        id: 'PROD-005',
        name: 'First Aid Kit',
        sku: 'MED-KIT-005',
        barcode: '8901000000059',
        category: 'Medical Supplies',
        description: 'Workplace first aid kit for minor emergencies.',
        location: 'South Warehouse',
        status: 'Out of Stock',
    },
    {
        id: 'PROD-006',
        name: 'Safety Inspection Checklist',
        sku: 'DOC-CHECK-006',
        barcode: '8901000000066',
        category: 'Inspection Materials',
        description: 'Standard checklist used during routine site inspections.',
        location: 'Central Distribution Centre',
        status: 'Available',
    },
]

export const DEMO_POLICIES: PolicyRecord[] = [
    {
        id: 'POL-001',
        title: 'Workplace Health and Safety Policy',
        category: 'Health & Safety',
        reference: 'HSE-POL-001',
        summary: 'Defines employee responsibilities, workplace hazards, protective equipment and general safety requirements.',
        lastUpdated: '15 October 2026',
    },
    {
        id: 'POL-002',
        title: 'Personal Protective Equipment Policy',
        category: 'Safety Equipment',
        reference: 'HSE-POL-002',
        summary: 'Explains when PPE is required, how it must be used and how damaged equipment should be reported.',
        lastUpdated: '10 October 2026',
    },
    {
        id: 'POL-003',
        title: 'Warehouse Fire Safety Procedure',
        category: 'Fire Safety',
        reference: 'FIRE-SOP-003',
        summary: 'Covers fire prevention, extinguisher access, emergency alarms and evacuation procedures.',
        lastUpdated: '8 October 2026',
    },
    {
        id: 'POL-004',
        title: 'Incident Reporting Procedure',
        category: 'Incident Management',
        reference: 'OPS-SOP-004',
        summary: 'Describes how employees must report workplace incidents, near misses and unsafe conditions.',
        lastUpdated: '5 October 2026',
    },
    {
        id: 'POL-005',
        title: 'Equipment Inspection Guidelines',
        category: 'Equipment',
        reference: 'OPS-POL-005',
        summary: 'Lists inspection responsibilities, documentation requirements and escalation procedures for faulty equipment.',
        lastUpdated: '1 October 2026',
    },
]
