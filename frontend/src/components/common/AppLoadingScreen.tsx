import { useEffect, useState } from 'react'
import { Activity, ShieldCheck, Cpu, Database, Sparkles, CheckCircle2 } from 'lucide-react'

interface Props {
  onComplete?: () => void
  durationMs?: number
}

const BOOT_STAGES = [
  { label: 'Initializing SiteSense Multimodal Neural Engine...', icon: Cpu, progress: 22 },
  { label: 'Calibrating Edge Sensor Telemetry & Visual PPE Nodes...', icon: ShieldCheck, progress: 48 },
  { label: 'Loading pgvector Authoritative Standards & Rules...', icon: Database, progress: 74 },
  { label: 'Establishing Neon Serverless Cloud Uplink...', icon: Sparkles, progress: 92 },
  { label: 'Operations Intelligence Platform Online.', icon: CheckCircle2, progress: 100 },
]

export default function AppLoadingScreen({ onComplete, durationMs = 1400 }: Props) {
  // Check if we are in automated test environment (e.g. vitest) to avoid delaying tests
  const isTest = (import.meta as any).env?.MODE === 'test'

  const [currentStageIndex, setCurrentStageIndex] = useState(0)
  const [progress, setProgress] = useState(isTest ? 100 : 0)
  const [isFadingOut, setIsFadingOut] = useState(false)
  const [isDismissed, setIsDismissed] = useState(isTest)

  useEffect(() => {
    if (isTest) {
      onComplete?.()
      return
    }

    const intervalTime = durationMs / 100
    let currentP = 0

    const timer = setInterval(() => {
      currentP += 2
      if (currentP >= 100) {
        currentP = 100
        setProgress(100)
        clearInterval(timer)

        // Trigger graceful fade out
        setTimeout(() => {
          setIsFadingOut(true)
          setTimeout(() => {
            setIsDismissed(true)
            onComplete?.()
          }, 350)
        }, 150)
      } else {
        setProgress(currentP)

        // Update stage based on progress
        const stageIdx = BOOT_STAGES.findIndex((s) => currentP <= s.progress)
        if (stageIdx !== -1) {
          setCurrentStageIndex(stageIdx)
        }
      }
    }, intervalTime)

    return () => clearInterval(timer)
  }, [durationMs, isTest, onComplete])

  if (isDismissed) return null

  const CurrentIcon = BOOT_STAGES[currentStageIndex]?.icon || Activity

  return (
    <div
      className={`fixed inset-0 z-50 flex flex-col items-center justify-center bg-slate-950 text-white transition-opacity duration-300 ${
        isFadingOut ? 'opacity-0 pointer-events-none' : 'opacity-100'
      }`}
      style={{
        background:
          'radial-gradient(circle at 50% 45%, rgba(30, 58, 138, 0.45) 0%, rgba(15, 23, 42, 0.95) 60%, rgba(2, 6, 23, 1) 100%)',
      }}
    >
      {/* Background ambient pulse grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b15_1px,transparent_1px),linear-gradient(to_bottom,#1e293b15_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center max-w-md px-6 text-center">
        {/* Glowing Radar Logo */}
        <div className="relative mb-8 flex items-center justify-center">
          {/* Animated pulsing rings */}
          <div className="absolute h-28 w-28 animate-ping rounded-full bg-blue-500/20 duration-1000" />
          <div className="absolute h-36 w-36 rounded-full border border-cyan-500/30 animate-pulse" />
          <div className="absolute h-44 w-44 rounded-full border border-blue-500/20" />

          {/* Central Hex Badge */}
          <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-400 p-0.5 shadow-2xl shadow-blue-500/50">
            <div className="flex h-full w-full items-center justify-center rounded-[14px] bg-slate-950">
              <Activity className="h-10 w-10 text-cyan-400 animate-pulse" />
            </div>
          </div>
        </div>

        {/* Brand Title */}
        <div className="mb-2">
          <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            Site<span className="bg-gradient-to-r from-blue-400 via-cyan-300 to-indigo-400 bg-clip-text text-transparent">Sense</span>
          </h1>
          <p className="mt-1 text-xs font-semibold uppercase tracking-[0.25em] text-cyan-400/90">
            Multimodal Operations Intelligence
          </p>
        </div>

        {/* Dynamic Telemetry Status */}
        <div className="my-6 flex items-center gap-2.5 rounded-full border border-blue-500/20 bg-blue-950/40 px-4 py-1.5 text-xs font-medium text-blue-200 backdrop-blur-md">
          <CurrentIcon className="h-4 w-4 text-cyan-400 animate-spin-slow shrink-0" />
          <span className="truncate max-w-[280px]">
            {BOOT_STAGES[currentStageIndex]?.label || 'Loading...'}
          </span>
        </div>

        {/* Progress Bar Container */}
        <div className="w-72 sm:w-80">
          <div className="relative h-2 w-full overflow-hidden rounded-full bg-slate-800/80 p-0.5 ring-1 ring-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-500 via-cyan-400 to-indigo-500 shadow-[0_0_12px_rgba(6,182,212,0.8)] transition-all duration-75 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="mt-2.5 flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span>SECURE SYSTEM BOOT</span>
            <span className="font-bold text-cyan-300">{progress}%</span>
          </div>
        </div>

        {/* Skip button for impatient users */}
        <button
          onClick={() => {
            setIsDismissed(true)
            onComplete?.()
          }}
          className="mt-8 text-xs text-slate-500 hover:text-slate-300 underline underline-offset-4 transition"
        >
          Skip intro &rarr;
        </button>
      </div>
    </div>
  )
}
