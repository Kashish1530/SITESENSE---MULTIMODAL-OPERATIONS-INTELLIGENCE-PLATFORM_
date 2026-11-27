import { useState, useEffect } from 'react'
import {
  CalendarDays,
  CheckCircle2,
  Clock3,
  ClipboardList,
  FileUp,
  ListTodo,
  MapPin,
  ShieldCheck,
  Zap,
  ArrowRight,
  Eye,
  Camera,
  Radio,
  Cpu,
} from 'lucide-react'
import type { DemoUser } from '../../data/users'
import type { InspectionRecord } from '../../inspections/types'
import {
  getActiveTasks,
  getCompletedTasks,
  getEmployeeTasks,
} from '../../inspections/taskUtils'

type Props = {
  currentUser: DemoUser
  inspections: InspectionRecord[]
  onNavigate: (page: string) => void
}

function formatDueDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Date not available'
  return date.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export default function EmployeeDashboard({
  currentUser,
  inspections,
  onNavigate,
}: Props) {
  const assignedTasks = getEmployeeTasks(inspections, currentUser.id)
  const activeTasks = getActiveTasks(inspections, currentUser.id)
  const completedTasks = getCompletedTasks(inspections, currentUser.id)
  const firstName = currentUser.name.split(' ')[0]

  // Simulated live sensor stream ticker
  const [pulseTick, setPulseTick] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => {
      setPulseTick((prev) => (prev + 1) % 4)
    }, 4000)
    return () => clearInterval(timer)
  }, [])

  const sensorFeeds = [
    {
      node: 'CAM-01 [Zone A Egress]',
      status: 'PPE Compliance Verified • Hard hat & vest detected (99.4%)',
      badge: 'STABLE',
      color: 'emerald',
    },
    {
      node: 'OPTICAL-03 [Forklift Bay]',
      status: 'Safe transit corridor clear • Speed adherence 100%',
      badge: 'NORMAL',
      color: 'blue',
    },
    {
      node: 'SENSOR-08 [Chemical Racks]',
      status: 'Containment perimeter optimal • 0 ppm volatile leakage',
      badge: 'SECURE',
      color: 'cyan',
    },
    {
      node: 'AI MULTIMODAL CORE',
      status: 'pgvector Authoritative Rules active • Real-time grounding ready',
      badge: 'ONLINE',
      color: 'indigo',
    },
  ]

  const currentFeed = sensorFeeds[pulseTick]

  return (
    <div className="space-y-6">
      {/* 1. Futuristic Hero Operations Cockpit */}
      <div className="relative overflow-hidden rounded-3xl border border-blue-500/20 bg-gradient-to-r from-slate-950 via-slate-900 to-blue-950 p-6 text-white shadow-2xl shadow-blue-950/30 sm:p-8">
        {/* Ambient background glows & mesh */}
        <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-cyan-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 -left-20 h-64 w-64 rounded-full bg-blue-600/20 blur-3xl" />
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,#38bdf80a_1px,transparent_1px),linear-gradient(to_bottom,#38bdf80a_1px,transparent_1px)] bg-[size:2.5rem_2.5rem]" />

        <div className="relative z-10 flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
          <div className="space-y-3">
            {/* Live Beacon Tag */}
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-500/10 px-3.5 py-1 text-xs font-semibold text-cyan-300 backdrop-blur-md">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-400"></span>
              </span>
              <span>MULTIMODAL OPERATIONS RADAR ACTIVE</span>
            </div>

            <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
              Welcome back,{' '}
              <span className="bg-gradient-to-r from-blue-400 via-cyan-300 to-indigo-300 bg-clip-text text-transparent">
                {firstName}
              </span>
            </h1>

            <p className="max-w-xl text-sm leading-relaxed text-slate-300">
              SiteSense AI Vision is monitoring your assigned operations sectors in real time.
              All safety standards from authoritative policy manuals are active.
            </p>

            {/* Quick status pills */}
            <div className="flex flex-wrap items-center gap-2 pt-1 font-mono text-xs">
              <span className="rounded-lg bg-white/10 px-2.5 py-1 text-slate-200">
                ROLE: {currentUser.role.toUpperCase()}
              </span>
              <span className="rounded-lg bg-white/10 px-2.5 py-1 text-slate-200">
                SECTOR: ZONE A / MAIN DC
              </span>
              <span className="inline-flex items-center gap-1 rounded-lg bg-emerald-500/20 px-2.5 py-1 font-semibold text-emerald-300">
                <CheckCircle2 className="h-3 w-3" />
                READINESS: 100%
              </span>
            </div>
          </div>

          {/* Right Holographic Radar & Chip Badge */}
          <div className="flex shrink-0 items-center gap-5">
            {/* Animated Sonar Radar Visualizer */}
            <div className="relative flex h-24 w-24 items-center justify-center rounded-full border border-cyan-500/30 bg-slate-950/80 shadow-lg shadow-cyan-500/10">
              <div className="absolute h-18 w-18 rounded-full border border-blue-500/20 animate-pulse" />
              <div className="absolute h-12 w-12 rounded-full border border-cyan-400/30" />
              <div className="absolute h-6 w-6 rounded-full bg-cyan-500/20" />
              {/* Rotating Radar Sweep */}
              <div
                className="absolute inset-0 rounded-full bg-[conic-gradient(from_0deg,transparent_0_300deg,rgba(6,182,212,0.5)_360deg)] animate-spin"
                style={{ animationDuration: '3.5s' }}
              />
              <Radio className="relative z-10 h-6 w-6 text-cyan-400" />
              {/* Glowing radar blips */}
              <span className="absolute top-4 right-5 h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
              <span className="absolute bottom-5 left-4 h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
            </div>

            {/* Holographic Chip ID Badge */}
            <div className="rounded-2xl border border-white/15 bg-gradient-to-br from-white/10 to-white/5 p-4 backdrop-blur-xl shadow-inner min-w-[150px]">
              <div className="flex items-center justify-between gap-3 text-[10px] font-semibold text-cyan-300">
                <span>IDENTITY CHIP</span>
                <Cpu className="h-3.5 w-3.5 text-cyan-400" />
              </div>
              <p className="mt-1 text-base font-extrabold tracking-wide text-white">
                {currentUser.employeeId}
              </p>
              <div className="mt-2 flex items-center gap-1.5 text-[10px] font-medium text-slate-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                <span>AUTHENTICATED</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Live Multimodal Sensor Feed Ribbon */}
      <div className="flex items-center justify-between gap-3 rounded-2xl border border-blue-500/20 bg-gradient-to-r from-blue-950/20 via-slate-900/10 to-indigo-950/20 px-5 py-3 shadow-sm backdrop-blur-md">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-blue-600/10 text-blue-600 dark:bg-blue-400/10 dark:text-cyan-400">
            <Camera className="h-4 w-4 animate-pulse" />
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center sm:gap-2 text-xs truncate">
            <span className="font-bold text-slate-900 dark:text-white uppercase tracking-wider text-[11px]">
              {currentFeed.node}:
            </span>
            <span className="text-slate-600 dark:text-slate-300 truncate">
              {currentFeed.status}
            </span>
          </div>
        </div>
        <span className="hidden sm:inline-flex rounded-full bg-cyan-100 px-2.5 py-0.5 text-[10px] font-bold text-cyan-800 dark:bg-cyan-950/60 dark:text-cyan-300">
          {currentFeed.badge}
        </span>
      </div>

      {/* 3. Crazy 3-Card Glassmorphic KPI Matrix */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        {/* Card 1: Assigned Tasks */}
        <div className="group relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white/80 p-6 shadow-sm backdrop-blur-md transition-all duration-300 hover:-translate-y-1 hover:border-blue-500/50 hover:shadow-xl hover:shadow-blue-500/10 dark:border-slate-800/80 dark:bg-slate-900/80">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-indigo-500" />
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Assigned Tasks
            </span>
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 shadow-inner group-hover:scale-110 transition dark:bg-blue-950/50 dark:text-blue-400">
              <ListTodo className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              {assignedTasks.length}
            </span>
            <span className="text-xs font-semibold text-blue-600 dark:text-blue-400">
              Total In Queue
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Work items synchronized from management pipeline
          </p>
        </div>

        {/* Card 2: Active Tasks */}
        <div className="group relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white/80 p-6 shadow-sm backdrop-blur-md transition-all duration-300 hover:-translate-y-1 hover:border-amber-500/50 hover:shadow-xl hover:shadow-amber-500/10 dark:border-slate-800/80 dark:bg-slate-900/80">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-amber-400 to-orange-500" />
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Active Tasks
            </span>
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-50 text-amber-600 shadow-inner group-hover:scale-110 transition dark:bg-amber-950/50 dark:text-amber-400">
              <Clock3 className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              {activeTasks.length}
            </span>
            <span className="text-xs font-semibold text-amber-600 dark:text-amber-400">
              In Progress
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Requires on-site inspection or photo evidence
          </p>
        </div>

        {/* Card 3: Completed */}
        <div className="group relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white/80 p-6 shadow-sm backdrop-blur-md transition-all duration-300 hover:-translate-y-1 hover:border-emerald-500/50 hover:shadow-xl hover:shadow-emerald-500/10 dark:border-slate-800/80 dark:bg-slate-900/80">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-400 to-teal-500" />
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Completed
            </span>
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 shadow-inner group-hover:scale-110 transition dark:bg-emerald-950/50 dark:text-emerald-400">
              <CheckCircle2 className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              {completedTasks.length}
            </span>
            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              100% Verified
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Passed safety checks with zero open violations
          </p>
        </div>
      </div>

      {/* 4. Active Tasks / Multimodal Zone Status */}
      <section className="rounded-3xl border border-slate-200/80 bg-white shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-100 p-6 dark:border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
              <ClipboardList className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-bold text-slate-900 dark:text-white">
                Your Assigned Safety Workload
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Track open inspections, complete checklists, and log visual proof
              </p>
            </div>
          </div>
          <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
            {activeTasks.length} Active
          </span>
        </div>

        {activeTasks.length === 0 ? (
          /* Futuristic Sonar Scan Empty State */
          <div className="flex flex-col items-center justify-center p-10 sm:p-14 text-center">
            {/* Concentric Pulse Scanner Visual */}
            <div className="relative mb-6 flex items-center justify-center">
              <div className="absolute h-28 w-28 animate-ping rounded-full bg-emerald-500/10 duration-1000" />
              <div className="absolute h-36 w-36 rounded-full border border-emerald-500/20" />
              <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white shadow-xl shadow-emerald-500/20">
                <ShieldCheck className="h-10 w-10" />
              </div>
            </div>

            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              All Operational Sectors Monitored & Clear
            </h3>
            <p className="mt-2 max-w-md text-sm text-slate-500 dark:text-slate-400">
              You currently have zero pending violations. SiteSense multimodal vision nodes are
              cross-referencing camera feeds with company safety standards (SHB-01).
            </p>

            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => onNavigate('Upload')}
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-md shadow-blue-500/20 transition hover:from-blue-700 hover:to-indigo-700 active:scale-95"
              >
                <FileUp className="h-4 w-4" />
                Upload Task Evidence
              </button>
              <button
                type="button"
                onClick={() => onNavigate('My Tasks')}
                className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                <Eye className="h-4 w-4 text-slate-400" />
                Inspect Full Log
              </button>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800/80">
            {activeTasks.slice(0, 4).map((task) => {
              const site = { name: task.siteName || task.siteId || 'Facility' }

              return (
                <div
                  key={task.id}
                  className="p-5 transition hover:bg-slate-50/80 dark:hover:bg-slate-800/40"
                >
                  <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
                    <div>
                      <h3 className="font-semibold text-slate-900 dark:text-white">
                        {task.title}
                      </h3>
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                        {task.description}
                      </p>
                    </div>
                    <span className="h-fit w-fit rounded-lg bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
                      {task.status}
                    </span>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                    <span className="flex items-center gap-1.5">
                      <MapPin className="h-3.5 w-3.5 text-slate-400" />
                      {site?.name ?? task.siteId} • {task.zone}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <CalendarDays className="h-3.5 w-3.5 text-slate-400" />
                      Due {formatDueDate(task.dueDate)}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        <div className="border-t border-slate-100 p-4 dark:border-slate-800/80 flex items-center justify-between">
          <button
            type="button"
            onClick={() => onNavigate('My Tasks')}
            className="flex items-center gap-2 text-xs font-bold text-blue-600 hover:text-blue-700 dark:text-blue-400"
          >
            <span>View all assigned workload</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
          <span className="text-xs text-slate-400">
            Realtime database sync via PostgreSQL
          </span>
        </div>
      </section>

      {/* 5. Crazy Futuristic Quick Action Hub */}
      <section className="rounded-3xl border border-slate-200/80 bg-white p-6 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Zap className="h-4 w-4 text-blue-600 dark:text-cyan-400" />
            Quick Command Actions
          </h2>
          <span className="text-xs text-slate-400">Direct workspace shortcuts</span>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {/* Action 1 */}
          <button
            type="button"
            onClick={() => onNavigate('My Tasks')}
            className="group flex items-center justify-between rounded-2xl border border-slate-200/80 bg-gradient-to-br from-white to-slate-50/50 p-4 text-left shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-blue-500/50 hover:shadow-md hover:shadow-blue-500/10 dark:border-slate-800 dark:from-slate-900 dark:to-slate-950"
          >
            <div className="flex items-center gap-3.5">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600 shadow-inner group-hover:scale-110 transition dark:bg-blue-950/50 dark:text-blue-400">
                <ClipboardList className="h-5 w-5" />
              </div>
              <div>
                <p className="font-bold text-slate-900 dark:text-white text-sm">
                  Review My Tasks
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Inspect task checklists, verify zone details & log notes
                </p>
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-1 transition" />
          </button>

          {/* Action 2 */}
          <button
            type="button"
            onClick={() => onNavigate('Upload')}
            className="group flex items-center justify-between rounded-2xl border border-slate-200/80 bg-gradient-to-br from-white to-slate-50/50 p-4 text-left shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-cyan-500/50 hover:shadow-md hover:shadow-cyan-500/10 dark:border-slate-800 dark:from-slate-900 dark:to-slate-950"
          >
            <div className="flex items-center gap-3.5">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-cyan-50 text-cyan-600 shadow-inner group-hover:scale-110 transition dark:bg-cyan-950/50 dark:text-cyan-400">
                <FileUp className="h-5 w-5" />
              </div>
              <div>
                <p className="font-bold text-slate-900 dark:text-white text-sm">
                  Upload Task Photos & Media
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Submit visual evidence for multimodal AI verification
                </p>
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-cyan-600 group-hover:translate-x-1 transition" />
          </button>
        </div>
      </section>
    </div>
  )
}
