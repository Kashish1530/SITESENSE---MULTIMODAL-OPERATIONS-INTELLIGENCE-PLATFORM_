
import { useId, useMemo, useState } from 'react'

export type BarChartItem = {
    id: string
    label: string
    value: number
    color?: string
}

type BarChartProps = {
    data: BarChartItem[]
    title?: string
    description?: string
    valueSuffix?: string
    emptyMessage?: string
}

const DEFAULT_COLOR = '#3b82f6'
const CHART_WIDTH = 720
const LEFT_PADDING = 190
const RIGHT_PADDING = 55
const ROW_HEIGHT = 48
const TOP_PADDING = 12

export default function BarChart({
    data,
    title,
    description,
    valueSuffix = '',
    emptyMessage = 'No data available for this period.',
}: BarChartProps) {
    const chartId = useId()
    const [activeId, setActiveId] = useState<string | null>(null)

    const chartData = useMemo(
        () => data.filter(
            item =>
                Number.isFinite(item.value) &&
                item.value >= 0,
        ),
        [data],
    )

    const selectedItem = activeId === null
        ? null
        : chartData.find(item => item.id === activeId) ?? null

    const maxValue = Math.max(
        1,
        ...chartData.map(item => item.value),
    )

    const chartHeight = Math.max(
        100,
        chartData.length * ROW_HEIGHT + TOP_PADDING * 2,
    )

    const availableWidth = CHART_WIDTH - LEFT_PADDING - RIGHT_PADDING

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
                        <p className="mt-1 text-sm text-slate-500">
                            {description}
                        </p>
                    )}
                </div>
            )}

            {chartData.length === 0 ? (
                <div className="flex min-h-40 items-center justify-center rounded-lg bg-slate-50 text-sm text-slate-400">
                    {emptyMessage}
                </div>
            ) : (
                <>
                    <div className="w-full overflow-x-auto">
                        <svg
                            viewBox={`0 0 ${CHART_WIDTH} ${chartHeight}`}
                            className="h-auto w-full"
                            role="img"
                            aria-labelledby={`${chartId}-title`}
                        >
                            <title id={`${chartId}-title`}>
                                {title ?? 'Bar chart'}
                            </title>

                            {chartData.map((item, index) => {
                                const y = TOP_PADDING + index * ROW_HEIGHT
                                const barWidth =
                                    (item.value / maxValue) * availableWidth

                                const itemId = item.id
                                const isActive = activeId === itemId

                                return (
                                    <g
                                        key={itemId}
                                        role="button"
                                        tabIndex={0}
                                        aria-label={`${item.label}: ${item.value}${valueSuffix}`}
                                        onMouseEnter={() => setActiveId(itemId)}
                                        onMouseLeave={() => setActiveId(null)}
                                        onFocus={() => setActiveId(itemId)}
                                        onBlur={() => setActiveId(null)}
                                        onClick={() =>
                                            setActiveId(isActive ? null : itemId)
                                        }
                                        onKeyDown={(event) => {
                                            if (event.key === 'Enter' || event.key === ' ') {
                                                event.preventDefault()
                                                setActiveId(isActive ? null : itemId)
                                            }
                                        }}
                                        className="cursor-pointer"
                                    >
                                        <text
                                            x={LEFT_PADDING - 12}
                                            y={y + 19}
                                            textAnchor="end"
                                            className="fill-slate-600 text-xs"
                                        >
                                            {item.label.length > 24
                                                ? `${item.label.slice(0, 22)}…`
                                                : item.label}
                                        </text>

                                        <rect
                                            x={LEFT_PADDING}
                                            y={y}
                                            width={availableWidth}
                                            height={26}
                                            rx={5}
                                            fill="#f1f5f9"
                                        />

                                        <rect
                                            x={LEFT_PADDING}
                                            y={y}
                                            width={Math.max(barWidth, item.value > 0 ? 2 : 0)}
                                            height={26}
                                            rx={5}
                                            fill={item.color ?? DEFAULT_COLOR}
                                            opacity={isActive ? 1 : 0.8}
                                        />

                                        <text
                                            x={LEFT_PADDING + availableWidth + 8}
                                            y={y + 18}
                                            className="fill-slate-600 text-xs"
                                        >
                                            {item.value}{valueSuffix}
                                        </text>
                                    </g>
                                )
                            })}
                        </svg>
                    </div>

                    {selectedItem && (
                        <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
                            <span className="font-semibold text-slate-800">
                                {selectedItem.label}
                            </span>
                            {' — '}
                            {selectedItem.value}{valueSuffix}
                        </div>
                    )}
                </>
            )}
        </section>
    )
}
