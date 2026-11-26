
import { TrendingUp, TrendingDown, Minus, AlertCircle } from 'lucide-react'

type MetricCardProps = {
    title: string
    value: string
    change: string
    trend: string
    description: string
}

export default function MetricCard({
    title,
    value,
    change,
    trend,
    description,
}: MetricCardProps) {
    const trendStyles = {
        up: 'bg-emerald-50 text-emerald-700',
        down: 'bg-red-50 text-red-700',
        warning: 'bg-amber-50 text-amber-700',
        neutral: 'bg-slate-100 text-slate-600',
    }

    const TrendIcon =
        trend === 'up'
            ? TrendingUp
            : trend === 'down'
                ? TrendingDown
                : trend === 'warning'
                    ? AlertCircle
                    : Minus

    const style =
        trendStyles[trend as keyof typeof trendStyles] ?? trendStyles.neutral

    return (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
            <p className="text-sm font-medium text-slate-500">{title}</p>

            <div className="mt-3 flex items-end justify-between gap-2">
                <h3 className="text-3xl font-bold tracking-tight text-slate-900">
                    {value}
                </h3>

                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold ${style}`}>
                    <TrendIcon size={13} />
                    {change}
                </span>
            </div>

            <p className="mt-3 text-xs text-slate-400">{description}</p>
        </div>
    )
}
