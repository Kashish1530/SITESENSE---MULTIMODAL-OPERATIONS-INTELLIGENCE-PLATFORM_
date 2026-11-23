
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
    cleanup,
    fireEvent,
    render,
    screen,
    within,
} from '@testing-library/react'

import ZoneDrawingEditor from '../../src/components/zones/ZoneDrawingEditor'
import type {
    BackgroundAsset,
    CountingLineDefinition,
    DetectionClassDefinition,
    ZoneDefinition,
} from '../../src/zones/zoneConfiguration'

const background: BackgroundAsset = {
    id: 'background-1',
    name: 'Warehouse background',
    type: 'image',
    mimeType: 'image/png',
    url: 'data:image/png;base64,dGVzdA==',
}

const availableClasses: DetectionClassDefinition[] = [
    {
        id: 'demo-person',
        displayName: 'Person',
        description: 'Person detection',
        status: 'active',
        supportedModelVersions: ['demo-model-v1'],
        illustrative: true,
    },
    {
        id: 'demo-vehicle',
        displayName: 'Vehicle',
        description: 'Vehicle detection',
        status: 'active',
        supportedModelVersions: ['demo-model-v1'],
        illustrative: true,
    },
]

const existingZone: ZoneDefinition = {
    id: 'zone-1',
    name: 'Loading Bay',
    description: 'Loading area',
    points: [
        { x: 10, y: 10 },
        { x: 80, y: 10 },
        { x: 40, y: 80 },
    ],
    detectionClassIds: ['demo-person'],
    enabled: true,
}

const existingLine: CountingLineDefinition = {
    id: 'line-1',
    name: 'Entry Line',
    start: { x: 20, y: 30 },
    end: { x: 80, y: 30 },
    direction: 'both',
    enabled: true,
}

function renderEditor({
    zones = [],
    countingLines = [],
    disabled = false,
    onZonesChange = vi.fn(),
    onCountingLinesChange = vi.fn(),
}: {
    zones?: ZoneDefinition[]
    countingLines?: CountingLineDefinition[]
    disabled?: boolean
    onZonesChange?: (zones: ZoneDefinition[]) => void
    onCountingLinesChange?: (lines: CountingLineDefinition[]) => void
} = {}) {
    const result = render(
        <ZoneDrawingEditor
            background={background}
            zones={zones}
            countingLines={countingLines}
            availableClasses={availableClasses}
            disabled={disabled}
            onZonesChange={onZonesChange}
            onCountingLinesChange={onCountingLinesChange}
        />,
    )

    const overlay = result.container.querySelector<SVGSVGElement>(
        'svg[aria-label="Zone drawing overlay"]',
    )

    if (!overlay) {
        throw new Error('Zone drawing overlay was not rendered.')
    }

    vi.spyOn(overlay, 'getBoundingClientRect').mockReturnValue({
        x: 0,
        y: 0,
        left: 0,
        top: 0,
        right: 100,
        bottom: 100,
        width: 100,
        height: 100,
        toJSON: () => ({}),
    })

    return {
        ...result,
        overlay,
        onZonesChange,
        onCountingLinesChange,
    }
}

function addTriangle(overlay: SVGSVGElement) {
    fireEvent.click(overlay, { clientX: 10, clientY: 10 })
    fireEvent.click(overlay, { clientX: 80, clientY: 10 })
    fireEvent.click(overlay, { clientX: 40, clientY: 80 })
}

function addCountingLinePoints(overlay: SVGSVGElement) {
    fireEvent.click(overlay, { clientX: 20, clientY: 30 })
    fireEvent.click(overlay, { clientX: 80, clientY: 30 })
}

afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
})

