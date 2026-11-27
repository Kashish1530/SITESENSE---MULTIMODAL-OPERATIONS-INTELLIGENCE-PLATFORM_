
import { describe, expect, it } from 'vitest'

import {
    createClassSnapshots,
    createWorkingCopy,
    getAvailableDetectionClasses,
    getDetectionClassById,
    replaceBackground,
    saveWorkingCopy,
    discardWorkingCopy,
    updateWorkingCopy,
    type BackgroundAsset,
    type ZoneConfiguration,
} from '../../src/zones/zoneConfiguration'

const createConfiguration = (): ZoneConfiguration => ({
    id: 'config-1',
    siteId: 'SITE-001',
    siteName: 'North Warehouse',
    cameraId: 'camera-1',
    cameraName: 'Entrance Camera',
    modelVersion: 'demo-model-v1',
    background: {
        id: 'background-1',
        name: 'entrance.jpg',
        type: 'image',
        mimeType: 'image/jpeg',
        url: 'blob:entrance',
    },
    zones: [
        {
            id: 'zone-1',
            name: 'Loading Area',
            points: [
                { x: 10, y: 10 },
                { x: 90, y: 10 },
                { x: 90, y: 90 },
            ],
            detectionClassIds: ['demo-person'],
            enabled: true,
        },
    ],
    countingLines: [
        {
            id: 'line-1',
            name: 'Entry Line',
            start: { x: 20, y: 50 },
            end: { x: 80, y: 50 },
            direction: 'both',
            enabled: true,
        },
    ],
    detectionClasses: [
        {
            id: 'demo-person',
            displayName: 'Person',
            description: 'Illustrative person detection class',
        },
    ],
    createdAt: '2026-11-23T10:00:00.000Z',
    updatedAt: '2026-11-23T10:00:00.000Z',
})

const replacementBackground: BackgroundAsset = {
    id: 'background-2',
    name: 'new-entrance.mp4',
    type: 'video',
    mimeType: 'video/mp4',
    url: 'blob:new-entrance',
}

describe('Detection class registry', () => {
    it('returns active classes supported by the selected model', () => {
        const classes = getAvailableDetectionClasses('demo-model-v1')

        expect(classes.length).toBeGreaterThan(0)
        expect(classes.every((item) => item.status === 'active')).toBe(true)
        expect(
            classes.every((item) =>
                item.supportedModelVersions.includes('demo-model-v1'),
            ),
        ).toBe(true)
    })

    it('returns no classes for an unsupported model version', () => {
        expect(getAvailableDetectionClasses('unknown-model')).toEqual([])
    })

    it('finds a class by its stable ID', () => {
        expect(getDetectionClassById('demo-person')?.displayName).toBe('Person')
    })

    it('returns undefined for an unknown class ID', () => {
        expect(getDetectionClassById('unknown-class')).toBeUndefined()
    })

    it('creates snapshots for valid classes', () => {
        const snapshots = createClassSnapshots(
            ['demo-person', 'demo-vehicle'],
            'demo-model-v1',
        )

        expect(snapshots).toEqual([
            {
                id: 'demo-person',
                displayName: 'Person',
                description: 'Illustrative person detection class',
            },
            {
                id: 'demo-vehicle',
                displayName: 'Vehicle',
                description: 'Illustrative vehicle detection class',
            },
        ])
    })

    it('rejects classes unavailable for the selected model', () => {
        expect(() =>
            createClassSnapshots(['demo-person'], 'unknown-model'),
        ).toThrow(/unavailable/)
    })
})

describe('Zone configuration working copy', () => {
    it('creates an independent working copy with no unsaved changes', () => {
        const configuration = createConfiguration()
        const state = createWorkingCopy(configuration)

        expect(state.hasUnsavedChanges).toBe(false)
        expect(state.working).toEqual(configuration)
        expect(state.working).not.toBe(state.saved)
        expect(state.saved).not.toBe(configuration)
    })

    it('updates the working copy without changing the saved version', () => {
        const state = createWorkingCopy(createConfiguration())

        const updated = updateWorkingCopy(state, (configuration) => ({
            ...configuration,
            cameraName: 'Updated Camera',
        }))

        expect(updated.working.cameraName).toBe('Updated Camera')
        expect(updated.saved.cameraName).toBe('Entrance Camera')
        expect(updated.hasUnsavedChanges).toBe(true)
    })

    it('does not mark the configuration dirty when nothing changes', () => {
        const state = createWorkingCopy(createConfiguration())

        const updated = updateWorkingCopy(state, (configuration) => ({
            ...configuration,
        }))

        expect(updated.hasUnsavedChanges).toBe(false)
    })

    it('saves the working copy and updates its timestamp', () => {
        const state = createWorkingCopy(createConfiguration())

        const edited = updateWorkingCopy(state, (configuration) => ({
            ...configuration,
            cameraName: 'Updated Camera',
        }))

        const saved = saveWorkingCopy(
            edited,
            '2026-11-23T12:00:00.000Z',
        )

        expect(saved.hasUnsavedChanges).toBe(false)
        expect(saved.saved.cameraName).toBe('Updated Camera')
        expect(saved.working.cameraName).toBe('Updated Camera')
        expect(saved.saved.updatedAt).toBe('2026-11-23T12:00:00.000Z')
    })

    it('discards unsaved changes and restores the last saved version', () => {
        const state = createWorkingCopy(createConfiguration())

        const edited = updateWorkingCopy(state, (configuration) => ({
            ...configuration,
            cameraName: 'Unsaved Camera',
        }))

        const discarded = discardWorkingCopy(edited)

        expect(discarded.hasUnsavedChanges).toBe(false)
        expect(discarded.working.cameraName).toBe('Entrance Camera')
        expect(discarded.saved.cameraName).toBe('Entrance Camera')
    })
})

describe('Background replacement', () => {
    it('leaves the configuration unchanged when replacement is declined', () => {
        const configuration = createConfiguration()

        const result = replaceBackground(
            configuration,
            replacementBackground,
            false,
        )

        expect(result).toEqual(configuration)
        expect(result).not.toBe(configuration)
        expect(result.zones).toHaveLength(1)
        expect(result.countingLines).toHaveLength(1)
    })

    it('replaces the background when confirmed and clears old geometry', () => {
        const configuration = createConfiguration()

        const result = replaceBackground(
            configuration,
            replacementBackground,
            true,
        )

        expect(result.background).toEqual(replacementBackground)
        expect(result.zones).toEqual([])
        expect(result.countingLines).toEqual([])
        expect(result.siteId).toBe(configuration.siteId)
        expect(result.cameraId).toBe(configuration.cameraId)
        expect(configuration.zones).toHaveLength(1)
    })
})
