import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import UploadPage from '../../src/components/upload/UploadPage'
import { DEMO_USERS } from '../../src/data/users'
import { INSPECTIONS } from '../../src/data/inspectionData'

describe('UploadPage component', () => {
    const adminUser = DEMO_USERS.find(u => u.role === 'admin') || DEMO_USERS[0]

    it('renders all 8 required sections and report generation options', () => {
        render(
            <UploadPage
                currentUser={adminUser}
                inspections={INSPECTIONS}
                evidence={[]}
                onInspect={vi.fn()}
                onNavigate={vi.fn()}
            />
        )

        // Section 1: Upload Statistics
        expect(screen.getByText('Total Uploads')).toBeInTheDocument()
        expect(screen.getAllByText('Completed').length).toBeGreaterThan(0)
        expect(screen.getAllByText('Processing').length).toBeGreaterThan(0)
        expect(screen.getAllByText('Failed').length).toBeGreaterThan(0)

        // Section 2: Inspection Details
        expect(screen.getByText('Inspection Details')).toBeInTheDocument()
        expect(screen.getByText(/Site Location/i)).toBeInTheDocument()
        expect(screen.getByText(/Operational Zone/i)).toBeInTheDocument()
        expect(screen.getByText(/Inspection Name \/ Title/i)).toBeInTheDocument()
        expect(screen.getByText(/Inspection Date/i)).toBeInTheDocument()
        expect(screen.getByText(/Camera \/ Capture Source/i)).toBeInTheDocument()

        // Section 3: Upload Files
        expect(screen.getByText('Upload Files')).toBeInTheDocument()
        expect(screen.getByText(/Drag and drop files here to upload/i)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /Browse Files/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /Capture Photo/i })).toBeInTheDocument()

        // Section 6: Recent Uploads
        expect(screen.getByText('Recent Uploads & Previous Inspections')).toBeInTheDocument()

        // Section 7: Filters
        expect(screen.getByText('All Sites')).toBeInTheDocument()
        expect(screen.getByText('All Statuses')).toBeInTheDocument()
        expect(screen.getByPlaceholderText(/Search inspection or zone/i)).toBeInTheDocument()

        // Section 8: Information Panel
        expect(screen.getByText('Information & Upload Instructions')).toBeInTheDocument()
        expect(screen.getAllByText(/MinIO Object Storage/i).length).toBeGreaterThan(0)

        // Final Section: Report Generation Options on All Points
        expect(screen.getByText('Report Generation on All Inspection Points')).toBeInTheDocument()
        expect(screen.getByText(/1\. Select Report Type/i)).toBeInTheDocument()
        expect(screen.getByText(/2\. Output Format/i)).toBeInTheDocument()
        expect(screen.getByText(/3\. Target Scope/i)).toBeInTheDocument()
        expect(screen.getAllByText(/Generate Official Report on All Points/i).length).toBeGreaterThan(0)
    })

    it('allows changing report options and compiling report', async () => {
        render(
            <UploadPage
                currentUser={adminUser}
                inspections={INSPECTIONS}
                evidence={[]}
                onInspect={vi.fn()}
                onNavigate={vi.fn()}
            />
        )

        const generateBtn = screen.getAllByText(/Generate Official Report on All Points/i)[0]
        expect(generateBtn).toBeInTheDocument()
        fireEvent.click(generateBtn)

        expect(await screen.findByText(/Compiling All Data Points/i)).toBeInTheDocument()
    })
})
