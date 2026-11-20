
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import Header from '../../src/components/layout/Header'
import { DEMO_USERS } from '../../src/data/users'

afterEach(cleanup)

const admin = DEMO_USERS.find((user) => user.role === 'admin')!

function renderHeader(overrides = {}) {
    const onMenuClick = vi.fn()
    const onLogout = vi.fn()

    render(
        <Header
            onMenuClick={onMenuClick}
            activePage="Overview"
            currentUser={admin}
            onLogout={onLogout}
            {...overrides}
        />,
    )

    return { onMenuClick, onLogout }
}

describe('Header', () => {
    it('renders the active page title', () => {
        renderHeader()

        expect(
            screen.getByRole('heading', { name: 'Overview' }),
        ).toBeInTheDocument()
    })

    it('renders the current user name and role', () => {
        renderHeader()

        expect(screen.getByText(admin.name)).toBeInTheDocument()
        expect(screen.getByText(admin.role)).toBeInTheDocument()
    })

    it('renders the current user initials', () => {
        renderHeader()

        const initials = admin.name
            .split(' ')
            .map((part) => part[0])
            .join('')
            .slice(0, 2)
            .toUpperCase()

        expect(screen.getByText(initials)).toBeInTheDocument()
    })

    it('calls onMenuClick when the mobile navigation button is clicked', () => {
        const { onMenuClick } = renderHeader()

        fireEvent.click(
            screen.getByRole('button', { name: 'Open navigation' }),
        )

        expect(onMenuClick).toHaveBeenCalledOnce()
    })

    it('opens the account menu when clicked', () => {
        renderHeader()

        const accountButton = screen.getByRole('button', {
            name: 'Open account menu',
        })

        expect(accountButton).toHaveAttribute('aria-expanded', 'false')

        fireEvent.click(accountButton)

        expect(accountButton).toHaveAttribute('aria-expanded', 'true')
        expect(screen.getByText(admin.email)).toBeInTheDocument()
        expect(
            screen.getByRole('button', { name: /sign out/i }),
        ).toBeInTheDocument()
    })

    it('closes the account menu when clicked again', () => {
        renderHeader()

        const accountButton = screen.getByRole('button', {
            name: 'Open account menu',
        })

        fireEvent.click(accountButton)
        fireEvent.click(accountButton)

        expect(accountButton).toHaveAttribute('aria-expanded', 'false')
        expect(screen.queryByText(admin.email)).not.toBeInTheDocument()
    })

    it('calls onLogout when Sign out is clicked', () => {
        const { onLogout } = renderHeader()

        fireEvent.click(
            screen.getByRole('button', { name: 'Open account menu' }),
        )

        fireEvent.click(
            screen.getByRole('button', { name: /sign out/i }),
        )

        expect(onLogout).toHaveBeenCalledOnce()
        expect(
            screen.getByRole('button', { name: 'Open account menu' }),
        ).toHaveAttribute('aria-expanded', 'false')
    })

    it('renders search and notification controls', () => {
        renderHeader()

        expect(
            screen.getByRole('button', { name: 'Search' }),
        ).toBeInTheDocument()

        expect(
            screen.getByRole('button', { name: 'Notifications' }),
        ).toBeInTheDocument()
    })
})
