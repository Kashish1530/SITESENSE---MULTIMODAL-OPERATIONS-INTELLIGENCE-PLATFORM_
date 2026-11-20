
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'

import App from '../src/App'
import { DEMO_USERS, type DemoUser } from '../src/data/users'

const appTestMocks = vi.hoisted(() => ({
    deactivateEmployee: null as null | ((userId: string) => void),
}))

vi.mock('../src/components/layout/AppLayout', () => ({
    default: ({
        children,
        activePage,
        onNavigate,
        currentUser,
        actualUser,
        isPreviewMode,
        onExitPreview,
        onLogout,
    }: {
        children: ReactNode
        activePage: string
        onNavigate: (page: string) => void
        currentUser: DemoUser
        actualUser: DemoUser
        isPreviewMode: boolean
        onExitPreview: () => void
        onLogout: () => void
    }) => (
        <div>
            <div data-testid="active-page">{activePage}</div>
            <div data-testid="current-user">{currentUser.id}</div>
            <div data-testid="actual-user">{actualUser.id}</div>

            <button onClick={() => onNavigate('Overview')}>Overview</button>
            <button onClick={() => onNavigate('Team')}>Team</button>
            <button onClick={() => onNavigate('Search')}>Search</button>
            <button onClick={() => onNavigate('Inspections')}>Inspections</button>
            <button onClick={() => onNavigate('Settings')}>Settings</button>
            <button onClick={() => onNavigate('Upload')}>Upload</button>
            <button onClick={() => onNavigate('Review Queue')}>Review Queue</button>
            <button onClick={() => onNavigate('My Tasks')}>My Tasks</button>
            <button onClick={onLogout}>Logout</button>

            {isPreviewMode && (
                <button onClick={onExitPreview}>Exit Preview</button>
            )}

            {children}
        </div>
    ),
}))

vi.mock('../src/components/dashboard/Overview', () => ({
    default: () => <div data-testid="admin-dashboard">Admin Overview</div>,
}))

vi.mock('../src/components/dashboard/SupervisorDashboard', () => ({
    default: () => (
        <div data-testid="supervisor-dashboard">Supervisor Dashboard</div>
    ),
}))

vi.mock('../src/components/dashboard/ManagerDashboard', () => ({
    default: () => <div data-testid="manager-dashboard">Manager Dashboard</div>,
}))

vi.mock('../src/components/dashboard/EmployeeDashboard', () => ({
    default: () => (
        <div data-testid="employee-dashboard">Employee Dashboard</div>
    ),
}))

vi.mock('../src/components/search/EmployeeSearch', () => ({
    default: () => <div data-testid="employee-search">Employee Search</div>,
}))

vi.mock('../src/components/inspections/InspectionDashboard', () => ({
    default: () => (
        <div data-testid="inspection-dashboard">Inspection Workspace</div>
    ),
}))

vi.mock('../src/components/dashboard/TeamManagement', () => ({
    default: ({
        onPreviewUser,
        onDeactivateEmployee,
    }: {
        onPreviewUser: (user: DemoUser) => void
        onDeactivateEmployee: (userId: string) => void
    }) => {
        appTestMocks.deactivateEmployee = onDeactivateEmployee

        return (
            <div data-testid="team-management">
                <button
                    onClick={() =>
                        onPreviewUser({
                            id: 'USER-011',
                            role: 'employee',
                            isActive: true,
                        } as DemoUser)
                    }
                >
                    Preview employee
                </button>

                <button onClick={() => onDeactivateEmployee('USER-011')}>
                    Deactivate preview employee
                </button>
            </div>
        )
    },
}))

const admin = DEMO_USERS.find(user => user.role === 'admin')!
const employee = DEMO_USERS.find(user => user.id === 'USER-011')!
const supervisor = DEMO_USERS.find(user => user.role === 'supervisor')!
const manager = DEMO_USERS.find(user => user.role === 'manager')!

