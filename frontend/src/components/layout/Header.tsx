
import { useState } from 'react'
import {
    Bell,
    ChevronDown,
    Menu,
    Search,
    Command,
    LogOut,
    Eye,
} from 'lucide-react'
import type { DemoUser } from '../../data/users'

type HeaderProps = {
    onMenuClick: () => void
    activePage: string
    currentUser: DemoUser
    onLogout: () => void
}

function getInitials(name: string) {
    return name
        .split(' ')
        .map(part => part[0])
        .join('')
        .slice(0, 2)
        .toUpperCase()
}

export default function Header({
    onMenuClick,
    activePage,
    currentUser,
    onLogout,
}: HeaderProps) {
    const [profileOpen, setProfileOpen] = useState(false)

    return (
        <header className="sticky top-0 z-30 flex h-[72px] shrink-0 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-6 lg:px-8">
            <div className="flex min-w-0 items-center gap-3">
                <button
                    onClick={onMenuClick}
                    className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
                    aria-label="Open navigation"
                >
                    <Menu size={21} />
                </button>

                <div className="min-w-0">
                    <h2 className="truncate text-lg font-semibold text-slate-900">
                        {activePage}
                    </h2>
                    <p className="hidden text-xs text-slate-400 sm:block">
                        Monitor and manage your operations
                    </p>
                </div>
            </div>

            <div className="flex items-center gap-2 sm:gap-4">
                <button
                    className="hidden items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-400 hover:bg-slate-50 md:flex"
                    aria-label="Search"
                >
                    <Search size={16} />
                    <span>Search</span>
                    <span className="ml-3 flex items-center gap-1 rounded border border-slate-200 px-1.5 py-0.5 text-[10px]">
                        <Command size={10} /> K
                    </span>
                </button>

                <button
                    className="relative rounded-lg p-2 text-slate-500 hover:bg-slate-100"
                    aria-label="Notifications"
                >
                    <Bell size={19} />
                    <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full border-2 border-white bg-red-500" />
                </button>

                <div className="relative">
                    <button
                        onClick={() => setProfileOpen(!profileOpen)}
                        className="flex items-center gap-2 rounded-lg p-1.5 hover:bg-slate-50"
                        aria-expanded={profileOpen}
                        aria-label="Open account menu"
                    >
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                            {getInitials(currentUser.name)}
                        </div>

                        <div className="hidden text-left sm:block">
                            <p className="max-w-32 truncate text-sm font-medium text-slate-700">
                                {currentUser.name}
                            </p>
                            <p className="text-xs capitalize text-slate-400">
                                {currentUser.role}
                            </p>
                        </div>

                        <ChevronDown size={15} className="hidden text-slate-400 sm:block" />
                    </button>

                    {profileOpen && (
                        <div className="absolute right-0 top-full z-50 mt-2 w-64 rounded-xl border border-slate-200 bg-white p-2 shadow-xl">
                            <div className="border-b border-slate-100 px-3 py-3">
                                <p className="truncate text-sm font-semibold text-slate-800">
                                    {currentUser.name}
                                </p>
                                <p className="mt-1 truncate text-xs text-slate-500">
                                    {currentUser.email}
                                </p>
                                <p className="mt-1 text-xs capitalize text-blue-600">
                                    {currentUser.role}
                                </p>
                                <div className="mt-2 inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-amber-700">
                                    <Eye size={12} />
                                    Preview identity
                                </div>
                            </div>

                            <button
                                onClick={() => {
                                    setProfileOpen(false)
                                    onLogout()
                                }}
                                className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-red-600 hover:bg-red-50"
                            >
                                <LogOut size={17} />
                                Sign out
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </header>
    )
}
