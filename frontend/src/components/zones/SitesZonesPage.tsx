
import { useMemo, useState } from 'react'
import {
    Building2,
    Camera,
    Check,
    ChevronDown,
    Clock3,
    RotateCcw,
    Save,
    ShieldCheck,
} from 'lucide-react'

import { DEMO_SITES, type DemoUser } from '../../data/users'
import BackgroundAssetEditor from './BackgroundAssetEditor'
import ZoneDrawingEditor from './ZoneDrawingEditor'
import {
    DEMO_MODEL_COMPATIBILITY,
    createWorkingCopy,
    createClassSnapshots,
    discardWorkingCopy,
    getAvailableDetectionClasses,
    replaceBackground,
    saveWorkingCopy,
    updateWorkingCopy,
    type BackgroundAsset,
    type CountingLineDefinition,
    type ZoneConfiguration,
    type ZoneConfigurationWorkingCopy,
    type ZoneDefinition,
} from '../../zones/zoneConfiguration'

type Props = {
    currentUser: DemoUser
}

type DemoCamera = {
    id: string
    siteId: string
    name: string
    location: string
    status: 'online' | 'offline'
}

const DEMO_CAMERAS: DemoCamera[] = DEMO_SITES.flatMap((site, index) => [
    {
        id: `${site.id}-CAM-01`,
        siteId: site.id,
        name: `${site.name} — Camera 01`,
        location: 'Main entrance',
        status: 'online' as const,
    },
    {
        id: `${site.id}-CAM-02`,
        siteId: site.id,
        name: `${site.name} — Camera 02`,
        location: 'Storage area',
        status: index === 1 ? 'offline' as const : 'online' as const,
    },
])

function createDemoConfigurations(): ZoneConfiguration[] {
    return DEMO_CAMERAS.map(camera => {
        const site = DEMO_SITES.find(item => item.id === camera.siteId)!

        return {
            id: `CONFIG-${camera.id}`,
            siteId: site.id,
            siteName: site.name,
            cameraId: camera.id,
            cameraName: camera.name,
            modelVersion: 'demo-model-v1',
            background: null,
            zones: [],
            countingLines: [],
            detectionClasses: [],
            createdAt: '2026-11-23T09:00:00.000Z',
            updatedAt: '2026-11-23T09:00:00.000Z',
        }
    })
}

function formatDate(value: string): string {
    const date = new Date(value)

    if (Number.isNaN(date.getTime())) return 'Not available'

    return date.toLocaleString()
}

