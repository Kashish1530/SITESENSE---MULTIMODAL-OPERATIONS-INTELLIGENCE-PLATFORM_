
/**
 * SiteSense M6.9 — Zone Configuration domain model
 *
 * Frontend demo implementation.
 * Detection classes and model compatibility below are illustrative mock data,
 * not confirmed production detector outputs.
 */

export type RegistryStatus = 'active' | 'deprecated' | 'inactive'

export interface ModelCompatibility {
    version: string
    label: string
    isDemo: boolean
}

export interface DetectionClassDefinition {
    id: string
    displayName: string
    description: string
    status: RegistryStatus
    supportedModelVersions: string[]
    illustrative: boolean
}

export interface Point2D {
    x: number
    y: number
}

export interface ZoneDefinition {
    id: string
    name: string
    description?: string
    points: Point2D[]
    detectionClassIds: string[]
    enabled: boolean
}

export interface CountingLineDefinition {
    id: string
    name: string
    start: Point2D
    end: Point2D
    direction: 'both' | 'forward' | 'backward'
    enabled: boolean
}

export interface BackgroundAsset {
    id: string
    name: string
    type: 'image' | 'video'
    mimeType: string
    url: string
    capturedAt?: string
    durationSeconds?: number
}

export interface DetectionClassSnapshot {
    id: string
    displayName: string
    description: string
}

export interface ZoneConfiguration {
    id: string
    siteId: string
    siteName: string
    cameraId: string
    cameraName: string
    modelVersion: string
    background: BackgroundAsset | null
    zones: ZoneDefinition[]
    countingLines: CountingLineDefinition[]
    detectionClasses: DetectionClassSnapshot[]
    createdAt: string
    updatedAt: string
}

export interface ZoneConfigurationWorkingCopy {
    saved: ZoneConfiguration
    working: ZoneConfiguration
    hasUnsavedChanges: boolean
}

/**
 * Demo model compatibility.
 * Replace with API-provided model metadata when backend integration exists.
 */
export const DEMO_MODEL_COMPATIBILITY: ModelCompatibility[] = [
    {
        version: 'demo-model-v1',
        label: 'Demo Detection Model v1',
        isDemo: true,
    },
]

/**
 * Illustrative registry entries.
 * These IDs are frontend demo IDs, not production detector class IDs.
 */
export const DETECTION_CLASS_REGISTRY: DetectionClassDefinition[] = [
    {
        id: 'demo-person',
        displayName: 'Person',
        description: 'Illustrative person detection class',
        status: 'active',
        supportedModelVersions: ['demo-model-v1'],
        illustrative: true,
    },
    {
        id: 'demo-vehicle',
        displayName: 'Vehicle',
        description: 'Illustrative vehicle detection class',
        status: 'active',
        supportedModelVersions: ['demo-model-v1'],
        illustrative: true,
    },
    {
        id: 'demo-forklift',
        displayName: 'Forklift',
        description: 'Illustrative forklift detection class',
        status: 'active',
        supportedModelVersions: ['demo-model-v1'],
        illustrative: true,
    },
    {
        id: 'demo-safety-helmet',
        displayName: 'Safety Helmet',
        description: 'Illustrative safety helmet detection class',
        status: 'active',
        supportedModelVersions: ['demo-model-v1'],
        illustrative: true,
    },
    {
        id: 'demo-safety-vest',
        displayName: 'Safety Vest',
        description: 'Illustrative safety vest detection class',
        status: 'active',
        supportedModelVersions: ['demo-model-v1'],
        illustrative: true,
    },
    {
        id: 'demo-fire',
        displayName: 'Fire',
        description: 'Illustrative fire detection class',
        status: 'active',
        supportedModelVersions: ['demo-model-v1'],
        illustrative: true,
    },
    {
        id: 'demo-spill',
        displayName: 'Spill',
        description: 'Illustrative spill detection class',
        status: 'active',
        supportedModelVersions: ['demo-model-v1'],
        illustrative: true,
    },
    {
        id: 'demo-fire-hose',
        displayName: 'Fire Hose',
        description: 'Illustrative fire hose detection class',
        status: 'active',
        supportedModelVersions: ['demo-model-v1'],
        illustrative: true,
    },
    {
        id: 'demo-safety-cone',
        displayName: 'Safety Cone',
        description: 'Illustrative safety cone detection class',
        status: 'active',
        supportedModelVersions: ['demo-model-v1'],
        illustrative: true,
    },
    {
        id: 'demo-obstacle',
        displayName: 'Obstacle',
        description: 'Illustrative obstacle detection class',
        status: 'active',
        supportedModelVersions: ['demo-model-v1'],
        illustrative: true,
    },
]

