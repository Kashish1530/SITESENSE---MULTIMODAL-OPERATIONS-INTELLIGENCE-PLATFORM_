
import { formatFileSize } from './uploadAdapter'

export const MAX_TASK_PHOTO_SIZE = 25 * 1024 * 1024
export const MAX_TASK_PHOTO_TOTAL_SIZE = 100 * 1024 * 1024

export const TASK_PHOTO_TYPES = [
    'image/jpeg',
    'image/png',
    'image/webp',
] as const

export type TaskPhotoUploadResult = {
    mode: 'mock'
    uploadedCount: number
}

export function validateTaskPhotos(files: File[]): string | null {
    if (files.length === 0) {
        return 'Add at least one photo before submitting.'
    }

    let totalSize = 0

    for (const file of files) {
        if (!TASK_PHOTO_TYPES.includes(
            file.type as (typeof TASK_PHOTO_TYPES)[number],
        )) {
            return `${file.name} is not a supported photo. Use JPEG, PNG or WebP.`
        }

        if (file.size > MAX_TASK_PHOTO_SIZE) {
            return `${file.name} exceeds the 25 MB per-photo limit.`
        }

        totalSize += file.size
    }

    if (totalSize > MAX_TASK_PHOTO_TOTAL_SIZE) {
        return 'Combined photo size exceeds the 100 MB limit.'
    }

    return null
}

export function createTaskPhotoFormData(
    inspectionId: string,
    files: File[],
): FormData {
    const formData = new FormData()

    formData.append('inspection_id', inspectionId)

    files.forEach(file => {
        formData.append('files[]', file, file.name)
    })

    return formData
}

/**
 * Development-only adapter.
 * Simulates a successful upload without transmitting files.
 */
export async function mockTaskPhotoUpload(
    formData: FormData,
    onProgress: (progress: number) => void,
): Promise<TaskPhotoUploadResult> {
    const files = formData.getAll('files[]')

    onProgress(0)
    await Promise.resolve()
    onProgress(100)

    return {
        mode: 'mock',
        uploadedCount: files.length,
    }
}

export { formatFileSize }
