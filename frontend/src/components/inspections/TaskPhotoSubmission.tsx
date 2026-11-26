
import { useEffect, useRef, useState } from 'react'
import { Camera, Image, Loader2, Trash2, Upload } from 'lucide-react'
import {
    formatFileSize,
    validateTaskPhotos,
} from '../../inspections/taskPhotoAdapter'

type Props = {
    onSubmit: (
        files: File[],
        onProgress: (progress: number) => void,
    ) => Promise<boolean>
    disabled?: boolean
}

type SelectedPhoto = {
    file: File
    previewUrl: string
}

export default function TaskPhotoSubmission({
    onSubmit,
    disabled = false,
}: Props) {
    const [photos, setPhotos] = useState<SelectedPhoto[]>([])
    const [error, setError] = useState('')
    const [progress, setProgress] = useState(0)
    const [submitting, setSubmitting] = useState(false)
    const previewUrls = useRef(new Set<string>())

    useEffect(() => {
        const urls = previewUrls.current

        return () => {
            urls.forEach(url => URL.revokeObjectURL(url))
            urls.clear()
        }
    }, [])

    function revokePreview(url: string) {
        URL.revokeObjectURL(url)
        previewUrls.current.delete(url)
    }

    function addFiles(incoming: File[]) {
        if (disabled || submitting || incoming.length === 0) return

        const combined = [...photos.map(photo => photo.file), ...incoming]
        const validationError = validateTaskPhotos(combined)

        if (validationError) {
            setError(validationError)
            return
        }

        const newPhotos = incoming.map(file => {
            const previewUrl = URL.createObjectURL(file)
            previewUrls.current.add(previewUrl)
            return { file, previewUrl }
        })

        setError('')
        setPhotos(previous => [...previous, ...newPhotos])
    }

    function removePhoto(index: number) {
        const photo = photos[index]
        if (photo) revokePreview(photo.previewUrl)

        setPhotos(previous => previous.filter((_, i) => i !== index))
    }

    async function handleSubmit() {
        const files = photos.map(photo => photo.file)
        const validationError = validateTaskPhotos(files)

        if (validationError) {
            setError(validationError)
            return
        }

        setError('')
        setProgress(0)
        setSubmitting(true)

        try {
            const success = await onSubmit(files, setProgress)

            if (success) {
                photos.forEach(photo => revokePreview(photo.previewUrl))
                setPhotos([])
            } else {
                setError(
                    'Photo submission failed. Your photos are still selected. Please retry.',
                )
            }
        } catch {
            setError(
                'Photo submission failed. Your photos are still selected. Please retry.',
            )
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div className="mt-4 space-y-4 rounded-xl border border-blue-100 bg-blue-50/40 p-4">
            <div>
                <h3 className="text-sm font-semibold text-slate-900">
                    Task Photo Evidence
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                    Capture or select photos showing that this task is complete.
                </p>
            </div>

            <div className="flex flex-wrap gap-3">
                <label
                    className={`inline-flex cursor-pointer items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 ${disabled || submitting
                            ? 'pointer-events-none opacity-50'
                            : ''
                        }`}
                >
                    <Camera className="h-4 w-4" />
                    Take Photo
                    <input
                        type="file"
                        accept="image/*"
                        capture="environment"
                        disabled={disabled || submitting}
                        onChange={event => {
                            addFiles(Array.from(event.target.files ?? []))
                            event.target.value = ''
                        }}
                        className="sr-only"
                        aria-label="Capture task photo"
                    />
                </label>

                <label
                    className={`inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 ${disabled || submitting
                            ? 'pointer-events-none opacity-50'
                            : ''
                        }`}
                >
                    <Image className="h-4 w-4" />
                    Choose from Gallery
                    <input
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        multiple
                        disabled={disabled || submitting}
                        onChange={event => {
                            addFiles(Array.from(event.target.files ?? []))
                            event.target.value = ''
                        }}
                        className="sr-only"
                        aria-label="Choose task photos from gallery"
                    />
                </label>
            </div>

            <p className="text-xs text-slate-500">
                JPEG, PNG or WebP · 25 MB per photo · 100 MB total
            </p>

            {photos.length > 0 && (
                <div className="space-y-3">
                    <p className="text-sm font-medium text-slate-800">
                        Selected photos ({photos.length})
                    </p>

                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                        {photos.map((photo, index) => (
                            <div
                                key={`${photo.file.name}-${photo.file.lastModified}-${index}`}
                                className="overflow-hidden rounded-lg border border-slate-200 bg-white"
                            >
                                <img
                                    src={photo.previewUrl}
                                    alt={`Preview of ${photo.file.name}`}
                                    className="h-28 w-full object-cover"
                                />

                                <div className="flex items-center gap-2 p-2">
                                    <div className="min-w-0 flex-1">
                                        <p className="truncate text-xs font-medium text-slate-700">
                                            {photo.file.name}
                                        </p>
                                        <p className="text-xs text-slate-500">
                                            {formatFileSize(photo.file.size)}
                                        </p>
                                    </div>

                                    <button
                                        type="button"
                                        onClick={() => removePhoto(index)}
                                        disabled={submitting}
                                        aria-label={`Remove ${photo.file.name}`}
                                        className="rounded-md p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>

                    <button
                        type="button"
                        onClick={handleSubmit}
                        disabled={disabled || submitting}
                        className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
                    >
                        {submitting ? (
                            <>
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Submitting...
                            </>
                        ) : (
                            <>
                                <Upload className="h-4 w-4" />
                                Submit {photos.length}{' '}
                                {photos.length === 1 ? 'Photo' : 'Photos'}
                            </>
                        )}
                    </button>

                    {submitting && (
                        <div
                            className="h-2 overflow-hidden rounded-full bg-slate-200"
                            role="progressbar"
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-valuenow={progress}
                            aria-label="Photo upload progress"
                        >
                            <div
                                className="h-full rounded-full bg-blue-600 transition-all"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                    )}
                </div>
            )}

            {error && (
                <p role="alert" className="text-sm text-red-600">
                    {error}
                </p>
            )}
        </div>
    )
}
