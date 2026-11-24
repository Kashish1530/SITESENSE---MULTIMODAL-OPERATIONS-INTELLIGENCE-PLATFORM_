
import { useState, type FormEvent } from 'react'
import {
    Activity,
    ArrowRight,
    Eye,
    EyeOff,
    LockKeyhole,
    Mail,
    ShieldCheck,
} from 'lucide-react'

type LoginProps = {
    onLogin: (identifier: string, password: string) => void
    error: string
    isLoading?: boolean
}

export default function Login({ onLogin, error, isLoading = false }: LoginProps) {
    const [identifier, setIdentifier] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)

    function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault()
        onLogin(identifier, password)
    }

    const quickLogins = [
        { label: 'Admin', email: 'admin@sitesense.io', pass: 'SiteSense@2026', roleDesc: 'admin' },
        { label: 'Manager', email: 'manager@sitesense.io', pass: 'SiteSense@2026', roleDesc: 'manager' },
        { label: 'Reviewer', email: 'reviewer1@sitesense.io', pass: 'SiteSense@2026', roleDesc: 'supervisor' },
        { label: 'Field', email: 'field1@sitesense.io', pass: 'SiteSense@2026', roleDesc: 'employee' },
    ]

    return (
        <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10">
            <div className="grid w-full max-w-5xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl lg:grid-cols-2">

                <section className="relative hidden flex-col justify-between overflow-hidden bg-slate-950 p-10 text-white lg:flex">
                    <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-blue-600/20 blur-3xl" />
                    <div className="absolute -bottom-24 -left-24 h-80 w-80 rounded-full bg-cyan-500/10 blur-3xl" />

                    <div className="relative flex items-center gap-3">
                        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600">
                            <Activity size={25} />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold tracking-tight">SiteSense</h1>
                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                                Operations Intelligence
                            </p>
                        </div>
                    </div>

                    <div className="relative my-12">
                        <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-blue-400/20 bg-blue-400/10 px-3 py-1.5 text-xs font-medium text-blue-200">
                            <ShieldCheck size={14} />
                            Intelligent operations platform
                        </div>

                        <h2 className="max-w-md text-4xl font-semibold leading-tight tracking-tight">
                            See more.
                            <br />
                            Understand better.
                            <br />
                            <span className="text-blue-400">Act smarter.</span>
                        </h2>

                        <p className="mt-5 max-w-sm text-sm leading-7 text-slate-400">
                            Bring inspections, evidence, operational insights
                            and team workflows together in one workspace.
                        </p>
                    </div>

                    <div className="relative border-t border-white/10 pt-5">
                        <p className="text-xs text-slate-500">
                            SiteSense · Multimodal Operations Intelligence
                        </p>
                    </div>
                </section>

                <section className="flex flex-col justify-center px-6 py-10 sm:px-12 lg:px-14">
                    <div className="mb-8 flex items-center gap-3 lg:hidden">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white">
                            <Activity size={23} />
                        </div>
                        <div>
                            <h1 className="text-lg font-bold text-slate-900">SiteSense</h1>
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                                Operations Intelligence
                            </p>
                        </div>
                    </div>

                    <div>
                        <p className="text-sm font-semibold text-blue-600">
                            Welcome back
                        </p>
                        <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
                            Sign in to SiteSense
                        </h2>
                        <p className="mt-2 text-sm leading-6 text-slate-500">
                            Enter your account details to access your workspace.
                        </p>
                    </div>

                    <form onSubmit={handleSubmit} className="mt-8 space-y-5">
                        <div>
                            <label
                                htmlFor="identifier"
                                className="mb-2 block text-sm font-medium text-slate-700"
                            >
                                Email or Employee ID
                            </label>

                            <div className="relative">
                                <Mail
                                    size={18}
                                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400"
                                />
                                <input
                                    id="identifier"
                                    type="text"
                                    autoComplete="username"
                                    required
                                    value={identifier}
                                    onChange={(event) => setIdentifier(event.target.value)}
                                    placeholder="Enter email or employee ID"
                                    className="w-full rounded-xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10"
                                />
                            </div>
                        </div>

                        <div>
                            <label
                                htmlFor="password"
                                className="mb-2 block text-sm font-medium text-slate-700"
                            >
                                Password
                            </label>

                            <div className="relative">
                                <LockKeyhole
                                    size={18}
                                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400"
                                />
                                <input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    autoComplete="current-password"
                                    required
                                    value={password}
                                    onChange={(event) => setPassword(event.target.value)}
                                    placeholder="Enter your password"
                                    className="w-full rounded-xl border border-slate-200 bg-white py-3 pl-11 pr-12 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                                >
                                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </div>

                        {error && (
                            <div
                                role="alert"
                                className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
                            >
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:bg-blue-700 active:scale-[0.99] disabled:opacity-60 disabled:cursor-not-allowed"
                        >
                            {isLoading ? 'Connecting to SiteSense...' : 'Sign in'}
                            <ArrowRight size={17} />
                        </button>
                    </form>

                    <div className="mt-6">
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                            Quick Sign-in (Live Backend Roles)
                        </p>
                        <div className="mt-2.5 grid grid-cols-2 gap-2 sm:grid-cols-4">
                            {quickLogins.map(item => (
                                <button
                                    key={item.label}
                                    type="button"
                                    onClick={() => {
                                        setIdentifier(item.email)
                                        setPassword(item.pass)
                                        onLogin(item.email, item.pass)
                                    }}
                                    className="flex flex-col items-start rounded-lg border border-slate-200 bg-slate-50/80 p-2 text-left hover:border-blue-400 hover:bg-blue-50/50 transition"
                                >
                                    <span className="text-xs font-bold text-slate-900">{item.label}</span>
                                    <span className="text-[10px] text-slate-500">{item.roleDesc}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="mt-5 rounded-xl border border-blue-100 bg-blue-50/70 p-4">
                        <div className="flex items-start gap-2.5">
                            <ShieldCheck size={18} className="mt-0.5 shrink-0 text-blue-600" />
                            <div>
                                <p className="text-xs font-semibold text-blue-900">
                                    Live FastAPI & Neon Database Connected
                                </p>
                                <p className="mt-1 text-xs leading-5 text-blue-800/80">
                                    Backend REST API: <code className="rounded bg-blue-100 px-1 py-0.5 font-mono text-[11px]">http://localhost:8000/api/v1</code>.
                                    Role mapping active: Employee ➔ Field, Supervisor ➔ Reviewer.
                                </p>
                            </div>
                        </div>
                    </div>

                    <p className="mt-8 text-center text-xs text-slate-400">
                        © 2026 SiteSense. All rights reserved.
                    </p>
                </section>
            </div>
        </main>
    )
}
