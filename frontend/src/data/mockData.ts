
export const dashboardMetrics = [
    {
        title: 'Total Inspections',
        value: '1,284',
        change: '+12.8%',
        trend: 'up',
        description: 'Compared to last month',
    },
    {
        title: 'Pass Rate',
        value: '94.2%',
        change: '+2.4%',
        trend: 'up',
        description: 'Compared to last month',
    },
    {
        title: 'Pending Reviews',
        value: '28',
        change: '8 urgent',
        trend: 'warning',
        description: 'Awaiting human review',
    },
    {
        title: 'Active Sites',
        value: '3',
        change: 'All operational',
        trend: 'neutral',
        description: 'Across 3 regions',
    },
]

export const inspectionTrend = [
    { month: 'Jun', inspections: 142 },
    { month: 'Jul', inspections: 168 },
    { month: 'Aug', inspections: 155 },
    { month: 'Sep', inspections: 190 },
    { month: 'Oct', inspections: 214 },
    { month: 'Nov', inspections: 238 },
]

export const sitePerformance = [
    {
        id: 'SITE-001',
        name: 'North Warehouse',
        region: 'North Region',
        inspections: 486,
        passRate: 95,
        pending: 8,
        status: 'Operational',
    },
    {
        id: 'SITE-002',
        name: 'South Warehouse',
        region: 'South Region',
        inspections: 392,
        passRate: 92,
        pending: 11,
        status: 'Operational',
    },
    {
        id: 'SITE-003',
        name: 'Central Distribution Centre',
        region: 'Central Region',
        inspections: 406,
        passRate: 96,
        pending: 9,
        status: 'Operational',
    },
]

export const recentInspections = [
    {
        id: 'INS-2048',
        site: 'North Warehouse',
        type: 'Safety Inspection',
        date: '18 Nov 2026',
        status: 'Passed',
    },
    {
        id: 'INS-2047',
        site: 'South Warehouse',
        type: 'Equipment Check',
        date: '18 Nov 2026',
        status: 'Review',
    },
    {
        id: 'INS-2046',
        site: 'Central Distribution Centre',
        type: 'Fire Safety',
        date: '17 Nov 2026',
        status: 'Failed',
    },
    {
        id: 'INS-2045',
        site: 'North Warehouse',
        type: 'Facility Inspection',
        date: '17 Nov 2026',
        status: 'Passed',
    },
    {
        id: 'INS-2044',
        site: 'South Warehouse',
        type: 'Storage Compliance',
        date: '16 Nov 2026',
        status: 'Review',
    },
]

export const activityFeed = [
    {
        id: 1,
        title: 'Inspection completed',
        detail: 'North Warehouse · Safety Inspection',
        time: '12 minutes ago',
        type: 'success',
    },
    {
        id: 2,
        title: 'Review required',
        detail: 'South Warehouse · 3 findings need attention',
        time: '35 minutes ago',
        type: 'warning',
    },
    {
        id: 3,
        title: 'New evidence uploaded',
        detail: 'Central Distribution Centre · 8 files',
        time: '1 hour ago',
        type: 'info',
    },
]