export default function SitesZonesPage({ currentUser }: Props) {
    const isAdmin = currentUser.role === 'admin'
    const canEdit = isAdmin

    const availableSites = useMemo(() => {
        if (isAdmin) return DEMO_SITES

        return DEMO_SITES.filter(
            site => site.id === currentUser.siteId,
        )
    }, [isAdmin, currentUser.siteId])

    const [configurations, setConfigurations] = useState(
        createDemoConfigurations,
    )

    const [selectedSiteId, setSelectedSiteId] = useState(
        availableSites[0]?.id ?? '',
    )

    const cameras = useMemo(
        () => DEMO_CAMERAS.filter(
            camera => camera.siteId === selectedSiteId,
        ),
        [selectedSiteId],
    )

    const [selectedCameraId, setSelectedCameraId] = useState(
        () => DEMO_CAMERAS.find(
            camera => camera.siteId === availableSites[0]?.id,
        )?.id ?? '',
    )

    const selectedConfiguration = configurations.find(
        item => item.cameraId === selectedCameraId,
    )

    // A working copy exists only during an explicit editing session.
    const [workingCopy, setWorkingCopy] =
        useState<ZoneConfigurationWorkingCopy | null>(null)

    const activeConfiguration = workingCopy?.working ??
        selectedConfiguration ?? null

    const availableClasses = useMemo(
        () => activeConfiguration
            ? getAvailableDetectionClasses(activeConfiguration.modelVersion)
            : [],
        [activeConfiguration],
    )

    const confirmLeavingEditor = (): boolean => {
        if (!workingCopy?.hasUnsavedChanges) return true

        return window.confirm(
            'You have unsaved changes. Leave this configuration and discard those changes?',
        )
    }

    const selectCamera = (cameraId: string) => {
        if (cameraId === selectedCameraId) return
        if (!confirmLeavingEditor()) return

        setSelectedCameraId(cameraId)
        setWorkingCopy(null)
    }

    const selectSite = (siteId: string) => {
        if (siteId === selectedSiteId) return
        if (!confirmLeavingEditor()) return

        const firstCamera = DEMO_CAMERAS.find(
            camera => camera.siteId === siteId,
        )

        setSelectedSiteId(siteId)
        setSelectedCameraId(firstCamera?.id ?? '')
        setWorkingCopy(null)
    }

    const beginEditing = () => {
        if (!selectedConfiguration || !canEdit) return

        setWorkingCopy(createWorkingCopy(selectedConfiguration))
    }

    const toggleClass = (classId: string, checked: boolean) => {
        if (!workingCopy || !canEdit) return

        setWorkingCopy(previous => {
            if (!previous) return previous

            const currentIds = previous.working.detectionClasses.map(
                item => item.id,
            )

            const nextIds = checked
                ? [...currentIds, classId]
                : currentIds.filter(id => id !== classId)

            return updateWorkingCopy(previous, configuration => ({
                ...configuration,
                detectionClasses: createClassSnapshots(
                    nextIds,
                    configuration.modelVersion,
                ),
            }))
        })
    }

    const applyBackground = (background: BackgroundAsset): boolean => {
        if (!workingCopy || !canEdit) return false

        const configuration = workingCopy.working

        const needsConfirmation =
            Boolean(configuration.background) ||
            configuration.zones.length > 0 ||
            configuration.countingLines.length > 0

        if (needsConfirmation) {
            const confirmed = window.confirm(
                'Replacing the background will clear all existing zones and counting lines because their coordinates may no longer match. Continue?',
            )

            if (!confirmed) return false
        }

        setWorkingCopy(previous => {
            if (!previous) return previous

            return updateWorkingCopy(previous, current =>
                replaceBackground(current, background, true),
            )
        })

        return true
    }

    const updateZones = (zones: ZoneDefinition[]) => {
        if (!workingCopy || !canEdit) return

        setWorkingCopy(previous => {
            if (!previous) return previous

            return updateWorkingCopy(previous, configuration => ({
                ...configuration,
                zones,
            }))
        })
    }

    const updateCountingLines = (
        countingLines: CountingLineDefinition[],
    ) => {
        if (!workingCopy || !canEdit) return

        setWorkingCopy(previous => {
            if (!previous) return previous

            return updateWorkingCopy(previous, configuration => ({
                ...configuration,
                countingLines,
            }))
        })
    }

    const handleSave = () => {
        if (!workingCopy || !canEdit) return

        const savedState = saveWorkingCopy(
            workingCopy,
            new Date().toISOString(),
        )

        setConfigurations(previous => previous.map(configuration =>
            configuration.id === savedState.saved.id
                ? savedState.saved
                : configuration,
        ))

        // The saved configuration is now the source of truth.
        setWorkingCopy(null)
    }

    const handleDiscard = () => {
        if (!workingCopy || !canEdit) return

        discardWorkingCopy(workingCopy)
        setWorkingCopy(null)
    }

    if (!availableSites.length) {
        return (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-6">
                <h2 className="font-semibold text-amber-900">
                    No assigned site
                </h2>
                <p className="mt-1 text-sm text-amber-800">
                    Your account does not currently have an assigned site.
                </p>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2">
                        <Building2 className="h-6 w-6 text-indigo-600" />
                        <h1 className="text-2xl font-bold text-slate-900">
                            Sites &amp; Zones
                        </h1>
                    </div>
                    <p className="mt-1 text-sm text-slate-500">
                        Configure camera detection areas and counting rules.
                    </p>
                </div>

                <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600">
                    <ShieldCheck className="h-4 w-4" />
                    {canEdit ? 'Admin · Edit access' : 'Supervisor · View only'}
                </span>
            </div>

            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                Demo configuration: camera records, model compatibility and
                saved changes are held in frontend memory only. No camera
                connection or backend persistence is active.
            </div>

            <section className="grid gap-4 rounded-xl border border-slate-200 bg-white p-5 md:grid-cols-2">
                <label className="block">
                    <span className="mb-2 block text-sm font-medium text-slate-700">
                        Site
                    </span>
                    <span className="relative block">
                        <select
                            value={selectedSiteId}
                            onChange={event => selectSite(event.target.value)}
                            className="w-full appearance-none rounded-lg border border-slate-300 bg-white px-3 py-2.5 pr-9 text-sm text-slate-800 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                        >
                            {availableSites.map(site => (
                                <option key={site.id} value={site.id}>
                                    {site.name}
                                </option>
                            ))}
                        </select>
                        <ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-400" />
                    </span>
                </label>

                <label className="block">
                    <span className="mb-2 block text-sm font-medium text-slate-700">
                        Camera
                    </span>
                    <span className="relative block">
                        <select
                            value={selectedCameraId}
                            onChange={event => selectCamera(event.target.value)}
                            className="w-full appearance-none rounded-lg border border-slate-300 bg-white px-3 py-2.5 pr-9 text-sm text-slate-800 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                        >
                            {cameras.map(camera => (
                                <option key={camera.id} value={camera.id}>
                                    {camera.name}
                                </option>
                            ))}
                        </select>
                        <ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-400" />
                    </span>
                </label>
            </section>

            {activeConfiguration && (
                <section className="space-y-5 rounded-xl border border-slate-200 bg-white p-5">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h2 className="text-lg font-semibold text-slate-900">
                                Configuration
                            </h2>
                            <p className="mt-1 text-sm text-slate-500">
                                {activeConfiguration.cameraName}
                            </p>
                        </div>

                        {canEdit && !workingCopy && (
                            <button
                                onClick={beginEditing}
                                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                            >
                                Edit configuration
                            </button>
                        )}
                    </div>

                    <div className="grid gap-3 sm:grid-cols-3">
                        <div className="rounded-lg bg-slate-50 p-3">
                            <p className="text-xs text-slate-500">Model</p>
                            <p className="mt-1 text-sm font-semibold text-slate-800">
                                {DEMO_MODEL_COMPATIBILITY.find(
                                    model => model.version === activeConfiguration.modelVersion,
                                )?.label ?? activeConfiguration.modelVersion}
                            </p>
                        </div>

                        <div className="rounded-lg bg-slate-50 p-3">
                            <p className="text-xs text-slate-500">Zones</p>
                            <p className="mt-1 text-sm font-semibold text-slate-800">
                                {activeConfiguration.zones.length}
                            </p>
                        </div>

                        <div className="rounded-lg bg-slate-50 p-3">
                            <p className="text-xs text-slate-500">Counting lines</p>
                            <p className="mt-1 text-sm font-semibold text-slate-800">
                                {activeConfiguration.countingLines.length}
                            </p>
                        </div>
                    </div>

                    <div>
                        <h3 className="text-sm font-semibold text-slate-800">
                            Detection classes
                        </h3>
                        <p className="mt-1 text-xs text-slate-500">
                            Only classes supported by the selected model are listed.
                        </p>

                        <div className="mt-3 grid gap-2 sm:grid-cols-2">
                            {availableClasses.map(item => {
                                const checked = activeConfiguration.detectionClasses.some(
                                    selected => selected.id === item.id,
                                )

                                return (
                                    <label
                                        key={item.id}
                                        className={`flex items-start gap-3 rounded-lg border p-3 ${canEdit && workingCopy
                                            ? 'cursor-pointer hover:border-indigo-300'
                                            : ''
                                            }`}
                                    >
                                        <input
                                            type="checkbox"
                                            checked={checked}
                                            disabled={!canEdit || !workingCopy}
                                            onChange={event => toggleClass(
                                                item.id,
                                                event.target.checked,
                                            )}
                                            className="mt-0.5 h-4 w-4 accent-indigo-600"
                                        />
                                        <span>
                                            <span className="block text-sm font-medium text-slate-800">
                                                {item.displayName}
                                            </span>
                                            <span className="mt-0.5 block text-xs text-slate-500">
                                                {item.description}
                                            </span>
                                        </span>
                                    </label>
                                )
                            })}
                        </div>
                    </div>

                    <div className="space-y-4 rounded-lg border border-slate-200 p-4">
                        <div className="flex items-center gap-2">
                            <Camera className="h-4 w-4 text-slate-500" />
                            <h3 className="text-sm font-semibold text-slate-800">
                                Background &amp; Zone Drawing
                            </h3>
                        </div>

                        <BackgroundAssetEditor
                            currentBackground={activeConfiguration.background}
                            disabled={!canEdit || !workingCopy}
                            onApply={applyBackground}
                            showPreview={false}
                        />

                        {activeConfiguration.background && (
                            <ZoneDrawingEditor
                                background={activeConfiguration.background}
                                zones={activeConfiguration.zones}
                                countingLines={activeConfiguration.countingLines}
                                availableClasses={availableClasses}
                                disabled={!canEdit || !workingCopy}
                                onZonesChange={updateZones}
                                onCountingLinesChange={updateCountingLines}
                            />
                        )}
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
                        <div className="text-xs text-slate-500">
                            <Clock3 className="mr-1 inline h-3.5 w-3.5" />
                            Last saved: {formatDate(activeConfiguration.updatedAt)}
                        </div>

                        {canEdit && workingCopy && (
                            <div className="flex flex-wrap gap-2">
                                <button
                                    onClick={handleDiscard}
                                    className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                                >
                                    <RotateCcw className="h-4 w-4" />
                                    Discard
                                </button>
                                <button
                                    onClick={handleSave}
                                    disabled={!workingCopy.hasUnsavedChanges}
                                    className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    <Save className="h-4 w-4" />
                                    Save changes
                                </button>
                            </div>
                        )}
                    </div>

                    {workingCopy?.hasUnsavedChanges && (
                        <p className="flex items-center gap-2 text-xs font-medium text-amber-700">
                            <Clock3 className="h-4 w-4" />
                            Unsaved changes — the saved configuration is unchanged.
                        </p>
                    )}

                    {workingCopy && !workingCopy.hasUnsavedChanges && (
                        <p className="flex items-center gap-2 text-xs text-emerald-700">
                            <Check className="h-4 w-4" />
                            Working copy matches the saved configuration.
                        </p>
                    )}
                </section>
            )}

            {!activeConfiguration && (
                <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
                    No camera configuration is available for this site.
                </div>
            )}
        </div>
    )
}
