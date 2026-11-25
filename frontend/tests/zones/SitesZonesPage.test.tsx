
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
    cleanup,
    fireEvent,
    render,
    screen,
} from '@testing-library/react'

import SitesZonesPage from '../../src/components/zones/SitesZonesPage'
import { DEMO_USERS } from '../../src/data/users'

const admin = DEMO_USERS.find(user => user.id === 'USER-001')!
const northSupervisor = DEMO_USERS.find(user => user.id === 'USER-002')!

afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
})

describe('SitesZonesPage', () => {
    describe('site access', () => {
        it('shows all sites to an admin', () => {
            render(<SitesZonesPage currentUser={admin} />)

            const siteSelect = screen.getByRole('combobox', {
                name: 'Site',
            }) as HTMLSelectElement

            expect(siteSelect.options).toHaveLength(3)
            expect(siteSelect).toHaveValue('SITE-001')
            expect(screen.getByRole('button', {
                name: 'Edit configuration',
            })).toBeInTheDocument()
        })

        it('limits a supervisor to their assigned site', () => {
            render(<SitesZonesPage currentUser={northSupervisor} />)

            const siteSelect = screen.getByRole('combobox', {
                name: 'Site',
            }) as HTMLSelectElement

            expect(siteSelect.options).toHaveLength(1)
            expect(siteSelect).toHaveValue('SITE-001')
            expect(siteSelect.options[0].text).toBe('North Warehouse')

            expect(screen.queryByRole('button', {
                name: 'Edit configuration',
            })).not.toBeInTheDocument()

            expect(screen.getAllByRole('checkbox').every(
                checkbox => (checkbox as HTMLInputElement).disabled,
            )).toBe(true)
        })
    })

    describe('editing behavior', () => {
        it('does not enter edit mode when switching cameras', () => {
            render(<SitesZonesPage currentUser={admin} />)

            const cameraSelect = screen.getByRole('combobox', {
                name: 'Camera',
            }) as HTMLSelectElement

            expect(screen.getAllByRole('checkbox').every(
                checkbox => (checkbox as HTMLInputElement).disabled,
            )).toBe(true)

            fireEvent.change(cameraSelect, {
                target: { value: 'SITE-001-CAM-02' },
            })

            expect(cameraSelect).toHaveValue('SITE-001-CAM-02')
            expect(screen.getByRole('button', {
                name: 'Edit configuration',
            })).toBeInTheDocument()

            expect(screen.getAllByRole('checkbox').every(
                checkbox => (checkbox as HTMLInputElement).disabled,
            )).toBe(true)
        })

        it('allows class changes only after explicitly entering edit mode', () => {
            render(<SitesZonesPage currentUser={admin} />)

            const firstCheckbox = screen.getAllByRole('checkbox')[0]

            expect(firstCheckbox).toBeDisabled()

            fireEvent.click(screen.getByRole('button', {
                name: 'Edit configuration',
            }))

            expect(firstCheckbox).toBeEnabled()
        })

        it('saves changes and Discard restores the last saved state', () => {
            render(<SitesZonesPage currentUser={admin} />)

            fireEvent.click(screen.getByRole('button', {
                name: 'Edit configuration',
            }))

            const firstCheckbox = screen.getAllByRole('checkbox')[0]

            fireEvent.click(firstCheckbox)

            expect(firstCheckbox).toBeChecked()
            expect(screen.getByText(/Unsaved changes/)).toBeInTheDocument()

            const saveButton = screen.getByRole('button', {
                name: 'Save changes',
            })

            expect(saveButton).toBeEnabled()
            fireEvent.click(saveButton)

            expect(screen.getByRole('button', {
                name: 'Edit configuration',
            })).toBeInTheDocument()

            expect(screen.getAllByRole('checkbox')[0]).toBeChecked()
            expect(screen.getAllByRole('checkbox').every(
                checkbox => (checkbox as HTMLInputElement).disabled,
            )).toBe(true)

            fireEvent.click(screen.getByRole('button', {
                name: 'Edit configuration',
            }))

            fireEvent.click(screen.getAllByRole('checkbox')[0])

            expect(screen.getAllByRole('checkbox')[0]).not.toBeChecked()

            fireEvent.click(screen.getByRole('button', {
                name: 'Discard',
            }))

            expect(screen.getAllByRole('checkbox')[0]).toBeChecked()
            expect(screen.getByRole('button', {
                name: 'Edit configuration',
            })).toBeInTheDocument()
        })
    })

    describe('unsaved changes protection', () => {
        it('keeps the current camera when the user cancels switching', () => {
            const confirmSpy = vi.spyOn(window, 'confirm')
                .mockReturnValue(false)

            render(<SitesZonesPage currentUser={admin} />)

            fireEvent.click(screen.getByRole('button', {
                name: 'Edit configuration',
            }))

            fireEvent.click(screen.getAllByRole('checkbox')[0])

            const cameraSelect = screen.getByRole('combobox', {
                name: 'Camera',
            }) as HTMLSelectElement

            fireEvent.change(cameraSelect, {
                target: { value: 'SITE-001-CAM-02' },
            })

            expect(confirmSpy).toHaveBeenCalledOnce()
            expect(cameraSelect).toHaveValue('SITE-001-CAM-01')
            expect(screen.getByText(/Unsaved changes/)).toBeInTheDocument()
        })

        it('discards unsaved changes and switches when the user confirms', () => {
            vi.spyOn(window, 'confirm').mockReturnValue(true)

            render(<SitesZonesPage currentUser={admin} />)

            fireEvent.click(screen.getByRole('button', {
                name: 'Edit configuration',
            }))

            fireEvent.click(screen.getAllByRole('checkbox')[0])

            const cameraSelect = screen.getByRole('combobox', {
                name: 'Camera',
            }) as HTMLSelectElement

            fireEvent.change(cameraSelect, {
                target: { value: 'SITE-001-CAM-02' },
            })

            expect(cameraSelect).toHaveValue('SITE-001-CAM-02')
            expect(screen.queryByText(/Unsaved changes/)).not.toBeInTheDocument()

            expect(screen.getByRole('button', {
                name: 'Edit configuration',
            })).toBeInTheDocument()

            expect(screen.getAllByRole('checkbox').every(
                checkbox => (checkbox as HTMLInputElement).disabled,
            )).toBe(true)
        })
    })
})