/**
 * Returns active classes supported by the selected model.
 * Deprecated and inactive classes are not offered for new configurations.
 */
export function getAvailableDetectionClasses(
    modelVersion: string,
): DetectionClassDefinition[] {
    return DETECTION_CLASS_REGISTRY.filter(
        (definition) =>
            definition.status === 'active' &&
            definition.supportedModelVersions.includes(modelVersion),
    ).map((definition) => structuredClone(definition))
}

/**
 * Finds a registry definition by its stable ID.
 */
export function getDetectionClassById(
    classId: string,
): DetectionClassDefinition | undefined {
    const definition = DETECTION_CLASS_REGISTRY.find(
        (item) => item.id === classId,
    )

    return definition ? structuredClone(definition) : undefined
}

/**
 * Creates immutable class snapshots for a configuration.
 * Only active classes supported by the selected model may be newly selected.
 */
export function createClassSnapshots(
    classIds: string[],
    modelVersion: string,
): DetectionClassSnapshot[] {
    const availableClasses = getAvailableDetectionClasses(modelVersion)

    return classIds.map((classId) => {
        const definition = availableClasses.find(
            (item) => item.id === classId,
        )

        if (!definition) {
            throw new Error(
                `Detection class "${classId}" is unavailable for model "${modelVersion}".`,
            )
        }

        return {
            id: definition.id,
            displayName: definition.displayName,
            description: definition.description,
        }
    })
}

/**
 * Creates an editable working copy without changing the saved configuration.
 */
export function createWorkingCopy(
    configuration: ZoneConfiguration,
): ZoneConfigurationWorkingCopy {
    const saved = structuredClone(configuration)

    return {
        saved,
        working: structuredClone(saved),
        hasUnsavedChanges: false,
    }
}

/**
 * Updates only the working copy.
 */
export function updateWorkingCopy(
    state: ZoneConfigurationWorkingCopy,
    update: (configuration: ZoneConfiguration) => ZoneConfiguration,
): ZoneConfigurationWorkingCopy {
    const nextWorking = update(structuredClone(state.working))

    return {
        ...state,
        working: structuredClone(nextWorking),
        hasUnsavedChanges:
            JSON.stringify(nextWorking) !== JSON.stringify(state.saved),
    }
}

/**
 * Explicitly saves the working copy.
 * The previous saved version remains untouched until this function is called.
 */
export function saveWorkingCopy(
    state: ZoneConfigurationWorkingCopy,
    updatedAt: string,
): ZoneConfigurationWorkingCopy {
    const saved = structuredClone({
        ...state.working,
        updatedAt,
    })

    return {
        saved,
        working: structuredClone(saved),
        hasUnsavedChanges: false,
    }
}

/**
 * Discards unsaved changes and restores the last saved configuration.
 */
export function discardWorkingCopy(
    state: ZoneConfigurationWorkingCopy,
): ZoneConfigurationWorkingCopy {
    return {
        saved: structuredClone(state.saved),
        working: structuredClone(state.saved),
        hasUnsavedChanges: false,
    }
}

/**
 * Replacing a background requires explicit confirmation.
 * On confirmation, old zone geometry and counting lines are cleared:
 * their coordinates must not silently carry over to a different background.
 */
export function replaceBackground(
    configuration: ZoneConfiguration,
    background: BackgroundAsset,
    confirmed: boolean,
): ZoneConfiguration {
    if (!confirmed) {
        return structuredClone(configuration)
    }

    return {
        ...structuredClone(configuration),
        background: structuredClone(background),
        zones: [],
        countingLines: [],
    }
}
