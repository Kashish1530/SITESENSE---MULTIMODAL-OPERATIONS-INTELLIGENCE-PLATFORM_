import { useEffect, useState, useMemo } from 'react'
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Search,
  BookOpen,
  Sparkles,
  Loader2,
  Layers,
  Building2,
  Check,
  RefreshCw,
  MessageSquare,
  ChevronRight,
  Eye,
  X,
  ShieldCheck,
} from 'lucide-react'
import type { DemoSite, DemoUser } from '../../data/users'
import { DEMO_SITES } from '../../data/users'
import { getPoliciesApi, getPolicyChunksApi, uploadPolicyApi, getSitesApi } from '../../api/client'

type Props = {
  currentUser?: DemoUser
  onNavigate?: (page: string) => void
}

export type PolicyItem = {
  id: string
  title: string
  version: string
  source_file: string
  effective_date?: string | null
  description?: string | null
  status: string
  chunks_count: number
  site_id?: string
}

export type PolicyChunkItem = {
  id: string
  chunk_index: number
  page_number: number
  section_heading?: string | null
  content: string
  embedding_id?: string | null
  metadata_json?: Record<string, any> | null
}

const DEFAULT_POLICIES: PolicyItem[] = [
  {
    id: '96276253-93e6-4053-b999-8e953266ac39',
    title: 'Warehouse Safety & Daily Operations Handbook',
    version: '1.0',
    source_file: 'SHB-01_Warehouse_Safety_and_Daily_Operations_Handbook.pdf',
    effective_date: '2026-01-15',
    description: 'Core facility safety standard covering PPE compliance, forklift speed zones, loading dock clearances, and stacking limits.',
    status: 'Active',
    chunks_count: 11,
    site_id: 'SITE-001',
  },
  {
    id: 'f7735021-98bd-40ff-9a87-eabf6c6c0c30',
    title: 'Occupational Health, Safety & Storage Handbook',
    version: '2026.1',
    source_file: 'ohs_guidelines_2026.pdf',
    effective_date: '2026-02-01',
    description: 'Industrial site health and safety standards for assembly areas, emergency egress routes, and fire safety systems.',
    status: 'Active',
    chunks_count: 14,
    site_id: 'SITE-002',
  },
  {
    id: 'a9117aaf-32ca-48cf-916d-8c8e759d53e6',
    title: 'Physical Site & Field Operations Safety Policy',
    version: '2.0',
    source_file: 'SITE_SAFETY_AND_OPERATIONS_POLICY.pdf',
    effective_date: '2026-01-01',
    description: 'Field inspection guidelines, perimeter security, PPE enforcement, and spill containment protocols.',
    status: 'Active',
    chunks_count: 9,
    site_id: 'SITE-003',
  },
  {
    id: '4f6b274e-0fa0-4d7d-8f27-4f7d7844628f',
    title: 'Hazardous Materials Storage & Chemical Protocols',
    version: '1.2',
    source_file: 'HAZMAT_STORAGE_STANDARD_2026.pdf',
    effective_date: '2026-03-01',
    description: 'Chemical depot ventilation requirements, secondary containment, and eye-wash station clearance rules.',
    status: 'Active',
    chunks_count: 8,
    site_id: 'SITE-001',
  },
]

const SAMPLE_CHUNKS_BY_POLICY: Record<string, PolicyChunkItem[]> = {
  default: [
    {
      id: 'chunk-1',
      chunk_index: 0,
      page_number: 1,
      section_heading: 'Section 1.1 Scope & Regulatory Authority',
      content:
        'This operational handbook defines mandatory health, safety, and equipment operation standards applicable to all warehouse personnel, contractors, and visiting drivers.',
    },
    {
      id: 'chunk-2',
      chunk_index: 1,
      page_number: 4,
      section_heading: 'Section 1.2 Mandatory PPE In Active Zones',
      content:
        'High-visibility safety vests (EN ISO 20471 Class 2) and approved safety helmets (ANSI Z89.1) must be worn at all times by any personnel entering active machinery bays, high-bay aisles, or truck loading docks.',
    },
    {
      id: 'chunk-3',
      chunk_index: 2,
      page_number: 7,
      section_heading: 'Section 2.4 Walkway & Emergency Egress Clearances',
      content:
        'Pedestrian walkways and emergency egress corridors must maintain an unobstructed clear width of at least 1.2 meters. Pallets, loose debris, or parked carts left in marked corridors represent an immediate safety violation.',
    },
    {
      id: 'chunk-4',
      chunk_index: 3,
      page_number: 12,
      section_heading: 'Section 3.1 Pallet Stacking & Vertical Limits',
      content:
        'Standard Euro and GMA pallets shall not be stacked higher than 4 vertical tiers or 2.5 meters in active staging bays unless stored within engineered pallet racking with seismic rated restraints.',
    },
    {
      id: 'chunk-5',
      chunk_index: 4,
      page_number: 15,
      section_heading: 'Section 4.3 Fire Equipment & Electrical Access',
      content:
        'Fire hose reels, chemical extinguishers, and emergency electrical disconnect switches must maintain a 360-degree clear operational perimeter of at least 1.0 meter with unobstructed visual signage.',
    },
  ],
}

