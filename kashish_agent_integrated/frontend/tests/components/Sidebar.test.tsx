
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import Sidebar from '../../src/components/layout/Sidebar'
import { DEMO_USERS } from '../../src/data/users'

afterEach(cleanup)

const admin = DEMO_USERS.find((user) => user.role === 'admin')!
const supervisor = DEMO_USERS.find(
    (user) => user.role === 'supervisor',
)!
const manager = DEMO_USERS.find((user) => user.role === 'manager')!
const employee = DEMO_USERS.find((user) => user.role === 'employee')!

function renderSidebar(
    currentUser = admin,
    overrides: {
        collapsed?: boolean
        mobileOpen?: boolean
        activePage?: string
    } = {},
) {
    const onToggle = vi.fn()
    const onMobileClose = vi.fn()
    const onNavigate = vi.fn()

    render(
        <Sidebar
            collapsed={overrides.collapsed ?? false}
            onToggle={onToggle}
            mobileOpen={overrides.mobileOpen ?? false}
            onMobileClose={onMobileClose}
            activePage={overrides.activePage ?? 'Overview'}
            onNavigate={onNavigate}
            currentUser={currentUser}
        />,
    )

    return { onToggle, onMobileClose, onNavigate }
}

describe('Sidebar', () => {
    it('renders the SiteSense branding', () => {
        renderSidebar()

        expect(screen.getByText('SiteSense')).toBeInTheDocument()
        expect(
            screen.getByText('Operations Intelligence'),
        ).toBeInTheDocument()
    })

    it('renders admin navigation items', () => {
        renderSidebar(admin)

        expect(screen.getByRole('button', { name: 'Overview' })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: 'Search' })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: 'Inspections' })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: 'Team' })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: 'Settings' })).toBeInTheDocument()
    })

    it('does not show admin-only navigation to employees', () => {
        renderSidebar(employee)

        expect(
            screen.getByRole('button', { name: 'My Dashboard' }),
        ).toBeInTheDocument()

        expect(
            screen.getByRole('button', { name: 'My Tasks' }),
        ).toBeInTheDocument()

        expect(
            screen.queryByRole('button', { name: 'Team' }),
        ).not.toBeInTheDocument()

        expect(
            screen.queryByRole('button', { name: 'Settings' }),
        ).not.toBeInTheDocument()
    })

    it('renders supervisor navigation according to role permissions', () => {
        renderSidebar(supervisor)

        expect(
            screen.getByRole('button', { name: 'Review Queue' }),
        ).toBeInTheDocument()

        expect(
            screen.getByRole('button', { name: 'Sites & Zones' }),
        ).toBeInTheDocument()

        expect(
            screen.queryByRole('button', { name: 'Settings' }),
        ).not.toBeInTheDocument()
    })

    it('renders manager navigation according to role permissions', () => {
        renderSidebar(manager)

        expect(
            screen.getByRole('button', { name: 'Upload' }),
        ).toBeInTheDocument()

        expect(
            screen.getByRole('button', { name: 'Team' }),
        ).toBeInTheDocument()

        expect(
            screen.queryByRole('button', { name: 'Settings' }),
        ).not.toBeInTheDocument()
    })

    it('calls onNavigate and closes mobile navigation after selecting an item', () => {
        const { onNavigate, onMobileClose } = renderSidebar(admin, {
            mobileOpen: true,
        })

        fireEvent.click(
            screen.getByRole('button', { name: 'Inspections' }),
        )

        expect(onNavigate).toHaveBeenCalledWith('Inspections')
        expect(onMobileClose).toHaveBeenCalledOnce()
    })

    it('highlights the active navigation item', () => {
        renderSidebar(admin, { activePage: 'Inspections' })

        const inspectionsButton = screen.getByRole('button', {
            name: 'Inspections',
        })

        expect(inspectionsButton.className).toContain('bg-blue-50')
        expect(inspectionsButton.className).toContain('text-blue-700')
    })

    it('calls onToggle when the collapse button is clicked', () => {
        const { onToggle } = renderSidebar(admin)

        fireEvent.click(
            screen.getByRole('button', { name: 'Collapse sidebar' }),
        )

        expect(onToggle).toHaveBeenCalledOnce()
    })

    it('shows the expand control when collapsed', () => {
        const { onToggle } = renderSidebar(admin, { collapsed: true })

        fireEvent.click(
            screen.getByRole('button', { name: 'Expand sidebar' }),
        )

        expect(onToggle).toHaveBeenCalledOnce()
    })

    it('renders the mobile overlay when navigation is open', () => {
        const { onMobileClose } = renderSidebar(admin, {
            mobileOpen: true,
        })

        fireEvent.click(
            screen.getByRole('button', { name: 'Close navigation' }),
        )

        expect(onMobileClose).toHaveBeenCalledOnce()
    })

    it('renders the sidebar close button for mobile', () => {
        const { onMobileClose } = renderSidebar(admin, {
            mobileOpen: true,
        })

        fireEvent.click(
            screen.getByRole('button', { name: 'Close sidebar' }),
        )

        expect(onMobileClose).toHaveBeenCalledOnce()
    })
})
