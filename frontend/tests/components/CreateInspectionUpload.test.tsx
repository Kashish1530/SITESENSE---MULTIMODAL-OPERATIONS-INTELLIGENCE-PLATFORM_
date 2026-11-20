
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'

import CreateInspectionModal from '../../src/components/inspections/CreateInspectionModal'
import { DEMO_USERS } from '../../src/data/users'
import type { UploadAdapter, UploadResult } from '../../src/inspections/uploadAdapter'

afterEach(cleanup)

const admin = DEMO_USERS.find(user => user.role === 'admin')!
const file = new File(['photo-content'], 'evidence.jpg', {
    type: 'image/jpeg',
})

function renderUploadModal(uploadAdapter: UploadAdapter) {
    const onClose = vi.fn()
    const onCreate = vi.fn()

    render(
        <CreateInspectionModal
            currentUser={admin}
            users={DEMO_USERS}
            onClose={onClose}
            onCreate={onCreate}
            uploadAdapter={uploadAdapter}
        />,
    )

    fireEvent.click(
        screen.getByRole('button', { name: /general workplace safety/i }),
    )
    fireEvent.click(screen.getByRole('button', { name: /next/i }))

    fireEvent.change(screen.getAllByRole('combobox')[0], {
        target: { value: 'SITE-001' },
    })

    fireEvent.change(screen.getAllByRole('combobox')[1], {
        target: { value: 'USER-011' },
    })

    fireEvent.change(
        screen.getByPlaceholderText('e.g. Loading Bay, Storage Area'),
        { target: { value: 'Loading Bay' } },
    )

    const date = new Date()
    const today = [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, '0'),
        String(date.getDate()).padStart(2, '0'),
    ].join('-')

    fireEvent.change(document.querySelector('input[type="date"]')!, {
        target: { value: today },
    })

    fireEvent.change(screen.getByLabelText('Choose evidence files'), {
        target: { files: [file] },
    })

    return { onClose, onCreate }
}

describe('CreateInspectionModal upload integration', () => {
    it('sends site_id and files[] through FormData and creates the inspection on success', async () => {
        let capturedFormData: FormData | undefined

        const uploadAdapter: UploadAdapter = vi.fn(
            async (
                formData: FormData,
                onProgress: (progress: number) => void,
            ): Promise<UploadResult> => {
                capturedFormData = formData
                onProgress(45)

                return {
                    mode: 'mock',
                    uploadedCount: 1,
                }
            },
        )

        const { onClose, onCreate } = renderUploadModal(uploadAdapter)

        fireEvent.click(
            screen.getByRole('button', { name: /create inspection/i }),
        )

        await waitFor(() => {
            expect(onCreate).toHaveBeenCalledTimes(1)
        })

        expect(uploadAdapter).toHaveBeenCalledTimes(1)
        expect(capturedFormData).toBeInstanceOf(FormData)
        expect(capturedFormData?.get('site_id')).toBe('SITE-001')
        expect(capturedFormData?.getAll('files[]')).toHaveLength(1)
        expect(capturedFormData?.getAll('files[]')[0]).toBeInstanceOf(File)
        expect((capturedFormData?.getAll('files[]')[0] as File).name)
            .toBe('evidence.jpg')

        expect(onCreate.mock.calls[0][1]).toEqual([file])
        expect(onCreate.mock.calls[0][0].siteId).toBe('SITE-001')
        expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('keeps the modal and selected files after failure and allows retry', async () => {
        let shouldFail = true

        const uploadAdapter: UploadAdapter = vi.fn(
            async (
                _formData: FormData,
                onProgress: (progress: number) => void,
            ): Promise<UploadResult> => {
                if (shouldFail) {
                    shouldFail = false
                    throw new Error('Simulated upload failure')
                }

                onProgress(100)

                return {
                    mode: 'mock',
                    uploadedCount: 1,
                }
            },
        )

        const { onClose, onCreate } = renderUploadModal(uploadAdapter)

        fireEvent.click(
            screen.getByRole('button', { name: /create inspection/i }),
        )

        expect(await screen.findByRole('alert'))
            .toHaveTextContent('Simulated upload failure')

        expect(screen.getByText('evidence.jpg')).toBeInTheDocument()
        expect(onCreate).not.toHaveBeenCalled()
        expect(onClose).not.toHaveBeenCalled()

        fireEvent.click(
            screen.getByRole('button', { name: /create inspection/i }),
        )

        await waitFor(() => {
            expect(onCreate).toHaveBeenCalledTimes(1)
        })

        expect(uploadAdapter).toHaveBeenCalledTimes(2)
        expect(onClose).toHaveBeenCalledTimes(1)
    })
})
