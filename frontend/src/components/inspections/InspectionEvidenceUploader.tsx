
import { useEffect, useRef, useState } from 'react'
import { Camera, FileUp, Image, Trash2, Upload } from 'lucide-react'
import {
    formatFileSize,
    validateInspectionFiles,
} from '../../inspections/uploadAdapter'

type Props = {
    files: File[]
    onFilesChange: (files: File[]) => void
    disabled?: boolean
}

export default function InspectionEvidenceUploader({
    files,
    onFilesChange,
    disabled = false,
}: Props) {
    const [error, setError] = useState('')
    const [dragging, setDragging] = useState(false)
    const [previews, setPreviews] = useState<Map<File, string>>(
        () => new Map(),
    )
    const previewUrls = useRef(new Map<File, string>())

    // Release previews for files removed externally by the parent.
    useEffect(() => {
        previewUrls.current.forEach((url, file) => {
            if (!files.includes(file)) {
                URL.revokeObjectURL(url)
                previewUrls.current.delete(file)
            }
        })
    }, [files])

    // Release any remaining previews when this component unmounts.
    useEffect(() => {
        const urls = previewUrls.current

        return () => {
            urls.forEach(url => URL.revokeObjectURL(url))
            urls.clear()
        }
    }, [])

    function addFiles(incoming: File[]) {
        if (disabled || incoming.length === 0) return

        const combined = [...files, ...incoming]
        const validationError = validateInspectionFiles(combined)

        if (validationError) {
            setError(validationError)
            return
        }

        const newPreviews = new Map<File, string>()

        incoming.forEach(file => {
            if (
                file.type.startsWith('image/') &&
                !previewUrls.current.has(file)
            ) {
                const url = URL.createObjectURL(file)
                previewUrls.current.set(file, url)
                newPreviews.set(file, url)
            }
        })

        if (newPreviews.size > 0) {
            setPreviews(previous => {
                const next = new Map(previous)
                newPreviews.forEach((url, file) => next.set(file, url))
                return next
            })
        }

        setError('')
        onFilesChange(combined)
    }

    function removeFile(indexToRemove: number) {
        const file = files[indexToRemove]
        const url = file ? previewUrls.current.get(file) : undefined

        if (file && url) {
            URL.revokeObjectURL(url)
            previewUrls.current.delete(file)

            setPreviews(previous => {
                const next = new Map(previous)
                next.delete(file)
                return next
            })
        }

        onFilesChange(files.filter((_, index) => index !== indexToRemove))
        setError('')
    }

    function handleInputChange(
        event: React.ChangeEvent<HTMLInputElement>,
    ) {
        addFiles(Array.from(event.target.files ?? []))
        event.target.value = ''
    }

    function handleDrop(event: React.DragEvent<HTMLDivElement>) {
        event.preventDefault()
        setDragging(false)
        addFiles(Array.from(event.dataTransfer.files))
    }

    return (
        <section className="space-y-4" aria-label="Inspection evidence">
            <div
                onDragOver={event => {
                    event.preventDefault()
                    if (!disabled) setDragging(true)
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                className={`rounded-xl border-2 border-dashed p-6 text-center transition-colors ${dragging
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-300 bg-gray-50'
                    } ${disabled ? 'opacity-50' : ''}`}
            >
                <Upload className="mx-auto mb-3 h-8 w-8 text-gray-500" />

                <p className="font-medium text-gray-800">
                    Drag and drop evidence files here
                </p>
                <p className="mt-1 text-sm text-gray-500">
                    JPEG, PNG, WebP, MP4, WebM, PDF, XLSX and CSV
                </p>

                <div className="mt-4 flex flex-wrap justify-center gap-3">
                    <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border bg-white px-4 py-2 text-sm font-medium hover:bg-gray-100">
                        <FileUp className="h-4 w-4" />
                        Choose files
                        <input
                            type="file"
                            multiple
                            accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,application/pdf,.xlsx,.xls,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,text/csv"
                            disabled={disabled}
                            onChange={handleInputChange}
                            className="sr-only"
                            aria-label="Choose evidence files"
                        />
                    </label>

                    <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border bg-white px-4 py-2 text-sm font-medium hover:bg-gray-100">
                        <Camera className="h-4 w-4" />
                        Take photo
                        <input
                            type="file"
                            accept="image/*"
                            capture="environment"
                            disabled={disabled}
                            onChange={handleInputChange}
                            className="sr-only"
                            aria-label="Take a photo"
                        />
                    </label>
                </div>
            </div>

            <p className="text-xs text-gray-500">
                Maximum 25 MB per file; 100 MB combined.
            </p>

            {error && (
                <p role="alert" className="text-sm text-red-600">
                    {error}
                </p>
            )}

            {files.length > 0 && (
                <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-gray-800">
                        Selected evidence ({files.length})
                    </h3>

                    {files.map((file, index) => {
                        const previewUrl = previews.get(file)

                        return (
                            <div
                                key={`${file.name}-${file.size}-${file.lastModified}-${index}`}
                                className="flex items-center gap-3 rounded-lg border bg-white p-3"
                            >
                                {previewUrl ? (
                                    <img
                                        src={previewUrl}
                                        alt={`Preview of ${file.name}`}
                                        className="h-12 w-12 rounded-md object-cover"
                                    />
                                ) : (
                                    <div className="flex h-12 w-12 items-center justify-center rounded-md bg-gray-100">
                                        <Image className="h-5 w-5 text-gray-500" />
                                    </div>
                                )}

                                <div className="min-w-0 flex-1">
                                    <p className="truncate text-sm font-medium text-gray-800">
                                        {file.name}
                                    </p>
                                    <p className="text-xs text-gray-500">
                                        {formatFileSize(file.size)}
                                    </p>
                                </div>

                                <button
                                    type="button"
                                    disabled={disabled}
                                    onClick={() => removeFile(index)}
                                    aria-label={`Remove ${file.name}`}
                                    className="rounded-md p-2 text-gray-500 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </div>
                        )
                    })}
                </div>
            )}
        </section>
    )
}
