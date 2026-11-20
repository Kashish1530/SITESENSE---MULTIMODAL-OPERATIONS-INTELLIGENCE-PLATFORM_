
import {
    cleanup,
    fireEvent,
    render,
    screen,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useState } from 'react'

import InspectionEvidenceUploader from '../../src/components/inspections/InspectionEvidenceUploader'

afterEach(() => {
    cleanup()
})

function TestUploader() {
    const [files, setFiles] = useState<File[]>([])

    return (
        <InspectionEvidenceUploader
            files={files}
            onFilesChange={setFiles}
        />
    )
}

function createFile(
    name: string,
    type: string,
    size = 1024,
) {
    return new File(
        [new Uint8Array(size)],
        name,
        { type },
    )
}

describe('InspectionEvidenceUploader', () => {
    it('renders file selection and camera controls', () => {
        render(<TestUploader />)

        expect(
            screen.getByLabelText('Choose evidence files'),
        ).toBeInTheDocument()

        expect(
            screen.getByLabelText('Take a photo'),
        ).toBeInTheDocument()
    })

    it('accepts a supported JPEG file', () => {
        render(<TestUploader />)

        const file = createFile('site-photo.jpg', 'image/jpeg')

        fireEvent.change(
            screen.getByLabelText('Choose evidence files'),
            { target: { files: [file] } },
        )

        expect(screen.getByText('site-photo.jpg')).toBeInTheDocument()
        expect(screen.getByText('Selected evidence (1)')).toBeInTheDocument()
    })

    it('accepts multiple supported files', () => {
        render(<TestUploader />)

        const files = [
            createFile('photo.png', 'image/png'),
            createFile('video.mp4', 'video/mp4'),
            createFile('report.pdf', 'application/pdf'),
        ]

        fireEvent.change(
            screen.getByLabelText('Choose evidence files'),
            { target: { files } },
        )

        expect(screen.getByText('Selected evidence (3)')).toBeInTheDocument()
    })

    it('rejects unsupported file types', () => {
        render(<TestUploader />)

        const file = createFile('script.exe', 'application/octet-stream')

        fireEvent.change(
            screen.getByLabelText('Choose evidence files'),
            { target: { files: [file] } },
        )

        expect(screen.getByRole('alert')).toHaveTextContent(
            'Unsupported file type',
        )
        expect(screen.queryByText('script.exe')).not.toBeInTheDocument()
    })

    it('rejects files larger than 25 MB', () => {
        render(<TestUploader />)

        const file = createFile(
            'large-video.mp4',
            'video/mp4',
            26 * 1024 * 1024,
        )

        fireEvent.change(
            screen.getByLabelText('Choose evidence files'),
            { target: { files: [file] } },
        )

        expect(screen.getByRole('alert')).toHaveTextContent(
            '25 MB per-file limit',
        )
    })

    it('rejects combined files larger than 100 MB', () => {
        render(<TestUploader />)

        const files = Array.from({ length: 6 }, (_, index) => {
            const file = createFile(`video-${index}.mp4`, 'video/mp4')

            Object.defineProperty(file, 'size', {
                value: 20 * 1024 * 1024,
            })

            return file
        })

        fireEvent.change(
            screen.getByLabelText('Choose evidence files'),
            { target: { files } },
        )

        expect(screen.getByRole('alert')).toHaveTextContent(
            '100 MB limit',
        )
    })

    it('supports drag and drop', () => {
        render(<TestUploader />)

        const dropArea = screen.getByText(
            'Drag and drop evidence files here',
        ).parentElement

        const file = createFile('dropped.webp', 'image/webp')

        expect(dropArea).not.toBeNull()

        fireEvent.drop(dropArea!, {
            dataTransfer: { files: [file] },
        })

        expect(screen.getByText('dropped.webp')).toBeInTheDocument()
    })

    it('removes a selected file', () => {
        render(<TestUploader />)

        const file = createFile('remove-me.pdf', 'application/pdf')

        fireEvent.change(
            screen.getByLabelText('Choose evidence files'),
            { target: { files: [file] } },
        )

        fireEvent.click(
            screen.getByRole('button', { name: 'Remove remove-me.pdf' }),
        )

        expect(screen.queryByText('remove-me.pdf')).not.toBeInTheDocument()
        expect(
            screen.queryByText('Selected evidence (1)'),
        ).not.toBeInTheDocument()
    })

    it('uses the rear camera capture preference', () => {
        render(<TestUploader />)

        const cameraInput = screen.getByLabelText('Take a photo')

        expect(cameraInput).toHaveAttribute('capture', 'environment')
        expect(cameraInput).toHaveAttribute('accept', 'image/*')
    })

    it('does not allow changes when disabled', () => {
        const onFilesChange = vi.fn()

        render(
            <InspectionEvidenceUploader
                files={[]}
                onFilesChange={onFilesChange}
                disabled
            />,
        )

        expect(screen.getByLabelText('Choose evidence files')).toBeDisabled()
        expect(screen.getByLabelText('Take a photo')).toBeDisabled()
    })
})
