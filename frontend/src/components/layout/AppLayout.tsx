
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
        <div className="h-screen overflow-hidden bg-slate-50 lg:flex">
            <Sidebar
                collapsed={collapsed}
                onToggle={() => setCollapsed(!collapsed)}
                mobileOpen={mobileOpen}
                onMobileClose={() => setMobileOpen(false)}
                activePage={activePage}
                onNavigate={onNavigate}
                currentUser={currentUser}
            />

            <div className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden">
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
                    <div className="mx-auto w-full max-w-[1600px]">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    )
}
