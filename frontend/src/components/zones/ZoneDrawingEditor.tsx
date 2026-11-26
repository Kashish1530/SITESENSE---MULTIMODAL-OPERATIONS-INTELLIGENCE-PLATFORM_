
import { useRef, useState } from 'react'
import type { MouseEvent, PointerEvent } from 'react'
import type {
    BackgroundAsset,
    CountingLineDefinition,
    DetectionClassDefinition,
    Point2D,
    ZoneDefinition,
} from '../../zones/zoneConfiguration'
import {
    getNormalizedPoint,
    isValidPolygon,
} from '../../zones/zoneGeometry'

type ZoneDrawingEditorProps = {
    background: BackgroundAsset
    zones: ZoneDefinition[]
    availableClasses: DetectionClassDefinition[]
    countingLines?: CountingLineDefinition[]
    disabled?: boolean
    onZonesChange: (zones: ZoneDefinition[]) => void
    onCountingLinesChange?: (lines: CountingLineDefinition[]) => void
}

type LineDirection = CountingLineDefinition['direction']

export default function ZoneDrawingEditor({
    background,
    zones,
    availableClasses,
    countingLines = [],
    disabled = false,
    onZonesChange,
    onCountingLinesChange = () => { },
}: ZoneDrawingEditorProps) {
    const [drawing, setDrawing] = useState(false)
    const [draftPoints, setDraftPoints] = useState<Point2D[]>([])
    const [draftName, setDraftName] = useState('')
    const [draftDescription, setDraftDescription] = useState('')
    const [draftClassIds, setDraftClassIds] = useState<string[]>([])
    const [editingZoneId, setEditingZoneId] = useState<string | null>(null)

    const [drawingLine, setDrawingLine] = useState(false)
    const [draftLinePoints, setDraftLinePoints] = useState<Point2D[]>([])
    const [draftLineName, setDraftLineName] = useState('')
    const [draftLineDirection, setDraftLineDirection] =
        useState<LineDirection>('both')
    const [editingLineId, setEditingLineId] = useState<string | null>(null)

    const [draggingPointIndex, setDraggingPointIndex] =
        useState<number | null>(null)
    const [error, setError] = useState('')

    const draggingPointIndexRef = useRef<number | null>(null)
    const suppressNextClickRef = useRef(false)

    const selectedZone = zones.find(zone => zone.id === editingZoneId)
    const selectedLine = countingLines.find(line => line.id === editingLineId)

    const isDrawing = drawing || drawingLine

    function resetPointerState() {
        draggingPointIndexRef.current = null
        suppressNextClickRef.current = false
        setDraggingPointIndex(null)
    }

    function startNewZone() {
        if (disabled || isDrawing) return

        resetPointerState()
        setEditingZoneId(null)
        setDraftPoints([])
        setDraftName('')
        setDraftDescription('')
        setDraftClassIds([])
        setError('')
        setDrawing(true)
    }

    function editZone(zone: ZoneDefinition) {
        if (disabled || isDrawing) return

        resetPointerState()
        setEditingZoneId(zone.id)
        setDraftPoints(zone.points.map(point => ({ ...point })))
        setDraftName(zone.name)
        setDraftDescription(zone.description ?? '')
        setDraftClassIds([...zone.detectionClassIds])
        setError('')
        setDrawing(true)
    }

    function cancelDrawing() {
        setDrawing(false)
        setDraftPoints([])
        setEditingZoneId(null)
        resetPointerState()
        setError('')
    }

    function startNewLine() {
        if (disabled || isDrawing) return

        resetPointerState()
        setEditingLineId(null)
        setDraftLinePoints([])
        setDraftLineName('')
        setDraftLineDirection('both')
        setError('')
        setDrawingLine(true)
    }

    function editLine(line: CountingLineDefinition) {
        if (disabled || isDrawing) return

        resetPointerState()
        setEditingLineId(line.id)
        setDraftLinePoints([
            { ...line.start },
            { ...line.end },
        ])
        setDraftLineName(line.name)
        setDraftLineDirection(line.direction)
        setError('')
        setDrawingLine(true)
    }

    function cancelLineDrawing() {
        setDrawingLine(false)
        setDraftLinePoints([])
        setEditingLineId(null)
        resetPointerState()
        setError('')
    }

    function addZonePoint(event: MouseEvent<SVGSVGElement>) {
        if (!drawing) return

        if (suppressNextClickRef.current) {
            suppressNextClickRef.current = false
            return
        }

        if (draggingPointIndexRef.current !== null) return

        const bounds = event.currentTarget.getBoundingClientRect()
        const point = getNormalizedPoint(
            event.clientX,
            event.clientY,
            bounds,
        )

        if (!point) return

        setDraftPoints(previous => [...previous, point])
        setError('')
    }

    function addLinePoint(event: MouseEvent<SVGSVGElement>) {
        if (!drawingLine || draftLinePoints.length >= 2) return

        const bounds = event.currentTarget.getBoundingClientRect()
        const point = getNormalizedPoint(
            event.clientX,
            event.clientY,
            bounds,
        )

        if (!point) return

        setDraftLinePoints(previous => [...previous, point])
        setError('')
    }

    function handleOverlayClick(event: MouseEvent<SVGSVGElement>) {
        if (drawing) {
            addZonePoint(event)
        } else if (drawingLine) {
            addLinePoint(event)
        }
    }

    function startDraggingPoint(
        event: PointerEvent<SVGCircleElement>,
        index: number,
    ) {
        if (!drawing) return

        event.preventDefault()
        event.stopPropagation()

        draggingPointIndexRef.current = index
        suppressNextClickRef.current = true
        setDraggingPointIndex(index)

        event.currentTarget.ownerSVGElement?.setPointerCapture(
            event.pointerId,
        )
    }

    function movePoint(event: PointerEvent<SVGSVGElement>) {
        const activeIndex = draggingPointIndexRef.current

        if (activeIndex === null) return

        const bounds = event.currentTarget.getBoundingClientRect()
        const point = getNormalizedPoint(
            event.clientX,
            event.clientY,
            bounds,
        )

        if (!point) return

        setDraftPoints(previous => previous.map((existing, index) =>
            index === activeIndex ? point : existing,
        ))
    }

    function stopDraggingPoint() {
        if (draggingPointIndexRef.current === null) return

        suppressNextClickRef.current = true
        draggingPointIndexRef.current = null
        setDraggingPointIndex(null)
    }

    function cancelPointerInteraction() {
        draggingPointIndexRef.current = null
        suppressNextClickRef.current = false
        setDraggingPointIndex(null)
    }

    function toggleClass(classId: string) {
        setDraftClassIds(previous =>
            previous.includes(classId)
                ? previous.filter(id => id !== classId)
                : [...previous, classId],
        )
    }

    function finishZone() {
        const name = draftName.trim()

        if (!name) {
            setError('Enter a zone name.')
            return
        }

        if (!isValidPolygon(draftPoints)) {
            setError(
                'Add at least three distinct points to create a valid zone.',
            )
            return
        }

        if (draftClassIds.length === 0) {
            setError('Select at least one detection class.')
            return
        }

        const updatedZone: ZoneDefinition = {
            id: editingZoneId ?? crypto.randomUUID(),
            name,
            description: draftDescription.trim() || undefined,
            points: draftPoints.map(point => ({ ...point })),
            detectionClassIds: [...draftClassIds],
            enabled: selectedZone?.enabled ?? true,
        }

        const nextZones = editingZoneId
            ? zones.map(zone =>
                zone.id === editingZoneId ? updatedZone : zone,
            )
            : [...zones, updatedZone]

        onZonesChange(nextZones)
        cancelDrawing()
    }

    function finishLine() {
        const name = draftLineName.trim()

        if (!name) {
            setError('Enter a counting line name.')
            return
        }

        if (draftLinePoints.length !== 2) {
            setError('Select exactly two points for the counting line.')
            return
        }

        const [start, end] = draftLinePoints
        const distance = Math.hypot(end.x - start.x, end.y - start.y)

        if (distance < 0.5) {
            setError('The counting line endpoints must be different.')
            return
        }

        const updatedLine: CountingLineDefinition = {
            id: editingLineId ?? crypto.randomUUID(),
            name,
            start: { ...start },
            end: { ...end },
            direction: draftLineDirection,
            enabled: selectedLine?.enabled ?? true,
        }

        const nextLines = editingLineId
            ? countingLines.map(line =>
                line.id === editingLineId ? updatedLine : line,
            )
            : [...countingLines, updatedLine]

        onCountingLinesChange(nextLines)
        cancelLineDrawing()
    }

    function deleteZone(zone: ZoneDefinition) {
        if (disabled || isDrawing) return

        const confirmed = window.confirm(
            `Delete zone "${zone.name}"? This change will remain unsaved until you save the configuration.`,
        )

        if (!confirmed) return

        onZonesChange(zones.filter(item => item.id !== zone.id))
    }

    function deleteLine(line: CountingLineDefinition) {
        if (disabled || isDrawing) return

        const confirmed = window.confirm(
            `Delete counting line "${line.name}"? This change will remain unsaved until you save the configuration.`,
        )

        if (!confirmed) return

        onCountingLinesChange(
            countingLines.filter(item => item.id !== line.id),
        )
    }

    function directionLabel(direction: LineDirection) {
        if (direction === 'forward') return 'Forward'
        if (direction === 'backward') return 'Backward'
        return 'Both directions'
    }

    return (
        <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                    <h3 className="font-semibold text-slate-900">
                        Zone and Counting Line Editor
                    </h3>
                    <p className="text-sm text-slate-500">
                        Configure polygon zones and counting lines over the background.
                    </p>
                </div>

                {!disabled && !isDrawing && (
                    <div className="flex flex-wrap gap-2">
                        <button
                            type="button"
                            onClick={startNewZone}
                            className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
                        >
                            Add Zone
                        </button>
                        <button
                            type="button"
                            onClick={startNewLine}
                            className="rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white hover:bg-violet-700"
                        >
                            Add Counting Line
                        </button>
                    </div>
                )}
            </div>

            <div className="flex justify-center overflow-hidden rounded-lg border border-slate-200 bg-slate-50 p-2">
                <div className="relative inline-block max-h-72 max-w-full">
                    <img
                        src={background.url}
                        alt={background.name}
                        draggable={false}
                        className="block max-h-72 max-w-full object-contain"
                    />

                    <svg
                        viewBox="0 0 100 100"
                        preserveAspectRatio="none"
                        className={`absolute inset-0 h-full w-full ${isDrawing ? 'cursor-crosshair' : ''
                            }`}
                        onClick={handleOverlayClick}
                        onPointerMove={movePoint}
                        onPointerUp={stopDraggingPoint}
                        onPointerCancel={cancelPointerInteraction}
                        role="img"
                        aria-label="Zone drawing overlay"
                    >
                        {zones
                            .filter(zone => zone.id !== editingZoneId)
                            .map(zone => (
                                <g key={zone.id}>
                                    <polygon
                                        points={zone.points.map(point =>
                                            `${point.x},${point.y}`,
                                        ).join(' ')}
                                        fill="rgba(37, 99, 235, 0.18)"
                                        stroke="#2563eb"
                                        strokeWidth="0.6"
                                        vectorEffect="non-scaling-stroke"
                                    />
                                    <text
                                        x={zone.points[0]?.x ?? 0}
                                        y={zone.points[0]?.y ?? 0}
                                        fill="#1d4ed8"
                                        fontSize="3"
                                        vectorEffect="non-scaling-stroke"
                                    >
                                        {zone.name}
                                    </text>
                                </g>
                            ))}

                        {countingLines
                            .filter(line => line.id !== editingLineId)
                            .map(line => (
                                <g
                                    key={line.id}
                                    opacity={line.enabled ? 1 : 0.4}
                                >
                                    <line
                                        x1={line.start.x}
                                        y1={line.start.y}
                                        x2={line.end.x}
                                        y2={line.end.y}
                                        stroke="#7c3aed"
                                        strokeWidth="1.2"
                                        vectorEffect="non-scaling-stroke"
                                    />
                                    <circle
                                        cx={line.start.x}
                                        cy={line.start.y}
                                        r="1.2"
                                        fill="#ffffff"
                                        stroke="#6d28d9"
                                        strokeWidth="0.7"
                                        vectorEffect="non-scaling-stroke"
                                    />
                                    <circle
                                        cx={line.end.x}
                                        cy={line.end.y}
                                        r="1.2"
                                        fill="#7c3aed"
                                        stroke="#ffffff"
                                        strokeWidth="0.5"
                                        vectorEffect="non-scaling-stroke"
                                    />
                                    <text
                                        x={(line.start.x + line.end.x) / 2}
                                        y={(line.start.y + line.end.y) / 2 - 2}
                                        fill="#6d28d9"
                                        fontSize="3"
                                        textAnchor="middle"
                                        vectorEffect="non-scaling-stroke"
                                    >
                                        {line.name}
                                    </text>
                                </g>
                            ))}

                        {draftLinePoints.length > 0 && (
                            <g>
                                {draftLinePoints.length === 2 && (
                                    <line
                                        x1={draftLinePoints[0].x}
                                        y1={draftLinePoints[0].y}
                                        x2={draftLinePoints[1].x}
                                        y2={draftLinePoints[1].y}
                                        stroke="#a855f7"
                                        strokeWidth="1.4"
                                        strokeDasharray="3 2"
                                        vectorEffect="non-scaling-stroke"
                                    />
                                )}
                                {draftLinePoints.map((point, index) => (
                                    <circle
                                        key={index}
                                        cx={point.x}
                                        cy={point.y}
                                        r="1.5"
                                        fill={index === 0 ? '#ffffff' : '#a855f7'}
                                        stroke="#6d28d9"
                                        strokeWidth="0.8"
                                        vectorEffect="non-scaling-stroke"
                                    />
                                ))}
                            </g>
                        )}

                        {draftPoints.length > 0 && (
                            <g>
                                {draftPoints.length >= 3 && (
                                    <polygon
                                        points={draftPoints.map(point =>
                                            `${point.x},${point.y}`,
                                        ).join(' ')}
                                        fill="rgba(16, 185, 129, 0.18)"
                                        stroke="#059669"
                                        strokeWidth="0.7"
                                        vectorEffect="non-scaling-stroke"
                                    />
                                )}

                                {draftPoints.length >= 2 && (
                                    <polyline
                                        points={draftPoints.map(point =>
                                            `${point.x},${point.y}`,
                                        ).join(' ')}
                                        fill="none"
                                        stroke="#059669"
                                        strokeWidth="0.7"
                                        vectorEffect="non-scaling-stroke"
                                    />
                                )}

                                {draftPoints.map((point, index) => (
                                    <circle
                                        key={index}
                                        cx={point.x}
                                        cy={point.y}
                                        r="1.2"
                                        fill="#ffffff"
                                        stroke="#047857"
                                        strokeWidth="0.7"
                                        vectorEffect="non-scaling-stroke"
                                        className="cursor-move"
                                        onPointerDown={event =>
                                            startDraggingPoint(event, index)
                                        }
                                    />
                                ))}
                            </g>
                        )}
                    </svg>
                </div>
            </div>

            {drawing && (
                <div className="space-y-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-medium text-emerald-900">
                            {editingZoneId ? 'Edit zone boundary' : 'Draw a new zone'}
                        </p>
                        <span className="text-xs text-emerald-800">
                            {draftPoints.length} points
                        </span>
                    </div>

                    <p className="text-xs text-emerald-800">
                        Click the image to add points. Drag a point to adjust it.
                        A valid polygon needs at least three distinct points.
                    </p>

                    <div className="flex flex-wrap gap-2">
                        <button
                            type="button"
                            onClick={() =>
                                setDraftPoints(previous => previous.slice(0, -1))
                            }
                            disabled={
                                draftPoints.length === 0 ||
                                draggingPointIndex !== null
                            }
                            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm disabled:opacity-40"
                        >
                            Undo last point
                        </button>
                        <button
                            type="button"
                            onClick={() => setDraftPoints([])}
                            disabled={
                                draftPoints.length === 0 ||
                                draggingPointIndex !== null
                            }
                            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm disabled:opacity-40"
                        >
                            Clear points
                        </button>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                        <label className="block text-sm font-medium text-slate-700">
                            Zone name
                            <input
                                value={draftName}
                                onChange={event => setDraftName(event.target.value)}
                                maxLength={80}
                                placeholder="e.g. Loading Bay"
                                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-normal"
                            />
                        </label>

                        <label className="block text-sm font-medium text-slate-700">
                            Description (optional)
                            <input
                                value={draftDescription}
                                onChange={event =>
                                    setDraftDescription(event.target.value)
                                }
                                maxLength={200}
                                placeholder="Describe this zone"
                                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-normal"
                            />
                        </label>
                    </div>

                    <fieldset className="space-y-2">
                        <legend className="text-sm font-medium text-slate-700">
                            Detection classes
                        </legend>
                        <div className="grid gap-2 sm:grid-cols-2">
                            {availableClasses.map(item => (
                                <label
                                    key={item.id}
                                    className="flex items-center gap-2 text-sm text-slate-700"
                                >
                                    <input
                                        type="checkbox"
                                        checked={draftClassIds.includes(item.id)}
                                        onChange={() => toggleClass(item.id)}
                                    />
                                    {item.displayName}
                                </label>
                            ))}
                        </div>
                    </fieldset>

                    {error && (
                        <p role="alert" className="text-sm text-red-700">
                            {error}
                        </p>
                    )}

                    <div className="flex flex-wrap gap-2">
                        <button
                            type="button"
                            onClick={finishZone}
                            disabled={draggingPointIndex !== null}
                            className="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            {editingZoneId ? 'Update Zone' : 'Finish Zone'}
                        </button>
                        <button
                            type="button"
                            onClick={cancelDrawing}
                            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {drawingLine && (
                <div className="space-y-3 rounded-lg border border-violet-200 bg-violet-50 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-medium text-violet-900">
                            {editingLineId
                                ? 'Edit counting line'
                                : 'Draw a counting line'}
                        </p>
                        <span className="text-xs text-violet-800">
                            {draftLinePoints.length}/2 endpoints
                        </span>
                    </div>

                    <p className="text-xs text-violet-800">
                        Click the background twice: first for the start point,
                        then for the end point.
                    </p>

                    <label className="block text-sm font-medium text-slate-700">
                        Counting line name
                        <input
                            value={draftLineName}
                            onChange={event =>
                                setDraftLineName(event.target.value)
                            }
                            maxLength={80}
                            placeholder="e.g. Main Entrance"
                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-normal"
                        />
                    </label>

                    <label className="block text-sm font-medium text-slate-700">
                        Crossing direction
                        <select
                            value={draftLineDirection}
                            onChange={event =>
                                setDraftLineDirection(
                                    event.target.value as LineDirection,
                                )
                            }
                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-normal"
                        >
                            <option value="both">Both directions</option>
                            <option value="forward">Forward</option>
                            <option value="backward">Backward</option>
                        </select>
                    </label>

                    <div className="flex flex-wrap gap-2">
                        <button
                            type="button"
                            onClick={() =>
                                setDraftLinePoints(previous => previous.slice(0, -1))
                            }
                            disabled={draftLinePoints.length === 0}
                            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm disabled:opacity-40"
                        >
                            Undo last endpoint
                        </button>
                        <button
                            type="button"
                            onClick={() => setDraftLinePoints([])}
                            disabled={draftLinePoints.length === 0}
                            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm disabled:opacity-40"
                        >
                            Clear endpoints
                        </button>
                    </div>

                    {error && (
                        <p role="alert" className="text-sm text-red-700">
                            {error}
                        </p>
                    )}

                    <div className="flex flex-wrap gap-2">
                        <button
                            type="button"
                            onClick={finishLine}
                            className="rounded-lg bg-violet-700 px-3 py-2 text-sm font-medium text-white hover:bg-violet-800"
                        >
                            {editingLineId
                                ? 'Update Counting Line'
                                : 'Finish Counting Line'}
                        </button>
                        <button
                            type="button"
                            onClick={cancelLineDrawing}
                            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            <div className="space-y-2">
                <h4 className="text-sm font-semibold text-slate-800">
                    Configured zones ({zones.length})
                </h4>

                {zones.length === 0 ? (
                    <p className="text-sm text-slate-500">
                        No zones created yet.
                    </p>
                ) : (
                    <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
                        {zones.map(zone => (
                            <li
                                key={zone.id}
                                className="flex flex-wrap items-center justify-between gap-2 p-3"
                            >
                                <div>
                                    <p className="text-sm font-medium text-slate-800">
                                        {zone.name}
                                    </p>
                                    <p className="text-xs text-slate-500">
                                        {zone.points.length} vertices · {zone.detectionClassIds.length} classes
                                    </p>
                                </div>

                                {!disabled && (
                                    <div className="flex gap-2">
                                        <button
                                            type="button"
                                            onClick={() => editZone(zone)}
                                            disabled={isDrawing}
                                            className="rounded-md border border-slate-300 px-2 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-40"
                                        >
                                            Edit
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => deleteZone(zone)}
                                            disabled={isDrawing}
                                            className="rounded-md border border-red-200 px-2 py-1 text-xs text-red-700 disabled:cursor-not-allowed disabled:opacity-40"
                                        >
                                            Delete
                                        </button>
                                    </div>
                                )}
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            <div className="space-y-2">
                <h4 className="text-sm font-semibold text-slate-800">
                    Counting lines ({countingLines.length})
                </h4>

                {countingLines.length === 0 ? (
                    <p className="text-sm text-slate-500">
                        No counting lines created yet.
                    </p>
                ) : (
                    <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
                        {countingLines.map(line => (
                            <li
                                key={line.id}
                                className="flex flex-wrap items-center justify-between gap-2 p-3"
                            >
                                <div>
                                    <p className="text-sm font-medium text-slate-800">
                                        {line.name}
                                    </p>
                                    <p className="text-xs text-slate-500">
                                        {directionLabel(line.direction)}
                                        {!line.enabled ? ' · Disabled' : ''}
                                    </p>
                                </div>

                                {!disabled && (
                                    <div className="flex gap-2">
                                        <button
                                            type="button"
                                            onClick={() => editLine(line)}
                                            disabled={isDrawing}
                                            className="rounded-md border border-slate-300 px-2 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-40"
                                        >
                                            Edit
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => deleteLine(line)}
                                            disabled={isDrawing}
                                            className="rounded-md border border-red-200 px-2 py-1 text-xs text-red-700 disabled:cursor-not-allowed disabled:opacity-40"
                                        >
                                            Delete
                                        </button>
                                    </div>
                                )}
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </section>
    )
}
