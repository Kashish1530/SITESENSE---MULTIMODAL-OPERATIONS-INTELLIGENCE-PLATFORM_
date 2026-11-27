
import { useState } from 'react'
import { Eye, X } from 'lucide-react'
import Sidebar from './Sidebar'
import Header from './Header'
import type { DemoUser } from '../../data/users'

type AppLayoutProps = {
    children: React.ReactNode
    activePage: string
    onNavigate: (page: string) => void
    currentUser: DemoUser
    actualUser: DemoUser
    isPreviewMode: boolean
    onExitPreview: () => void
    onLogout: () => void
}

export default function AppLayout({
    children,
    activePage,
    onNavigate,
    currentUser,
    actualUser,
    isPreviewMode,
    onExitPreview,
    onLogout,
}: AppLayoutProps) {
    const [collapsed, setCollapsed] = useState(false)
    const [mobileOpen, setMobileOpen] = useState(false)

    return (
        <div className="relative h-screen overflow-hidden bg-slate-50/80 dark:bg-slate-950 lg:flex">
            {/* Ambient High-Tech Grid & Lighting Mesh */}
            <div className="pointer-events-none fixed inset-0 z-0 bg-[linear-gradient(to_right,#0ea5e908_1px,transparent_1px),linear-gradient(to_bottom,#0ea5e908_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_80%_60%_at_50%_0%,#000_70%,transparent_100%)]" />
            <div className="pointer-events-none fixed -top-40 -right-40 h-96 w-96 rounded-full bg-blue-500/10 blur-3xl" />
            <div className="pointer-events-none fixed top-1/2 -left-40 h-96 w-96 rounded-full bg-cyan-500/10 blur-3xl" />

            <Sidebar
                collapsed={collapsed}
                onToggle={() => setCollapsed(!collapsed)}
                mobileOpen={mobileOpen}
                onMobileClose={() => setMobileOpen(false)}
                activePage={activePage}
                onNavigate={onNavigate}
                currentUser={currentUser}
            />

            <div className="relative z-10 flex h-screen min-w-0 flex-1 flex-col overflow-hidden">
                {isPreviewMode && (
                    <div className="shrink-0 flex flex-wrap items-center justify-between gap-3 border-b border-amber-200 bg-amber-50 px-4 py-3 sm:px-6">
                        <div className="flex items-center gap-3">
                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-700">
                                <Eye size={18} />
                            </div>
                            <div>
                                <p className="text-sm font-semibold text-amber-900">
                                    Preview Mode
                                </p>
                                <p className="text-xs text-amber-800">
                                    Viewing {currentUser.name} ({currentUser.role}) as {actualUser.name}
                                </p>
                            </div>
                        </div>

                        <button
                            type="button"
                            onClick={onExitPreview}
                            className="inline-flex items-center gap-2 rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm font-semibold text-amber-900 transition hover:bg-amber-100"
                        >
                            <X size={15} />
                            Exit Preview
                        </button>
                    </div>
                )}

                <Header
                    onMenuClick={() => setMobileOpen(true)}
                    activePage={activePage}
                    currentUser={currentUser}
                    onLogout={onLogout}
                />

                <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
                    <div className="mx-auto w-full max-w-[1600px] space-y-5">
                        {/* High-Tech Operational Telemetry Header */}
                        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-blue-500/15 bg-white/70 px-4 py-2.5 shadow-sm backdrop-blur-md dark:border-blue-500/20 dark:bg-slate-900/70">
                            <div className="flex items-center gap-2.5">
                                <span className="relative flex h-2.5 w-2.5">
                                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
                                </span>
                                <span className="text-[11px] font-bold tracking-wider text-slate-800 uppercase dark:text-slate-100">
                                    SYSTEM TELEMETRY: ONLINE
                                </span>
                                <span className="text-slate-300 dark:text-slate-700">|</span>
                                <span className="hidden text-xs text-slate-500 dark:text-slate-400 sm:inline">
                                    Multimodal AI Vision & pgvector Policy Engine Active
                                </span>
                            </div>
                            <div className="flex items-center gap-3 font-mono text-[11px] text-slate-500 dark:text-slate-400">
                                <span className="flex items-center gap-1.5 rounded-md bg-blue-50/80 px-2 py-0.5 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
                                    <span className="h-1.5 w-1.5 rounded-full bg-blue-500"></span>
                                    4 Sensor Nodes
                                </span>
                                <span className="flex items-center gap-1.5 rounded-md bg-cyan-50/80 px-2 py-0.5 text-cyan-700 dark:bg-cyan-950/40 dark:text-cyan-300">
                                    <span className="h-1.5 w-1.5 rounded-full bg-cyan-500"></span>
                                    RAG Grounded
                                </span>
                                <span className="flex items-center gap-1.5 rounded-md bg-emerald-50/80 px-2 py-0.5 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                                    99.4% Compliance
                                </span>
                            </div>
                        </div>

                        {children}
                    </div>
                </main>
            </div>
        </div>
    )
}
