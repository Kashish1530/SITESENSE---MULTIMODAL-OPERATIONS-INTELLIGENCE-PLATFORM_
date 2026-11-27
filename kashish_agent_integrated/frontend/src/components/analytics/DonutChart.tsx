
import { useId, useMemo, useState } from 'react'

export type DonutChartItem = {
    label: string
    value: number
    color: string
}

type DonutChartProps = {
    data: DonutChartItem[]
    title?: string
    description?: string
    centerLabel?: string
    centerValue?: string
    emptyMessage?: string
}

type DonutChartSegment = DonutChartItem & {
    percentage: number
    offset: number
    key: string
}

const SIZE = 220
const CENTER = SIZE / 2
const RADIUS = 76
const STROKE_WIDTH = 24
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

export default function DonutChart({
    data,
    title,
    description,
    centerLabel = 'Total',
    centerValue,
    emptyMessage = 'No data available for this period.',
}: DonutChartProps) {
    const chartId = useId()
    const [activeItemKey, setActiveItemKey] = useState<string | null>(null)

    const chartData = useMemo(
        () => data.filter(
            item =>
                Number.isFinite(item.value) &&
                item.value >= 0,
        ),
        [data],
    )

    const total = chartData.reduce(
        (sum, item) => sum + item.value,
        0,
    )

    const { segments } = chartData.reduce<{
        segments: DonutChartSegment[]
        accumulated: number
    }>(
        (result, item, index) => {
            const percentage = total > 0
                ? item.value / total
                : 0

            const segment: DonutChartSegment = {
                ...item,
                percentage,
                offset: result.accumulated,
                key: `${index}-${item.label}-${item.value}-${item.color}`,
            }

            return {
                segments: [...result.segments, segment],
                accumulated: result.accumulated + percentage,
            }
        },
        {
            segments: [],
            accumulated: 0,
        },
    )

    const activeItem =
        segments.find(segment => segment.key === activeItemKey) ?? null

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            {(title || description) && (
                <div className="mb-5">
                    {title && (
                        <h3 className="font-semibold text-slate-900">
                            {title}
                        </h3>
                    )}

                    {description && (
                        <p className="mt-1 text-xs text-slate-400">
                            {description}
                        </p>
                    )}
                </div>
            )}

            {total <= 0 ? (
                <div className="flex min-h-52 items-center justify-center rounded-lg bg-slate-50 text-sm text-slate-400">
                    {emptyMessage}
                </div>
            ) : (
                <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-around">
                    <div className="relative shrink-0">
                        <svg
                            viewBox={`0 0 ${SIZE} ${SIZE}`}
                            className="w-full max-w-[220px]"
                            role="img"
                            aria-labelledby={`${chartId}-title`}
                        >
                            <title id={`${chartId}-title`}>
                                {title ?? 'Donut chart'}
                            </title>

                            <circle
                                cx={CENTER}
                                cy={CENTER}
                                r={RADIUS}
                                fill="none"
                                stroke="#f1f5f9"
                                strokeWidth={STROKE_WIDTH}
                            />

                            {segments.map(segment => {
                                if (segment.value === 0) return null

                                const length =
                                    segment.percentage * CIRCUMFERENCE

                                const isActive = activeItemKey === segment.key

                                return (
                                    <circle
                                        key={segment.key}
                                        cx={CENTER}
                                        cy={CENTER}
                                        r={RADIUS}
                                        fill="none"
                                        stroke={segment.color}
                                        strokeWidth={
                                            isActive
                                                ? STROKE_WIDTH + 5
                                                : STROKE_WIDTH
                                        }
                                        strokeDasharray={`${length} ${CIRCUMFERENCE - length}`}
                                        strokeDashoffset={
                                            -segment.offset * CIRCUMFERENCE
                                        }
                                        strokeLinecap="butt"
                                        transform={`rotate(-90 ${CENTER} ${CENTER})`}
                                        className="transition-all duration-200"
                                    />
                                )
                            })}
                        </svg>

                        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                            <span className="text-3xl font-bold text-slate-900">
                                {centerValue ?? total}
                            </span>
                            <span className="mt-1 text-xs text-slate-400">
                                {centerLabel}
                            </span>
                        </div>
                    </div>

                    <div className="w-full min-w-0 space-y-3">
                        {segments.map(item => (
                            <button
                                key={item.key}
                                type="button"
                                onMouseEnter={() => setActiveItemKey(item.key)}
                                onMouseLeave={() => setActiveItemKey(null)}
                                onFocus={() => setActiveItemKey(item.key)}
                                onBlur={() => setActiveItemKey(null)}
                                onClick={() =>
                                    setActiveItemKey(
                                        activeItemKey === item.key
                                            ? null
                                            : item.key,
                                    )
                                }
                                className="flex w-full items-center justify-between gap-3 rounded-lg px-2 py-1.5 text-left transition hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-blue-500"
                            >
                                <span className="flex min-w-0 items-center gap-2">
                                    <span
                                        className="h-3 w-3 shrink-0 rounded-full"
                                        style={{
                                            backgroundColor: item.color,
                                        }}
                                    />
                                    <span className="truncate text-sm text-slate-600">
                                        {item.label}
                                    </span>
                                </span>

                                <span className="shrink-0 text-sm font-semibold text-slate-800">
                                    {item.value}
                                    <span className="ml-2 text-xs font-normal text-slate-400">
                                        {(item.percentage * 100).toFixed(1)}%
                                    </span>
                                </span>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {activeItem && (
                <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
                    <span className="font-semibold text-slate-800">
                        {activeItem.label}
                    </span>
                    {' — '}
                    {activeItem.value} records (
                    {(activeItem.percentage * 100).toFixed(1)}%)
                </div>
            )}
        </section>
    )
}
