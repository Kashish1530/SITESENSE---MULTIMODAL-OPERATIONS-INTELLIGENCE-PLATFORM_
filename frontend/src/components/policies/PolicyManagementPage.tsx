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
} from 'lucide-react'
import type { DemoSite, DemoUser } from '../../data/users'
import { DEMO_SITES } from '../../data/users'
import { getPoliciesApi, uploadPolicyApi, getSitesApi } from '../../api/client'

type Props = {
  currentUser: DemoUser
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

export default function PolicyManagementPage({ currentUser }: Props) {
  const [policies, setPolicies] = useState<PolicyItem[]>([])
  const [sites, setSites] = useState<DemoSite[]>(DEMO_SITES)
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSiteFilter, setSelectedSiteFilter] = useState('all')

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

  // RAG query test state
  const [testQuery, setTestQuery] = useState('')
  const [testResults, setTestResults] = useState<any[] | null>(null)
  const [isSearchingRag, setIsSearchingRag] = useState(false)

  const loadData = async () => {
    setIsLoading(true)
    try {
      const [polData, siteData] = await Promise.all([
        getPoliciesApi(),
        getSitesApi().catch(() => DEMO_SITES),
      ])
      setPolicies(polData)
      if (Array.isArray(siteData) && siteData.length > 0) {
        setSites(siteData)
        if (!uploadSiteId) setUploadSiteId(siteData[0].id)
      }
    } catch (err) {
      console.error('Failed to load policies:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

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
      await new Promise((r) => setTimeout(r, 600))

      setIngestStep('2. Extracting text & segmenting semantic chunks...')
      await new Promise((r) => setTimeout(r, 700))

      setIngestStep('3. Generating 384-dimensional dense vector embeddings...')
      await new Promise((r) => setTimeout(r, 800))

      setIngestStep('4. Persisting chunks and indexing in Neon PostgreSQL...')
      const res = await uploadPolicyApi({
        siteId: uploadSiteId,
        title: title.trim(),
        version: version.trim() || '1.0',
        effectiveDate,
        description: description.trim() || undefined,
        file: selectedFile,
      })

      setUploadSuccess(
        `Policy "${res.title || title}" successfully ingested! Created ${
          res.chunks_ingested || res.chunks_count || 'multiple'
        } vector chunks in PostgreSQL.`
      )
      setSelectedFile(null)
      setTitle('')
      setDescription('')
      await loadData()
      setTimeout(() => {
        setIsUploadOpen(false)
        setUploadSuccess(null)
      }, 2500)
    } catch (err: any) {
      setUploadError(err.message || 'Failed to ingest policy.')
    } finally {
      setIsIngesting(false)
      setIngestStep('')
    }
  }

  const handleTestSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!testQuery.trim()) return
    setIsSearchingRag(true)
    try {
      const res = await getPoliciesApi(testQuery)
      setTestResults(res)
    } catch (err) {
      console.error('RAG test error:', err)
    } finally {
      setIsSearchingRag(false)
    }
  }

  const filteredPolicies = useMemo(() => {
    return policies.filter((p) => {
      const matchesSearch =
        !searchQuery.trim() ||
        p.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.source_file?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.description?.toLowerCase().includes(searchQuery.toLowerCase())

      const matchesSite =
        selectedSiteFilter === 'all' || p.site_id === selectedSiteFilter

      return matchesSearch && matchesSite
    })
  }, [policies, searchQuery, selectedSiteFilter])

  const totalChunks = useMemo(() => {
    return policies.reduce((acc, p) => acc + (p.chunks_count || 0), 0)
  }, [policies])

  return (
    <div className="space-y-6 p-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600/10 text-blue-600 dark:bg-blue-500/20 dark:text-blue-400">
              <BookOpen className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                  Policies & Knowledge Base
                </h1>
                <span className="rounded-md bg-blue-100 px-2 py-0.5 text-xs font-semibold capitalize text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                  {currentUser.role}
                </span>
              </div>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Authoritative Operations Standards & Vectorized Policy Ingestion
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={isLoading}
            className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
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
            Dynamically loaded from database
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
            384-dimensional dense vectors
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
              Sites
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Site-scoped policy isolation
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
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Strict refusal on ungrounded queries
          </p>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search policies by title, rule topic, or filename..."
            className="w-full rounded-xl border border-slate-200 bg-slate-50/50 py-2.5 pl-10 pr-4 text-sm text-slate-900 transition focus:border-blue-500 focus:bg-white focus:outline-none dark:border-slate-800 dark:bg-slate-950 dark:text-white dark:focus:border-blue-500"
          />
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedSiteFilter}
            onChange={(e) => setSelectedSiteFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-700 transition focus:border-blue-500 focus:outline-none dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300"
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

      {/* Policies Table List */}
      <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-sm dark:border-slate-800/90 dark:bg-slate-900/80">
        <div className="border-b border-slate-200/80 px-6 py-4 dark:border-slate-800/80">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">
            Authoritative Operational Policies ({filteredPolicies.length})
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Uploaded compliance documents indexed in PostgreSQL
          </p>
        </div>

        {isLoading ? (
          <div className="flex min-h-[250px] items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : filteredPolicies.length === 0 ? (
          <div className="flex min-h-[250px] flex-col items-center justify-center p-8 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
              <FileText className="h-7 w-7" />
            </div>
            <h3 className="mt-4 text-base font-semibold text-slate-900 dark:text-white">
              No policy documents found
            </h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Upload your company operations safety manual or warehouse standards to begin.
            </p>
            <button
              onClick={() => setIsUploadOpen(true)}
              className="mt-4 flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
            >
              <UploadCloud className="h-4 w-4" />
              Upload Policy Document
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-400">
              <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:bg-slate-950/60 dark:text-slate-400">
                <tr>
                  <th className="px-6 py-3.5">Policy Document</th>
                  <th className="px-6 py-3.5">Version</th>
                  <th className="px-6 py-3.5">Ingested Chunks</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Effective Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/80 dark:divide-slate-800/80">
                {filteredPolicies.map((policy) => (
                  <tr
                    key={policy.id}
                    className="transition hover:bg-slate-50/80 dark:hover:bg-slate-800/40"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
                          <FileText className="h-5 w-5" />
                        </div>
                        <div>
                          <div className="font-semibold text-slate-900 dark:text-white">
                            {policy.title}
                          </div>
                          <div className="text-xs text-slate-400">
                            {policy.source_file || 'Document PDF'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                        v{policy.version || '1.0'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5">
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Live RAG Test Console Section */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm dark:border-slate-800/90 dark:bg-slate-900/80">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-50 text-purple-600 dark:bg-purple-950/40 dark:text-purple-400">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">
              Live Policy Retrieval & Refusal Console
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Test semantic hybrid retrieval against your uploaded database chunks
            </p>
          </div>
        </div>

        <form onSubmit={handleTestSearch} className="mt-4 flex gap-3">
          <input
            type="text"
            value={testQuery}
            onChange={(e) => setTestQuery(e.target.value)}
            placeholder="Try: 'What is the rule for forklift pedestrian clearance?' or 'helmet standard'"
            className="flex-1 rounded-xl border border-slate-200 bg-slate-50/50 px-4 py-2.5 text-sm text-slate-900 transition focus:border-blue-500 focus:bg-white focus:outline-none dark:border-slate-800 dark:bg-slate-950 dark:text-white"
          />
          <button
            type="submit"
            disabled={isSearchingRag || !testQuery.trim()}
            className="flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:opacity-50 dark:bg-blue-600 dark:hover:bg-blue-700"
          >
            {isSearchingRag ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            Test Query
          </button>
        </form>

        {testResults && (
          <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Retrieval Results ({testResults.length} matches)
            </div>
            {testResults.length === 0 ? (
              <div className="mt-2 text-sm text-slate-500">
                No matching policy chunks found. (Ungrounded queries are refused).
              </div>
            ) : (
              <div className="mt-2 space-y-3">
                {testResults.map((r, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-slate-200/80 bg-white p-3 shadow-xs dark:border-slate-800 dark:bg-slate-900"
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-slate-900 dark:text-white">
                        {r.title || r.source_file}
                      </div>
                      <span className="rounded bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-400">
                        v{r.version || '1.0'}
                      </span>
                    </div>
                    {r.description && (
                      <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                        {r.description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Upload Policy Modal */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Ingest New Operational Policy
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Document text will be chunked, vectorized, and stored in Neon DB
                </p>
              </div>
              <button
                onClick={() => !isIngesting && setIsUploadOpen(false)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="mt-4 space-y-4">
              {uploadError && (
                <div className="flex items-center gap-2 rounded-xl bg-red-50 p-3 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-400">
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

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Assign Facility / Site
                </label>
                <select
                  value={uploadSiteId}
                  onChange={(e) => setUploadSiteId(e.target.value)}
                  className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 focus:border-blue-500 focus:outline-none dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                >
                  {sites.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.location || 'Facility'})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Policy Title *
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Warehouse General Operations Policy"
                  className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 focus:border-blue-500 focus:outline-none dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Version
                  </label>
                  <input
                    type="text"
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                    placeholder="1.0"
                    className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 focus:border-blue-500 focus:outline-none dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Effective Date
                  </label>
                  <input
                    type="date"
                    value={effectiveDate}
                    onChange={(e) => setEffectiveDate(e.target.value)}
                    className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 focus:border-blue-500 focus:outline-none dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Description / Regulatory Scope
                </label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Summary of PPE, forklift speed, or walkway clearance rules..."
                  className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 focus:border-blue-500 focus:outline-none dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                />
              </div>

              {/* PDF File Drag & Drop Zone */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Policy Document PDF *
                </label>
                <div className="mt-1.5 flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50/50 p-6 text-center transition hover:border-blue-500 dark:border-slate-700 dark:bg-slate-950/40">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="hidden"
                    id="policy-file-input"
                  />
                  <label
                    htmlFor="policy-file-input"
                    className="flex cursor-pointer flex-col items-center"
                  >
                    <UploadCloud className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                    <span className="mt-2 text-sm font-semibold text-slate-800 dark:text-slate-200">
                      {selectedFile ? selectedFile.name : 'Select or drop PDF document'}
                    </span>
                    <span className="mt-0.5 text-xs text-slate-400">
                      Supports standard PDF files up to 25MB
                    </span>
                  </label>
                </div>
              </div>

              {isIngesting && (
                <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-3.5 dark:border-blue-900 dark:bg-blue-950/40">
                  <div className="flex items-center gap-2.5 text-xs font-semibold text-blue-800 dark:text-blue-300">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Ingestion Pipeline In Progress</span>
                  </div>
                  <div className="mt-1.5 text-xs text-blue-700 dark:text-blue-400">
                    {ingestStep}
                  </div>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  disabled={isIngesting}
                  className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isIngesting || !selectedFile}
                  className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-blue-500/20 transition hover:bg-blue-700 disabled:opacity-50"
                >
                  {isIngesting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Ingesting...
                    </>
                  ) : (
                    <>
                      <Check className="h-4 w-4" />
                      Start Ingestion
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
