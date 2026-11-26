
export const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
export const MAX_TOTAL_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024

export const ALLOWED_FILE_TYPES = [
    'image/jpeg',
    'image/png',
    'image/webp',
    'video/mp4',
    'video/webm',
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'text/csv',
] as const

export type UploadResult = {
    mode: 'mock'
    uploadedCount: number
}

export type UploadAdapter = (
    formData: FormData,
    onProgress: (progress: number) => void,
) => Promise<UploadResult>

export function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function validateInspectionFiles(files: File[]): string | null {
    let totalSize = 0

    for (const file of files) {
        const isAllowedType = ALLOWED_FILE_TYPES.includes(
            file.type as (typeof ALLOWED_FILE_TYPES)[number],
        )
        const isAllowedExt = /\.(jpe?g|png|webp|mp4|webm|pdf|xlsx|xls|csv)$/i.test(file.name)

        if (!isAllowedType && !isAllowedExt) {
            return `Unsupported file type: ${file.name}`
        }

        if (file.size > MAX_FILE_SIZE_BYTES) {
            return `${file.name} exceeds the 25 MB per-file limit.`
        }

        totalSize += file.size
    }

    if (totalSize > MAX_TOTAL_UPLOAD_SIZE_BYTES) {
        return 'Combined file size exceeds the 100 MB limit.'
    }

    return null
}

export function createInspectionFormData(
    siteId: string,
    files: File[],
): FormData {
    const formData = new FormData()

    formData.append('site_id', siteId)

    for (const file of files) {
        formData.append('files[]', file, file.name)
    }

    return formData
}

/**
 * Development adapter only.
 * It simulates completion; it does not transmit files to a server.
 */
export const mockUploadAdapter: UploadAdapter = async (
    formData,
    onProgress,
) => {
    const files = formData.getAll('files[]')

    onProgress(0)
    await Promise.resolve()
    onProgress(100)

    return {
        mode: 'mock',
        uploadedCount: files.length,
    }
}