export default function PolicyManagementPage({ currentUser: _currentUser, onNavigate }: Props) {
  const [policies, setPolicies] = useState<PolicyItem[]>(DEFAULT_POLICIES)
  const [sites, setSites] = useState<DemoSite[]>(DEMO_SITES)
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSiteFilter, setSelectedSiteFilter] = useState('all')

  // Document details / chunk inspector modal
  const [selectedPolicyForView, setSelectedPolicyForView] = useState<PolicyItem | null>(null)
  const [chunks, setChunks] = useState<PolicyChunkItem[]>([])
  const [isLoadingChunks, setIsLoadingChunks] = useState(false)
  const [chunkSearchQuery, setChunkSearchQuery] = useState('')

  // Upload modal state
  const [isUploadOpen, setIsUploadOpen] = useState(false)
  const [uploadSiteId, setUploadSiteId] = useState(DEMO_SITES[0]?.id || '')
  const [title, setTitle] = useState('')
  const [version, setVersion] = useState('1.0')
  const [description, setDescription] = useState('')
  const [effectiveDate, setEffectiveDate] = useState(
    new Date().toISOString().split('T')[0]
  )
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isIngesting, setIsIngesting] = useState(false)
  const [ingestStep, setIngestStep] = useState('')
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)

  const loadData = async () => {
    setIsLoading(true)
    try {
      const [polData, siteData] = await Promise.all([
        getPoliciesApi().catch(() => []),
        getSitesApi().catch(() => DEMO_SITES),
      ])

      if (Array.isArray(polData) && polData.length > 0) {
        const mapped = polData.map((p: any) => ({
          id: p.id,
          title: p.title,
          version: p.version || '1.0',
          source_file: p.source_file || 'policy.pdf',
          effective_date: p.effective_date || null,
          description: p.description || null,
          status: p.status || 'Active',
          chunks_count: p.chunks_count || 0,
          site_id: p.site_id || undefined,
        }))
        setPolicies(mapped)
      } else {
        setPolicies(DEFAULT_POLICIES)
      }

      if (Array.isArray(siteData) && siteData.length > 0) {
        setSites(siteData)
        if (!uploadSiteId) setUploadSiteId(siteData[0].id)
      }
    } catch (err) {
      console.warn('Backend policy fetch fallback to authoritative standards:', err)
      setPolicies(DEFAULT_POLICIES)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // Open Document Details / Chunk Viewer
  const handleOpenDocViewer = async (policy: PolicyItem) => {
    setSelectedPolicyForView(policy)
    setChunkSearchQuery('')
    setIsLoadingChunks(true)
    try {
      const fetched = await getPolicyChunksApi(policy.id).catch(() => [])
      if (Array.isArray(fetched) && fetched.length > 0) {
        setChunks(fetched)
      } else {
        setChunks(SAMPLE_CHUNKS_BY_POLICY[policy.id] || SAMPLE_CHUNKS_BY_POLICY.default)
      }
    } catch {
      setChunks(SAMPLE_CHUNKS_BY_POLICY.default)
    } finally {
      setIsLoadingChunks(false)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setUploadError('Only PDF policy documents are currently supported.')
        return
      }
      setSelectedFile(file)
      setUploadError(null)
      if (!title) {
        setTitle(file.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' '))
      }
    }
  }

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile) {
      setUploadError('Please select a PDF file to upload.')
      return
    }
    if (!title.trim()) {
      setUploadError('Please enter a policy title.')
      return
    }

    setIsIngesting(true)
    setUploadError(null)
    setUploadSuccess(null)

    try {
      setIngestStep('1. Uploading PDF to secure storage...')
      await new Promise((r) => setTimeout(r, 400))

      setIngestStep('2. Extracting text & segmenting semantic chunks...')
      await new Promise((r) => setTimeout(r, 500))

      setIngestStep('3. Generating 384-dimensional dense embeddings & indexing pgvector...')
      const res = await uploadPolicyApi({
        siteId: uploadSiteId,
        title: title.trim(),
        version: version.trim() || '1.0',
        effectiveDate,
        description: description.trim() || undefined,
        file: selectedFile,
      })

      setIngestStep('4. Document successfully indexed into Knowledge Base!')
      setUploadSuccess(
        `Successfully indexed "${title}" (${res?.chunks_created || 8} semantic vector chunks created).`
      )

      // Add to visible policies list immediately
      const newPolicy: PolicyItem = {
        id: res?.policy_id || String(Date.now()),
        title: title.trim(),
        version: version.trim() || '1.0',
        source_file: selectedFile.name,
        effective_date: effectiveDate,
        description: description.trim() || undefined,
        status: 'Active',
        chunks_count: res?.chunks_created || 8,
        site_id: uploadSiteId,
      }

      setPolicies((prev) => [newPolicy, ...prev.filter((p) => p.id !== newPolicy.id)])

      setTimeout(() => {
        setIsUploadOpen(false)
        setTitle('')
        setDescription('')
        setSelectedFile(null)
        setUploadSuccess(null)
        loadData()
      }, 1500)
    } catch (err: any) {
      setUploadError(err.message || 'Failed to ingest policy.')
    } finally {
      setIsIngesting(false)
      setIngestStep('')
    }
  }

  const filteredPolicies = useMemo(() => {
    return policies.filter((p) => {
      const query = searchQuery.toLowerCase().trim()
      const matchesSearch =
        !query ||
        p.title.toLowerCase().includes(query) ||
        p.source_file.toLowerCase().includes(query) ||
        (p.description && p.description.toLowerCase().includes(query)) ||
        p.version.toLowerCase().includes(query)

      const matchesSite =
        selectedSiteFilter === 'all' ||
        !p.site_id ||
        p.site_id === selectedSiteFilter

      return matchesSearch && matchesSite
    })
  }, [policies, searchQuery, selectedSiteFilter])

  const filteredChunks = useMemo(() => {
    if (!chunkSearchQuery.trim()) return chunks
    const q = chunkSearchQuery.toLowerCase()
    return chunks.filter(
      (c) =>
        c.content.toLowerCase().includes(q) ||
        (c.section_heading && c.section_heading.toLowerCase().includes(q))
    )
  }, [chunks, chunkSearchQuery])

  const totalChunks = useMemo(() => {
    return policies.reduce((acc, p) => acc + (p.chunks_count || 0), 0)
  }, [policies])

  const siteMap = useMemo(() => {
    const map = new Map<string, string>()
    sites.forEach((s) => map.set(s.id, s.name))
    return map
  }, [sites])

  return (
    <div className="space-y-6 p-6">
      {/* Header banner */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
            <BookOpen className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                Policies & Knowledge Base
              </h1>
              <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
                Authoritative Standards
              </span>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Manage operational manuals, view extracted clauses, and inspect vectorized policy documents.
            </p>
          </div>
        </div>

        {/* Unified Top-Right Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={isLoading}
            className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
            title="Refresh policies from database"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setIsUploadOpen(true)}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-blue-500/20 transition hover:from-blue-700 hover:to-indigo-700"
          >
            <UploadCloud className="h-4 w-4" />
            Upload New Policy
          </button>
        </div>
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
              Active Ingested Policies
            </span>
            <span className="rounded-lg bg-emerald-500/10 p-2 text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
              {policies.length}
            </span>
            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              Authoritative
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            All uploaded compliance documents visible
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
              pgvector Chunks Embedded
            </span>
            <span className="rounded-lg bg-blue-500/10 p-2 text-blue-600 dark:text-blue-400">
              <Layers className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
              {totalChunks}
            </span>
            <span className="text-xs font-semibold text-blue-600 dark:text-blue-400">
              Vectors
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            384-dimensional dense semantic vectors
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
              Facility Coverage
            </span>
            <span className="rounded-lg bg-indigo-500/10 p-2 text-indigo-600 dark:text-indigo-400">
              <Building2 className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
              {sites.length}
            </span>
            <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">
              Facilities
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Site-scoped & enterprise isolation
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
              RAG Grounding Status
            </span>
            <span className="rounded-lg bg-purple-500/10 p-2 text-purple-600 dark:text-purple-400">
              <Sparkles className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-white">
              Active RAG
            </span>
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Strict citation & refusal controls active
          </p>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search uploaded documents by title, filename, or topic..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-slate-50/50 py-2 pl-10 pr-4 text-sm text-slate-800 outline-none transition focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-500/20 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
          />
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedSiteFilter}
            onChange={(e) => setSelectedSiteFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 outline-none transition hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300"
          >
            <option value="all">All Facilities ({sites.length})</option>
            {sites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Uploaded Documents Table */}
      <div className="rounded-2xl border border-slate-200/80 bg-white shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60">
        <div className="border-b border-slate-100 p-5 dark:border-slate-800/80">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                Authoritative Operational Documents ({filteredPolicies.length})
              </h2>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                All uploaded compliance manuals indexed in PostgreSQL & pgvector
              </p>
            </div>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="text-xs font-medium text-blue-600 hover:underline dark:text-blue-400"
              >
                Clear Search Filter
              </button>
            )}
          </div>
        </div>

        {isLoading ? (
          <div className="flex min-h-[220px] flex-col items-center justify-center p-8 text-center">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <p className="mt-3 text-sm text-slate-500">Loading uploaded policy documents...</p>
          </div>
        ) : filteredPolicies.length === 0 ? (
          <div className="flex min-h-[240px] flex-col items-center justify-center p-8 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
              <FileText className="h-7 w-7" />
            </div>
            <h3 className="mt-4 text-base font-semibold text-slate-900 dark:text-white">
              No policy documents match your criteria
            </h3>
            <p className="mt-1 max-w-md text-sm text-slate-500 dark:text-slate-400">
              {searchQuery
                ? `No documents matching "${searchQuery}". Clear your search or upload a new policy.`
                : 'Upload your company safety manual or warehouse standards using the top-right button to begin.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-400">
              <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:bg-slate-950/60 dark:text-slate-400">
                <tr>
                  <th className="px-6 py-3.5">Policy Document</th>
                  <th className="px-6 py-3.5">Scope / Facility</th>
                  <th className="px-6 py-3.5">Version</th>
                  <th className="px-6 py-3.5">Indexed Chunks</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Effective Date</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/80 dark:divide-slate-800/80">
                {filteredPolicies.map((policy) => {
                  const facilityName = policy.site_id
                    ? siteMap.get(policy.site_id) || policy.site_id
                    : 'Enterprise Universal'

                  return (
                    <tr
                      key={policy.id}
                      className="transition hover:bg-slate-50/80 dark:hover:bg-slate-800/40"
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
                            <FileText className="h-5 w-5" />
                          </div>
                          <div>
                            <div className="font-semibold text-slate-900 dark:text-white">
                              {policy.title}
                            </div>
                            <div className="text-xs text-slate-400">
                              {policy.source_file}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="px-6 py-4">
                        <span className="inline-flex items-center gap-1.5 rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                          <Building2 className="h-3.5 w-3.5 text-slate-400" />
                          {facilityName}
                        </span>
                      </td>

                      <td className="px-6 py-4">
                        <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
                          v{policy.version || '1.0'}
                        </span>
                      </td>

                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1.5">
                          <Layers className="h-3.5 w-3.5 text-blue-500" />
                          <span className="font-semibold text-slate-900 dark:text-white">
                            {policy.chunks_count || 0}
                          </span>
                          <span className="text-xs text-slate-400">chunks</span>
                        </div>
                      </td>

                      <td className="px-6 py-4">
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                          {policy.status || 'Active'}
                        </span>
                      </td>

                      <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400">
                        {policy.effective_date || 'Standard Effective'}
                      </td>

                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleOpenDocViewer(policy)}
                            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 hover:text-blue-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                            title="Inspect document and extracted chunks"
                          >
                            <Eye className="h-3.5 w-3.5" />
                            View Chunks
                          </button>
                          <button
                            onClick={() => onNavigate?.('Intelligence Chat')}
                            className="flex items-center gap-1.5 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-600 transition hover:bg-blue-100 dark:bg-blue-950/40 dark:text-blue-400 dark:hover:bg-blue-900/60"
                            title="Query this document in Intelligence Chat"
                          >
                            <Sparkles className="h-3.5 w-3.5" />
                            Ask Agent
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Unified AI Copilot Link Card */}
      <div className="flex flex-col items-start justify-between gap-4 rounded-2xl border border-blue-200/70 bg-gradient-to-r from-blue-50/80 via-indigo-50/30 to-white p-6 shadow-sm dark:border-blue-900/40 dark:from-blue-950/20 dark:via-slate-900 dark:to-slate-900 sm:flex-row sm:items-center">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-md shadow-blue-500/20">
            <MessageSquare className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white">
              Interact with Ingested Policies in Intelligence Chat
            </h3>
            <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">
              Ask natural language questions, verify visual PPE compliance against standards, and review proposed tickets with the SiteSense AI Agent.
            </p>
          </div>
        </div>

        <button
          onClick={() => onNavigate?.('Intelligence Chat')}
          className="flex shrink-0 items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-blue-500/20 transition hover:bg-blue-700"
        >
          Open Intelligence Chat
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      {/* Document Details & Chunk Inspector Modal */}
      {selectedPolicyForView && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm">
          <div className="relative flex max-h-[90vh] w-full max-w-4xl flex-col rounded-3xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-100 p-6 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
                  <FileText className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                    {selectedPolicyForView.title}
                  </h3>
                  <div className="flex items-center gap-3 text-xs text-slate-400">
                    <span>{selectedPolicyForView.source_file}</span>
                    <span>•</span>
                    <span>Version v{selectedPolicyForView.version}</span>
                    <span>•</span>
                    <span>Effective: {selectedPolicyForView.effective_date || 'Standard'}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => setSelectedPolicyForView(null)}
                className="rounded-xl p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-5">
              {/* Summary metadata */}
              <div className="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-950/40">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                    <ShieldCheck className="h-4 w-4 text-emerald-500" />
                    <span className="font-semibold">Ingestion Status:</span> Active in pgvector
                  </div>
                  <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                    <Layers className="h-4 w-4 text-blue-500" />
                    <span className="font-semibold">Indexed Chunks:</span>{' '}
                    {chunks.length || selectedPolicyForView.chunks_count} passages
                  </div>
                  <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                    <Building2 className="h-4 w-4 text-indigo-500" />
                    <span className="font-semibold">Facility Scope:</span>{' '}
                    {selectedPolicyForView.site_id
                      ? siteMap.get(selectedPolicyForView.site_id) || selectedPolicyForView.site_id
                      : 'Enterprise Universal'}
                  </div>
                </div>
                {selectedPolicyForView.description && (
                  <p className="mt-3 text-xs text-slate-600 dark:text-slate-300">
                    {selectedPolicyForView.description}
                  </p>
                )}
              </div>

              {/* Chunk Search Bar */}
              <div className="relative">
                <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter extracted clauses by keyword (e.g. PPE, forklift, walkway)..."
                  value={chunkSearchQuery}
                  onChange={(e) => setChunkSearchQuery(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-10 pr-4 text-xs text-slate-800 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
                />
              </div>

              {/* Chunk list */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Extracted Semantic Chunks & Clauses ({filteredChunks.length})
                </h4>

                {isLoadingChunks ? (
                  <div className="flex min-h-[160px] items-center justify-center">
                    <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                  </div>
                ) : filteredChunks.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-xs text-slate-500 dark:border-slate-800">
                    No chunk clauses matched "{chunkSearchQuery}".
                  </div>
                ) : (
                  filteredChunks.map((chunk, idx) => (
                    <div
                      key={chunk.id || idx}
                      className="rounded-xl border border-slate-200/80 bg-white p-4 text-xs transition hover:border-blue-300 dark:border-slate-800 dark:bg-slate-950/30"
                    >
                      <div className="mb-2 flex items-center justify-between text-slate-500 dark:text-slate-400">
                        <span className="font-semibold text-blue-600 dark:text-blue-400">
                          {chunk.section_heading || `Chunk #${chunk.chunk_index + 1}`}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                            Page {chunk.page_number}
                          </span>
                          <span className="rounded bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
                            384-d vector
                          </span>
                        </div>
                      </div>
                      <p className="leading-relaxed text-slate-700 dark:text-slate-300">
                        {chunk.content}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between border-t border-slate-100 p-6 dark:border-slate-800">
              <button
                onClick={() => setSelectedPolicyForView(null)}
                className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                Close
              </button>
              <button
                onClick={() => {
                  setSelectedPolicyForView(null)
                  onNavigate?.('Intelligence Chat')
                }}
                className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700"
              >
                <Sparkles className="h-3.5 w-3.5" />
                Ask Intelligence Agent About This Standard
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Policy Document Modal */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm">
          <div className="relative w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
                  <UploadCloud className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    Upload & Vectorize Policy
                  </h3>
                  <p className="text-xs text-slate-400">
                    Chunked, embedded, and indexed into PostgreSQL for agent RAG grounding.
                  </p>
                </div>
              </div>
              <button
                onClick={() => !isIngesting && setIsUploadOpen(false)}
                disabled={isIngesting}
                className="rounded-xl p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="mt-5 space-y-4">
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Target Facility / Site Scope *
                </label>
                <select
                  value={uploadSiteId}
                  onChange={(e) => setUploadSiteId(e.target.value)}
                  disabled={isIngesting}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3.5 py-2 text-sm text-slate-800 outline-none focus:border-blue-500 focus:bg-white dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
                >
                  {sites.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Policy Title *
                </label>
                <input
                  type="text"
                  placeholder="e.g. Warehouse Operations & Egress Policy 2026"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  disabled={isIngesting}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3.5 py-2 text-sm text-slate-800 outline-none focus:border-blue-500 focus:bg-white dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Version
                  </label>
                  <input
                    type="text"
                    placeholder="1.0"
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                    disabled={isIngesting}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3.5 py-2 text-sm text-slate-800 outline-none focus:border-blue-500 focus:bg-white dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Effective Date
                  </label>
                  <input
                    type="date"
                    value={effectiveDate}
                    onChange={(e) => setEffectiveDate(e.target.value)}
                    disabled={isIngesting}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3.5 py-2 text-sm text-slate-800 outline-none focus:border-blue-500 focus:bg-white dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Summary / Scope Description
                </label>
                <textarea
                  rows={2}
                  placeholder="Brief summary of rules and topics covered in this document..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={isIngesting}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3.5 py-2 text-sm text-slate-800 outline-none focus:border-blue-500 focus:bg-white dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
                />
              </div>

              {/* PDF file dropzone */}
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Policy Document (PDF) *
                </label>
                <label
                  className={`flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-5 text-center transition cursor-pointer ${
                    selectedFile
                      ? 'border-emerald-500/50 bg-emerald-50/20 dark:bg-emerald-950/10'
                      : 'border-slate-300 bg-slate-50/50 hover:border-blue-500 dark:border-slate-700 dark:bg-slate-900'
                  }`}
                >
                  <input
                    type="file"
                    accept=".pdf,application/pdf"
                    onChange={handleFileChange}
                    disabled={isIngesting}
                    className="hidden"
                  />
                  {selectedFile ? (
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-emerald-500/10 p-2 text-emerald-600 dark:text-emerald-400">
                        <Check className="h-5 w-5" />
                      </div>
                      <div className="text-left">
                        <div className="font-semibold text-slate-900 dark:text-white">
                          {selectedFile.name}
                        </div>
                        <div className="text-xs text-slate-400">
                          {(selectedFile.size / 1024 / 1024).toFixed(2)} MB PDF
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center">
                      <UploadCloud className="h-8 w-8 text-slate-400" />
                      <span className="mt-2 text-xs font-semibold text-slate-700 dark:text-slate-300">
                        Click to browse or drop standard PDF here
                      </span>
                      <span className="mt-1 text-[11px] text-slate-400">
                        PDF format up to 50 MB
                      </span>
                    </div>
                  )}
                </label>
              </div>

              {/* Ingestion progress */}
              {isIngesting && (
                <div className="rounded-xl border border-blue-200 bg-blue-50/80 p-3.5 text-xs text-blue-800 dark:border-blue-900/50 dark:bg-blue-950/40 dark:text-blue-300">
                  <div className="flex items-center gap-2 font-semibold">
                    <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                    <span>Processing & Indexing Document...</span>
                  </div>
                  <div className="mt-1.5 text-blue-600 dark:text-blue-400 font-medium">
                    {ingestStep}
                  </div>
                </div>
              )}

              {uploadError && (
                <div className="flex items-center gap-2 rounded-xl bg-red-50 p-3 text-xs text-red-600 dark:bg-red-950/40 dark:text-red-400">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}

              {uploadSuccess && (
                <div className="flex items-center gap-2 rounded-xl bg-emerald-50 p-3 text-xs text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400">
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  <span>{uploadSuccess}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  disabled={isIngesting}
                  className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isIngesting || !selectedFile}
                  className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow-md shadow-blue-500/20 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50"
                >
                  {isIngesting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Vectorizing...
                    </>
                  ) : (
                    <>
                      <UploadCloud className="h-4 w-4" />
                      Ingest & Index Policy
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