function loginAs(user: DemoUser) {
    fireEvent.change(screen.getByLabelText('Email or Employee ID'), {
        target: { value: user.email },
    })

    fireEvent.change(screen.getByLabelText('Password'), {
        target: { value: user.password },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
}

beforeEach(() => {
    sessionStorage.clear()
    appTestMocks.deactivateEmployee = null
})

afterEach(() => {
    cleanup()
})

describe('App integration', () => {
    it('shows the login screen when no session exists', () => {
        render(<App />)

        expect(
            screen.getByRole('heading', { name: 'Sign in to SiteSense' }),
        ).toBeInTheDocument()
    })

    it('logs in an admin and displays the admin dashboard', () => {
        render(<App />)

        loginAs(admin)

        expect(screen.getByTestId('admin-dashboard')).toBeInTheDocument()
        expect(screen.getByTestId('current-user')).toHaveTextContent(admin.id)
        expect(sessionStorage.getItem('sitesense_demo_session')).toBe(admin.id)
    })

    it('displays an error for invalid credentials', () => {
        render(<App />)

        fireEvent.change(screen.getByLabelText('Email or Employee ID'), {
            target: { value: admin.email },
        })

        fireEvent.change(screen.getByLabelText('Password'), {
            target: { value: 'incorrect-password' },
        })

        fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

        expect(screen.getByRole('alert')).toHaveTextContent(
            'Invalid email, employee ID or password.',
        )

        expect(sessionStorage.getItem('sitesense_demo_session')).toBeNull()
    })

    it('logs in an employee and displays the employee dashboard', () => {
        render(<App />)

        loginAs(employee)

        expect(screen.getByTestId('employee-dashboard')).toBeInTheDocument()
        expect(screen.getByTestId('active-page')).toHaveTextContent('My Dashboard')
    })

    it('restores an existing admin session', () => {
        sessionStorage.setItem('sitesense_demo_session', admin.id)

        render(<App />)

        expect(screen.getByTestId('admin-dashboard')).toBeInTheDocument()
        expect(screen.getByTestId('current-user')).toHaveTextContent(admin.id)
    })

    it('restores an employee session to the employee landing page', () => {
        sessionStorage.setItem('sitesense_demo_session', employee.id)

        render(<App />)

        expect(screen.getByTestId('employee-dashboard')).toBeInTheDocument()
        expect(screen.getByTestId('active-page')).toHaveTextContent('My Dashboard')
    })

    it('clears an invalid stored session and displays login', () => {
        sessionStorage.setItem('sitesense_demo_session', 'UNKNOWN-USER')

        render(<App />)

        expect(
            screen.getByRole('heading', { name: 'Sign in to SiteSense' }),
        ).toBeInTheDocument()

        expect(sessionStorage.getItem('sitesense_demo_session')).toBeNull()
    })

    it('logs out and clears the session', () => {
        sessionStorage.setItem('sitesense_demo_session', admin.id)

        render(<App />)

        fireEvent.click(screen.getByRole('button', { name: 'Logout' }))

        expect(
            screen.getByRole('heading', { name: 'Sign in to SiteSense' }),
        ).toBeInTheDocument()

        expect(sessionStorage.getItem('sitesense_demo_session')).toBeNull()
    })

    it('allows an admin to preview an employee', () => {
        sessionStorage.setItem('sitesense_demo_session', admin.id)

        render(<App />)

        fireEvent.click(screen.getByRole('button', { name: 'Team' }))
        fireEvent.click(screen.getByRole('button', { name: 'Preview employee' }))

        expect(screen.getByTestId('employee-dashboard')).toBeInTheDocument()
        expect(screen.getByTestId('current-user')).toHaveTextContent(employee.id)
        expect(screen.getByTestId('actual-user')).toHaveTextContent(admin.id)
        expect(
            screen.getByRole('button', { name: 'Exit Preview' }),
        ).toBeInTheDocument()
    })

    it('exits employee preview and returns to the admin dashboard', () => {
        sessionStorage.setItem('sitesense_demo_session', admin.id)

        render(<App />)

        fireEvent.click(screen.getByRole('button', { name: 'Team' }))
        fireEvent.click(screen.getByRole('button', { name: 'Preview employee' }))
        fireEvent.click(screen.getByRole('button', { name: 'Exit Preview' }))

        expect(screen.getByTestId('admin-dashboard')).toBeInTheDocument()
        expect(screen.getByTestId('current-user')).toHaveTextContent(admin.id)
        expect(sessionStorage.getItem('sitesense_demo_session')).toBe(admin.id)
    })

    it('exits preview when the previewed employee is deactivated', () => {
        sessionStorage.setItem('sitesense_demo_session', admin.id)

        render(<App />)

        fireEvent.click(screen.getByRole('button', { name: 'Team' }))

        expect(appTestMocks.deactivateEmployee).toBeTypeOf('function')

        fireEvent.click(screen.getByRole('button', { name: 'Preview employee' }))

        act(() => {
            appTestMocks.deactivateEmployee?.('USER-011')
        })

        expect(screen.getByTestId('admin-dashboard')).toBeInTheDocument()
        expect(screen.getByTestId('current-user')).toHaveTextContent(admin.id)
        expect(sessionStorage.getItem('sitesense_demo_session')).toBe(admin.id)
    })

    it('does not allow an employee to navigate directly to Team', () => {
        sessionStorage.setItem('sitesense_demo_session', employee.id)

        render(<App />)

        fireEvent.click(screen.getByRole('button', { name: 'Team' }))

        expect(screen.getByTestId('active-page')).toHaveTextContent('My Dashboard')
        expect(screen.getByTestId('employee-dashboard')).toBeInTheDocument()
        expect(screen.queryByTestId('team-management')).not.toBeInTheDocument()
    })

    it('does not allow an employee to navigate directly to Settings', () => {
        sessionStorage.setItem('sitesense_demo_session', employee.id)

        render(<App />)

        fireEvent.click(screen.getByRole('button', { name: 'Settings' }))

        expect(screen.getByTestId('active-page')).toHaveTextContent('My Dashboard')
    })

    it('does not allow a supervisor to navigate directly to Settings', () => {
        sessionStorage.setItem('sitesense_demo_session', supervisor.id)

        render(<App />)

        fireEvent.click(screen.getByRole('button', { name: 'Settings' }))

        expect(screen.getByTestId('active-page')).toHaveTextContent('Overview')
        expect(screen.getByTestId('supervisor-dashboard')).toBeInTheDocument()
    })

    it('does not allow a manager to navigate directly to Settings', () => {
        sessionStorage.setItem('sitesense_demo_session', manager.id)

        render(<App />)

        fireEvent.click(screen.getByRole('button', { name: 'Settings' }))

        expect(screen.getByTestId('active-page')).toHaveTextContent('Overview')
        expect(screen.getByTestId('manager-dashboard')).toBeInTheDocument()
    })

    it('allows an admin to navigate to Settings', () => {
        sessionStorage.setItem('sitesense_demo_session', admin.id)

        render(<App />)

        fireEvent.click(screen.getByRole('button', { name: 'Settings' }))

        expect(screen.getByTestId('active-page')).toHaveTextContent('Settings')
        expect(screen.getByText('This workspace module is coming soon.')).toBeInTheDocument()
    })

    it('does not grant admin navigation permissions during employee preview', () => {
        sessionStorage.setItem('sitesense_demo_session', admin.id)

        render(<App />)

        fireEvent.click(screen.getByRole('button', { name: 'Team' }))
        fireEvent.click(screen.getByRole('button', { name: 'Preview employee' }))

        fireEvent.click(screen.getByRole('button', { name: 'Team' }))

        expect(screen.getByTestId('active-page')).toHaveTextContent('My Dashboard')
        expect(screen.getByTestId('current-user')).toHaveTextContent(employee.id)
        expect(screen.getByTestId('actual-user')).toHaveTextContent(admin.id)
        expect(screen.queryByTestId('team-management')).not.toBeInTheDocument()
    })

    it('navigates to the employee search workspace', () => {
        sessionStorage.setItem('sitesense_demo_session', admin.id)

        render(<App />)

        fireEvent.click(screen.getByRole('button', { name: 'Search' }))

        expect(screen.getByTestId('employee-search')).toBeInTheDocument()
        expect(screen.getByTestId('active-page')).toHaveTextContent('Search')
    })

    it('opens the inspection workspace with the authenticated user', () => {
        sessionStorage.setItem('sitesense_demo_session', supervisor.id)

        render(<App />)

        fireEvent.click(screen.getByRole('button', { name: 'Inspections' }))

        expect(screen.getByTestId('inspection-dashboard')).toBeInTheDocument()
        expect(screen.getByTestId('current-user')).toHaveTextContent(supervisor.id)
    })

    it('allows a manager to navigate to Upload because it is in their role navigation', () => {
        sessionStorage.setItem('sitesense_demo_session', manager.id)

        render(<App />)

        fireEvent.click(screen.getByRole('button', { name: 'Upload' }))

        expect(screen.getByTestId('active-page')).toHaveTextContent('Upload')
    })
})
