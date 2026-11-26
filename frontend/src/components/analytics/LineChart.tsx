
import { useId, useMemo, useState } from 'react'

export type LineChartSeries = {
    key: string
    label: string
    color: string
}

export type LineChartPoint = {
    id?: string
    label: string
    [key: string]: string | number | undefined
}

type ProcessedLineChartPoint = {
    id?: string
    label: string
    values: (number | null)[]
}

type LineChartProps = {
    data: LineChartPoint[]
    series: LineChartSeries[]
    title?: string
    description?: string
    height?: number
    emptyMessage?: string
}

const CHART_WIDTH = 720
const CHART_HEIGHT = 280

const PADDING = {
    top: 24,
    right: 24,
    bottom: 42,
    left: 42,
}

function getPointId(point: ProcessedLineChartPoint, index: number) {
    return point.id ?? `${point.label}-${index}`
}

export default function LineChart({
    data,
    series,
    title,
    description,
    height = 280,
    emptyMessage = 'No data available for this period.',
}: LineChartProps) {
    const chartId = useId()
    const [activeId, setActiveId] = useState<string | null>(null)

    const chartData = useMemo(() => {
        const validSeries = series.filter(
            item => item.key.trim() !== '',
        )

        const points: ProcessedLineChartPoint[] = data.map(point => ({
            id: point.id,
            label: point.label,
            values: validSeries.map(item => {
                const value = point[item.key]

                return typeof value === 'number' &&
                    Number.isFinite(value)
                    ? value
                    : null
            }),
        }))

        return {
            series: validSeries,
            points,
        }
    }, [data, series])

    const plotWidth = CHART_WIDTH - PADDING.left - PADDING.right
    const plotHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom

    const maxValue = Math.max(
        1,
        ...chartData.points.flatMap(point =>
            point.values.filter(
                (value): value is number => value !== null,
            ),
        ),
    )

    const roundedMax = Math.ceil(maxValue / 5) * 5

    const yTicks = Array.from(
        { length: 5 },
        (_, index) => roundedMax - (roundedMax / 4) * index,
    )

    function getX(index: number) {
        if (chartData.points.length <= 1) {
            return PADDING.left + plotWidth / 2
        }

        return PADDING.left +
            (index / (chartData.points.length - 1)) * plotWidth
    }

    function getY(value: number) {
        return PADDING.top +
            plotHeight -
            (value / roundedMax) * plotHeight
    }

    function createPath(seriesIndex: number) {
        let started = false

        return chartData.points
            .map((point, index) => {
                const value = point.values[seriesIndex]

                if (value === null) {
                    started = false
                    return null
                }

                const command = started ? 'L' : 'M'
                started = true

                return `${command} ${getX(index)} ${getY(value)}`
            })
            .filter((segment): segment is string => segment !== null)
            .join(' ')
    }

    const hasValues = chartData.points.some(
        point => point.values.some(value => value !== null),
    )

    const selectedPointIndex = chartData.points.findIndex(
        (point, index) => getPointId(point, index) === activeId,
    )

    const selectedPoint = selectedPointIndex >= 0
        ? chartData.points[selectedPointIndex]
        : null

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

            {!hasValues ? (
                <div
                    className="flex items-center justify-center rounded-lg bg-slate-50 text-sm text-slate-400"
                    style={{ minHeight: height }}
                >
                    {emptyMessage}
                </div>
            ) : (
                <>
                    <div className="relative w-full">
                        <svg
                            viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
                            role="img"
                            aria-labelledby={`${chartId}-title`}
                            className="w-full overflow-visible"
                            style={{ height: 'auto', maxHeight: height }}
                        >
                            <title id={`${chartId}-title`}>
                                {title ?? 'Line chart'}
                            </title>

                            {yTicks.map((tick, index) => {
                                const y =
                                    PADDING.top +
                                    (plotHeight / 4) * index

                                return (
                                    <g key={index}>
                                        <line
                                            x1={PADDING.left}
                                            x2={CHART_WIDTH - PADDING.right}
                                            y1={y}
                                            y2={y}
                                            stroke="#e2e8f0"
                                            strokeDasharray="4 5"
                                        />

                                        <text
                                            x={PADDING.left - 10}
                                            y={y + 4}
                                            textAnchor="end"
                                            fontSize="11"
                                            fill="#94a3b8"
                                        >
                                            {Math.round(tick)}
                                        </text>
                                    </g>
                                )
                            })}

                            {chartData.points.map((point, index) => (
                                <text
                                    key={getPointId(point, index)}
                                    x={getX(index)}
                                    y={CHART_HEIGHT - 12}
                                    textAnchor="middle"
                                    fontSize="11"
                                    fill="#94a3b8"
                                >
                                    {point.label}
                                </text>
                            ))}

                            {chartData.series.map((item, index) => (
                                <path
                                    key={item.key}
                                    d={createPath(index)}
                                    fill="none"
                                    stroke={item.color}
                                    strokeWidth="3"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                />
                            ))}

                            {chartData.series.map((item, seriesIndex) => (
                                <g key={item.key}>
                                    {chartData.points.map((point, index) => {
                                        const value = point.values[seriesIndex]

                                        if (value === null) return null

                                        return (
                                            <circle
                                                key={getPointId(point, index)}
                                                cx={getX(index)}
                                                cy={getY(value)}
                                                r={
                                                    activeId === getPointId(point, index)
                                                        ? 6
                                                        : 4
                                                }
                                                fill={item.color}
                                                stroke="white"
                                                strokeWidth="2"
                                            />
                                        )
                                    })}
                                </g>
                            ))}

                            {chartData.points.map((point, index) => {
                                const pointId = getPointId(point, index)
                                const isActive = activeId === pointId
                                const pointWidth =
                                    plotWidth /
                                    Math.max(chartData.points.length, 2)

                                return (
                                    <rect
                                        key={pointId}
                                        x={getX(index) - pointWidth / 2}
                                        y={PADDING.top}
                                        width={pointWidth}
                                        height={plotHeight}
                                        fill="transparent"
                                        role="button"
                                        tabIndex={0}
                                        aria-label={`Show data for ${point.label}`}
                                        onMouseEnter={() => setActiveId(pointId)}
                                        onMouseLeave={() => setActiveId(null)}
                                        onFocus={() => setActiveId(pointId)}
                                        onBlur={() => setActiveId(null)}
                                        onClick={() =>
                                            setActiveId(isActive ? null : pointId)
                                        }
                                        onKeyDown={event => {
                                            if (
                                                event.key === 'Enter' ||
                                                event.key === ' '
                                            ) {
                                                event.preventDefault()
                                                setActiveId(
                                                    isActive ? null : pointId,
                                                )
                                            }
                                        }}
                                    />
                                )
                            })}
                        </svg>
                    </div>

                    {selectedPoint && (
                        <div className="mt-2 rounded-lg bg-slate-50 p-3">
                            <p className="mb-2 text-xs font-semibold text-slate-700">
                                {selectedPoint.label}
                            </p>

                            <div className="flex flex-wrap gap-x-5 gap-y-2">
                                {chartData.series.map((item, index) => (
                                    <div
                                        key={item.key}
                                        className="flex items-center gap-2 text-xs text-slate-600"
                                    >
                                        <span
                                            className="h-2.5 w-2.5 rounded-full"
                                            style={{ backgroundColor: item.color }}
                                        />
                                        {item.label}:{' '}
                                        {selectedPoint.values[index] ?? '—'}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="mt-5 flex flex-wrap gap-5">
                        {chartData.series.map(item => (
                            <div
                                key={item.key}
                                className="flex items-center gap-2 text-xs text-slate-500"
                            >
                                <span
                                    className="h-2.5 w-2.5 rounded-full"
                                    style={{ backgroundColor: item.color }}
                                />
                                {item.label}
                            </div>
                        ))}
                    </div>
                </>
            )}
        </section>
    )
}