describe('ZoneDrawingEditor', () => {
    describe('zone creation', () => {
        it('creates a zone with three points, a name and a detection class', () => {
            const onZonesChange = vi.fn()
            const { overlay } = renderEditor({ onZonesChange })

            fireEvent.click(screen.getByRole('button', {
                name: 'Add Zone',
            }))

            addTriangle(overlay)

            fireEvent.change(screen.getByPlaceholderText('e.g. Loading Bay'), {
                target: { value: 'Loading Bay' },
            })

            fireEvent.click(screen.getByLabelText('Person'))
            fireEvent.click(screen.getByRole('button', {
                name: 'Finish Zone',
            }))

            expect(onZonesChange).toHaveBeenCalledOnce()

            const savedZones = onZonesChange.mock.calls[0][0]

            expect(savedZones).toHaveLength(1)
            expect(savedZones[0]).toMatchObject({
                name: 'Loading Bay',
                detectionClassIds: ['demo-person'],
                enabled: true,
            })
            expect(savedZones[0].points).toHaveLength(3)
            expect(screen.queryByText('Draw a new zone')).not.toBeInTheDocument()
        })

        it('validates the zone name, polygon and detection class', () => {
            const { overlay } = renderEditor()

            fireEvent.click(screen.getByRole('button', {
                name: 'Add Zone',
            }))

            fireEvent.click(screen.getByRole('button', {
                name: 'Finish Zone',
            }))

            expect(screen.getByRole('alert')).toHaveTextContent(
                'Enter a zone name.',
            )

            fireEvent.change(screen.getByPlaceholderText('e.g. Loading Bay'), {
                target: { value: 'Test Zone' },
            })

            fireEvent.click(overlay, { clientX: 10, clientY: 10 })
            fireEvent.click(overlay, { clientX: 80, clientY: 10 })

            fireEvent.click(screen.getByRole('button', {
                name: 'Finish Zone',
            }))

            expect(screen.getByRole('alert')).toHaveTextContent(
                'at least three distinct points',
            )

            fireEvent.click(overlay, { clientX: 40, clientY: 80 })

            fireEvent.click(screen.getByRole('button', {
                name: 'Finish Zone',
            }))

            expect(screen.getByRole('alert')).toHaveTextContent(
                'Select at least one detection class.',
            )
        })

        it('does not change zones when drawing is cancelled', () => {
            const onZonesChange = vi.fn()
            const { overlay } = renderEditor({ onZonesChange })

            fireEvent.click(screen.getByRole('button', {
                name: 'Add Zone',
            }))

            addTriangle(overlay)

            fireEvent.click(screen.getByRole('button', {
                name: 'Cancel',
            }))

            expect(onZonesChange).not.toHaveBeenCalled()
            expect(screen.getByText('No zones created yet.')).toBeInTheDocument()
        })
    })

    describe('zone editing', () => {
        it('updates an existing zone while preserving its ID', () => {
            const onZonesChange = vi.fn()

            renderEditor({
                zones: [existingZone],
                onZonesChange,
            })

            fireEvent.click(screen.getByRole('button', {
                name: 'Edit',
            }))

            expect(screen.getByDisplayValue('Loading Bay')).toBeInTheDocument()

            fireEvent.change(screen.getByPlaceholderText('e.g. Loading Bay'), {
                target: { value: 'Updated Loading Bay' },
            })

            fireEvent.click(screen.getByRole('button', {
                name: 'Update Zone',
            }))

            expect(onZonesChange).toHaveBeenCalledOnce()

            const updatedZones = onZonesChange.mock.calls[0][0]

            expect(updatedZones).toHaveLength(1)
            expect(updatedZones[0]).toMatchObject({
                id: 'zone-1',
                name: 'Updated Loading Bay',
                detectionClassIds: ['demo-person'],
            })
        })

        it('does not allow editing or deleting another zone while drawing', () => {
            renderEditor({ zones: [existingZone] })

            fireEvent.click(screen.getByRole('button', {
                name: 'Add Zone',
            }))

            expect(screen.getByRole('button', {
                name: 'Edit',
            })).toBeDisabled()

            expect(screen.getByRole('button', {
                name: 'Delete',
            })).toBeDisabled()
        })
    })

    describe('zone deletion', () => {
        it('deletes a zone after confirmation', () => {
            const onZonesChange = vi.fn()
            vi.spyOn(window, 'confirm').mockReturnValue(true)

            renderEditor({
                zones: [existingZone],
                onZonesChange,
            })

            fireEvent.click(screen.getByRole('button', {
                name: 'Delete',
            }))

            expect(window.confirm).toHaveBeenCalledOnce()
            expect(onZonesChange).toHaveBeenCalledWith([])
        })

        it('keeps a zone when deletion is cancelled', () => {
            const onZonesChange = vi.fn()
            vi.spyOn(window, 'confirm').mockReturnValue(false)

            renderEditor({
                zones: [existingZone],
                onZonesChange,
            })

            fireEvent.click(screen.getByRole('button', {
                name: 'Delete',
            }))

            expect(window.confirm).toHaveBeenCalledOnce()
            expect(onZonesChange).not.toHaveBeenCalled()
        })
    })

    describe('counting-line creation', () => {
        it('creates a counting line with two endpoints, a name and direction', () => {
            const onCountingLinesChange = vi.fn()
            const { overlay } = renderEditor({ onCountingLinesChange })

            fireEvent.click(screen.getByRole('button', {
                name: 'Add Counting Line',
            }))

            addCountingLinePoints(overlay)

            fireEvent.change(screen.getByLabelText('Counting line name'), {
                target: { value: 'Entry Counter' },
            })

            fireEvent.change(screen.getByLabelText('Crossing direction'), {
                target: { value: 'forward' },
            })

            fireEvent.click(screen.getByRole('button', {
                name: 'Finish Counting Line',
            }))

            expect(onCountingLinesChange).toHaveBeenCalledOnce()

            const savedLines = onCountingLinesChange.mock.calls[0][0]

            expect(savedLines).toHaveLength(1)
            expect(savedLines[0]).toMatchObject({
                name: 'Entry Counter',
                start: { x: 20, y: 30 },
                end: { x: 80, y: 30 },
                direction: 'forward',
                enabled: true,
            })
        })

        it('validates the line name, endpoint count and endpoint distance', () => {
            const { overlay } = renderEditor()

            fireEvent.click(screen.getByRole('button', {
                name: 'Add Counting Line',
            }))

            fireEvent.click(screen.getByRole('button', {
                name: 'Finish Counting Line',
            }))

            expect(screen.getByRole('alert')).toHaveTextContent(
                'Enter a counting line name.',
            )

            fireEvent.change(screen.getByLabelText('Counting line name'), {
                target: { value: 'Test Line' },
            })

            fireEvent.click(screen.getByRole('button', {
                name: 'Finish Counting Line',
            }))

            expect(screen.getByRole('alert')).toHaveTextContent(
                'Select exactly two points for the counting line.',
            )

            fireEvent.click(overlay, { clientX: 30, clientY: 30 })
            fireEvent.click(overlay, { clientX: 30, clientY: 30 })

            fireEvent.click(screen.getByRole('button', {
                name: 'Finish Counting Line',
            }))

            expect(screen.getByRole('alert')).toHaveTextContent(
                'The counting line endpoints must be different.',
            )
        })

        it('does not change counting lines when drawing is cancelled', () => {
            const onCountingLinesChange = vi.fn()
            const { overlay } = renderEditor({ onCountingLinesChange })

            fireEvent.click(screen.getByRole('button', {
                name: 'Add Counting Line',
            }))

            addCountingLinePoints(overlay)

            fireEvent.change(screen.getByLabelText('Counting line name'), {
                target: { value: 'Cancelled Line' },
            })

            fireEvent.click(screen.getByRole('button', {
                name: 'Cancel',
            }))

            expect(onCountingLinesChange).not.toHaveBeenCalled()
            expect(screen.getByText('No counting lines created yet.')).toBeInTheDocument()
        })
    })

    describe('counting-line editing', () => {
        it('updates an existing counting line while preserving its ID', () => {
            const onCountingLinesChange = vi.fn()

            renderEditor({
                countingLines: [existingLine],
                onCountingLinesChange,
            })

            const lineItem = screen
                .getAllByText('Entry Line')
                .find(element => element.tagName === 'P')
                ?.closest('li')

            if (!lineItem) {
                throw new Error('Counting line list item was not rendered.')
            }

            fireEvent.click(within(lineItem).getByRole('button', {
                name: 'Edit',
            }))

            expect(screen.getByDisplayValue('Entry Line')).toBeInTheDocument()

            fireEvent.change(screen.getByLabelText('Counting line name'), {
                target: { value: 'Updated Entry Line' },
            })

            fireEvent.change(screen.getByLabelText('Crossing direction'), {
                target: { value: 'backward' },
            })

            fireEvent.click(screen.getByRole('button', {
                name: 'Update Counting Line',
            }))

            expect(onCountingLinesChange).toHaveBeenCalledOnce()

            const updatedLines = onCountingLinesChange.mock.calls[0][0]

            expect(updatedLines).toHaveLength(1)
            expect(updatedLines[0]).toMatchObject({
                id: 'line-1',
                name: 'Updated Entry Line',
                direction: 'backward',
                enabled: true,
            })
        })
    })

    describe('counting-line deletion', () => {
        it('deletes a counting line after confirmation', () => {
            const onCountingLinesChange = vi.fn()
            vi.spyOn(window, 'confirm').mockReturnValue(true)

            renderEditor({
                countingLines: [existingLine],
                onCountingLinesChange,
            })

            const lineItem = screen
                .getAllByText('Entry Line')
                .find(element => element.tagName === 'P')
                ?.closest('li')

            if (!lineItem) {
                throw new Error('Counting line list item was not rendered.')
            }

            fireEvent.click(within(lineItem).getByRole('button', {
                name: 'Delete',
            }))

            expect(window.confirm).toHaveBeenCalledOnce()
            expect(onCountingLinesChange).toHaveBeenCalledWith([])
        })

        it('keeps a counting line when deletion is cancelled', () => {
            const onCountingLinesChange = vi.fn()
            vi.spyOn(window, 'confirm').mockReturnValue(false)

            renderEditor({
                countingLines: [existingLine],
                onCountingLinesChange,
            })

            const lineItem = screen
                .getAllByText('Entry Line')
                .find(element => element.tagName === 'P')
                ?.closest('li')

            if (!lineItem) {
                throw new Error('Counting line list item was not rendered.')
            }

            fireEvent.click(within(lineItem).getByRole('button', {
                name: 'Delete',
            }))

            expect(window.confirm).toHaveBeenCalledOnce()
            expect(onCountingLinesChange).not.toHaveBeenCalled()
        })
    })

    describe('view-only access', () => {
        it('does not show editing controls when disabled', () => {
            renderEditor({
                zones: [existingZone],
                countingLines: [existingLine],
                disabled: true,
            })

            expect(screen.queryByRole('button', {
                name: 'Add Zone',
            })).not.toBeInTheDocument()

            expect(screen.queryByRole('button', {
                name: 'Add Counting Line',
            })).not.toBeInTheDocument()

            expect(screen.queryByRole('button', {
                name: 'Edit',
            })).not.toBeInTheDocument()

            expect(screen.queryByRole('button', {
                name: 'Delete',
            })).not.toBeInTheDocument()
        })
    })

    describe('vertex dragging', () => {
        it('moves a vertex without adding an extra polygon point', () => {
            const { overlay } = renderEditor()

            fireEvent.click(screen.getByRole('button', {
                name: 'Add Zone',
            }))

            addTriangle(overlay)

            const firstVertex = overlay.querySelector('circle')

            expect(firstVertex).not.toBeNull()

            Object.defineProperty(overlay, 'setPointerCapture', {
                configurable: true,
                value: vi.fn(),
            })

            fireEvent.pointerDown(firstVertex!, {
                pointerId: 1,
                clientX: 10,
                clientY: 10,
            })

            fireEvent.pointerMove(overlay, {
                pointerId: 1,
                clientX: 50,
                clientY: 50,
            })

            fireEvent.pointerUp(overlay, {
                pointerId: 1,
                clientX: 50,
                clientY: 50,
            })

            fireEvent.click(overlay, {
                clientX: 50,
                clientY: 50,
            })

            expect(screen.getByText('3 points')).toBeInTheDocument()
            expect(firstVertex).toHaveAttribute('cx', '50')
            expect(firstVertex).toHaveAttribute('cy', '50')
        })
    })
})
