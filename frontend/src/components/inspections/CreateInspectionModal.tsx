
import { useMemo, useState } from 'react'
import { X, ArrowLeft, ArrowRight, ClipboardCheck } from 'lucide-react'

import { DEMO_SITES, type DemoUser } from '../../data/users'
import { INSPECTION_TEMPLATES } from '../../data/inspectionData'
import type { InspectionRecord, InspectionType } from '../../inspections/types'
import InspectionEvidenceUploader from './InspectionEvidenceUploader'
import {
    createInspectionFormData,
    mockUploadAdapter,
    validateInspectionFiles,
    type UploadAdapter,
} from '../../inspections/uploadAdapter'

type Props = {
    currentUser: DemoUser
    users: DemoUser[]
    onClose: () => void
    onCreate: (inspection: InspectionRecord, files: File[]) => void
    uploadAdapter?: UploadAdapter
}

type FormData = {
    templateId: string
    title: string
    description: string
    type: InspectionType
    siteId: string
    zone: string
    assignedToUserId: string
    dueDate: string
}

const today = () => {
    const date = new Date()
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
}

function CreateInspectionModal({
    currentUser,
    users,
    onClose,
    onCreate,
    uploadAdapter = mockUploadAdapter,
}: Props) {
    const [step, setStep] = useState(1)
    const [error, setError] = useState('')
    const [selectedFiles, setSelectedFiles] = useState<File[]>([])
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [uploadProgress, setUploadProgress] = useState(0)

    const [form, setForm] = useState<FormData>({
        templateId: '',
        title: '',
        description: '',
        type: 'Custom',
        siteId: currentUser.siteId ?? '',
        zone: '',
        assignedToUserId: '',
        dueDate: '',
    })

    const isAdmin = currentUser.role === 'admin'
    const isSupervisor = currentUser.role === 'supervisor'
    const isManager = currentUser.role === 'manager'

    const availableSites = useMemo(() => {
        if (isAdmin) return DEMO_SITES

        return DEMO_SITES.filter(
            site => site.id === currentUser.siteId
        )
    }, [isAdmin, currentUser.siteId])

    const availableAssignees = useMemo(() => {
        return users.filter(user => {
            if (!user.isActive || user.role === 'admin') return false
            if (user.siteId !== form.siteId) return false

            if (isAdmin || isSupervisor) {
                return user.role === 'manager' || user.role === 'employee'
            }

            if (isManager) {
                return (
                    user.role === 'employee' &&
                    user.managerId === currentUser.id
                )
            }

            return false
        })
    }, [
        users,
        form.siteId,
        currentUser.id,
        isAdmin,
        isSupervisor,
        isManager,
    ])

    const selectedTemplate = INSPECTION_TEMPLATES.find(
        template => template.id === form.templateId
    )

    const updateForm = (updates: Partial<FormData>) => {
        setForm(previous => ({ ...previous, ...updates }))
        setError('')
    }

    const selectTemplate = (templateId: string) => {
        if (templateId === 'custom') {
            updateForm({
                templateId: '',
                title: '',
                description: '',
                type: 'Custom',
            })
            return
        }

        const template = INSPECTION_TEMPLATES.find(
            item => item.id === templateId
        )

        if (!template) return

        updateForm({
            templateId: template.id,
            title: template.name,
            description: template.description,
            type: template.category,
        })
    }

    const goToStepTwo = () => {
        if (!form.templateId && !form.title.trim()) {
            setError('Enter a title for your custom inspection.')
            return
        }

        if (!form.title.trim()) {
            setError('Inspection title is required.')
            return
        }

        setStep(2)
        setError('')
    }

    const handleCreate = async () => {
        if (isSubmitting) return

        if (!form.siteId || !form.zone.trim()) {
            setError('Select a site and enter a zone.')
            return
        }

        if (!form.assignedToUserId) {
            setError('Please select an assignee.')
            return
        }

        if (!form.dueDate || form.dueDate < today()) {
            setError('Choose a valid due date.')
            return
        }

        const fileValidationError = validateInspectionFiles(selectedFiles)

        if (fileValidationError) {
            setError(fileValidationError)
            return
        }

        setError('')
        setIsSubmitting(true)
        setUploadProgress(0)

        try {
            if (selectedFiles.length > 0) {
                const formData = createInspectionFormData(
                    form.siteId,
                    selectedFiles,
                )

                await uploadAdapter(formData, progress => {
                    setUploadProgress(
                        Math.min(100, Math.max(0, progress)),
                    )
                })
            }
        } catch (uploadError) {
            setError(
                uploadError instanceof Error
                    ? uploadError.message
                    : 'Evidence upload failed. Please try again.',
            )
            setIsSubmitting(false)
            return
        }

        const now = new Date().toISOString()
        const dueDate = new Date(`${form.dueDate}T17:00:00`).toISOString()

        const inspection: InspectionRecord = {
            id: `INS-${Date.now()}`,
            title: form.title.trim(),
            description: form.description.trim(),
            type: form.type,
            ...(selectedTemplate ? { templateId: selectedTemplate.id } : {}),
            siteId: form.siteId,
            zone: form.zone.trim(),
            status: 'Scheduled',
            assignedToUserId: form.assignedToUserId,
            assignedByUserId: currentUser.id,
            createdAt: now,
            scheduledAt: now,
            dueDate,
            answers: [],
            observations: [],
            findingIds: [],
            evidenceIds: [],
        }

        onCreate(inspection, selectedFiles)
        onClose()
    }

    const inputClass =
        'w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100'

    const labelClass =
        'mb-1.5 block text-sm font-medium text-slate-700'

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4"
            onMouseDown={event => {
                if (
                    event.target === event.currentTarget &&
                    !isSubmitting
                ) {
                    onClose()
                }
            }}
        >
            <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="create-inspection-title"
                className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl"
            >
                <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
                    <div>
                        <h2
                            id="create-inspection-title"
                            className="text-xl font-bold text-slate-900"
                        >
                            Create Inspection
                        </h2>
                        <p className="mt-1 text-sm text-slate-500">
                            Step {step} of 2 · {step === 1 ? 'Inspection details' : 'Assignment and schedule'}
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={onClose}
                        disabled={isSubmitting}
                        aria-label="Close modal"
                        className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50"
                    >
                        <X size={20} />
                    </button>
                </div>

                <div className="flex gap-2 px-6 pt-5">
                    <div className={`h-1.5 flex-1 rounded-full ${step >= 1 ? 'bg-blue-600' : 'bg-slate-200'}`} />
                    <div className={`h-1.5 flex-1 rounded-full ${step >= 2 ? 'bg-blue-600' : 'bg-slate-200'}`} />
                </div>

                <div className="space-y-5 p-6">
                    {step === 1 && (
                        <>
                            <div>
                                <h3 className="font-semibold text-slate-900">
                                    Choose an inspection type
                                </h3>
                                <p className="mt-1 text-sm text-slate-500">
                                    Start with a ready-made checklist or create your own.
                                </p>
                            </div>

                            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                                {INSPECTION_TEMPLATES.filter(
                                    template => template.isActive
                                ).map(template => (
                                    <button
                                        key={template.id}
                                        type="button"
                                        onClick={() => selectTemplate(template.id)}
                                        className={`rounded-xl border p-4 text-left transition ${form.templateId === template.id
                                                ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-100'
                                                : 'border-slate-200 hover:border-blue-300'
                                            }`}
                                    >
                                        <ClipboardCheck className="mb-3 text-blue-600" size={21} />
                                        <p className="font-semibold text-slate-900">
                                            {template.name}
                                        </p>
                                        <p className="mt-1 text-xs text-slate-500">
                                            {template.checklist.length} questions · {template.estimatedMinutes} min
                                        </p>
                                    </button>
                                ))}

                                <button
                                    type="button"
                                    onClick={() => selectTemplate('custom')}
                                    className={`rounded-xl border border-dashed p-4 text-left transition ${form.type === 'Custom'
                                            ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-100'
                                            : 'border-slate-300 hover:border-blue-300'
                                        }`}
                                >
                                    <span className="mb-3 block text-xl text-blue-600">＋</span>
                                    <p className="font-semibold text-slate-900">
                                        Custom Inspection
                                    </p>
                                    <p className="mt-1 text-xs text-slate-500">
                                        Start with your own inspection details.
                                    </p>
                                </button>
                            </div>

                            <div>
                                <label className={labelClass}>Inspection title *</label>
                                <input
                                    className={inputClass}
                                    value={form.title}
                                    onChange={event => updateForm({ title: event.target.value })}
                                    placeholder="Enter inspection title"
                                />
                            </div>

                            <div>
                                <label className={labelClass}>Description</label>
                                <textarea
                                    className={inputClass}
                                    rows={3}
                                    value={form.description}
                                    onChange={event => updateForm({ description: event.target.value })}
                                    placeholder="Describe the purpose of this inspection"
                                />
                            </div>
                        </>
                    )}

                    {step === 2 && (
                        <>
                            <div>
                                <h3 className="font-semibold text-slate-900">
                                    Assignment and schedule
                                </h3>
                                <p className="mt-1 text-sm text-slate-500">
                                    Choose where the inspection takes place and who will conduct it.
                                </p>
                            </div>

                            <div>
                                <label className={labelClass}>Site *</label>
                                <select
                                    className={inputClass}
                                    value={form.siteId}
                                    onChange={event => updateForm({
                                        siteId: event.target.value,
                                        assignedToUserId: '',
                                    })}
                                >
                                    <option value="">Select a site</option>
                                    {availableSites.map(site => (
                                        <option key={site.id} value={site.id}>
                                            {site.name}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className={labelClass}>Zone / Area *</label>
                                <input
                                    className={inputClass}
                                    value={form.zone}
                                    onChange={event => updateForm({ zone: event.target.value })}
                                    placeholder="e.g. Loading Bay, Storage Area"
                                />
                            </div>

                            <div>
                                <label className={labelClass}>Assign to *</label>
                                <select
                                    className={inputClass}
                                    value={form.assignedToUserId}
                                    onChange={event => updateForm({
                                        assignedToUserId: event.target.value,
                                    })}
                                >
                                    <option value="">Select an assignee</option>
                                    {availableAssignees.map(user => (
                                        <option key={user.id} value={user.id}>
                                            {user.name} · {user.role}
                                        </option>
                                    ))}
                                </select>
                                {form.siteId && availableAssignees.length === 0 && (
                                    <p className="mt-1 text-xs text-amber-600">
                                        No eligible active assignees are available for this site.
                                    </p>
                                )}
                            </div>

                            <div>
                                <label className={labelClass}>Due date *</label>
                                <input
                                    type="date"
                                    min={today()}
                                    className={inputClass}
                                    value={form.dueDate}
                                    onChange={event => updateForm({ dueDate: event.target.value })}
                                />
                            </div>

                            <div className="space-y-3 border-t border-slate-200 pt-5">
                                <div>
                                    <h3 className="font-semibold text-slate-900">
                                        Inspection evidence
                                    </h3>
                                    <p className="mt-1 text-sm text-slate-500">
                                        Capture a photo or attach existing evidence.
                                    </p>
                                </div>

                                <InspectionEvidenceUploader
                                    files={selectedFiles}
                                    onFilesChange={files => {
                                        setSelectedFiles(files)
                                        setError('')
                                    }}
                                    disabled={isSubmitting}
                                />

                                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                                    Demo mode: uploads are simulated. Files are not sent to a server.
                                </div>

                                {isSubmitting && selectedFiles.length > 0 && (
                                    <div aria-live="polite" className="space-y-2">
                                        <div className="flex justify-between text-sm">
                                            <span className="font-medium text-slate-700">
                                                Simulated upload progress
                                            </span>
                                            <span className="text-slate-600">
                                                {uploadProgress}%
                                            </span>
                                        </div>
                                        <div
                                            className="h-2 overflow-hidden rounded-full bg-slate-200"
                                            role="progressbar"
                                            aria-valuenow={uploadProgress}
                                            aria-valuemin={0}
                                            aria-valuemax={100}
                                        >
                                            <div
                                                className="h-full rounded-full bg-blue-600 transition-all"
                                                style={{ width: `${uploadProgress}%` }}
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="rounded-xl bg-slate-50 p-4">
                                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                    Review
                                </p>
                                <p className="mt-2 font-semibold text-slate-900">
                                    {form.title || 'Untitled inspection'}
                                </p>
                                <p className="mt-1 text-sm text-slate-500">
                                    {selectedTemplate?.name ?? 'Custom inspection'}
                                </p>
                            </div>
                        </>
                    )}

                    {error && (
                        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                            {error}
                        </p>
                    )}
                </div>

                <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4">
                    <button
                        type="button"
                        disabled={isSubmitting}
                        onClick={step === 1 ? onClose : () => {
                            setStep(1)
                            setError('')
                        }}
                        className="inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100 disabled:opacity-50"
                    >
                        {step === 1 ? 'Cancel' : <><ArrowLeft size={16} /> Back</>}
                    </button>

                    {step === 1 ? (
                        <button
                            type="button"
                            onClick={goToStepTwo}
                            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
                        >
                            Next <ArrowRight size={16} />
                        </button>
                    ) : (
                        <button
                            type="button"
                            onClick={handleCreate}
                            disabled={isSubmitting}
                            className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {isSubmitting ? 'Creating...' : 'Create Inspection'}
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}

export default CreateInspectionModal
