
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
    cleanup,
    fireEvent,
    render,
    screen,
    within,
} from '@testing-library/react'

import CreateInspectionModal from '../../src/components/inspections/CreateInspectionModal'
import { DEMO_USERS, type DemoUser } from '../../src/data/users'

afterEach(() => {
    cleanup()
})

const admin = DEMO_USERS.find(user => user.role === 'admin')!
const supervisor = DEMO_USERS.find(user => user.id === 'USER-002')!
const manager = DEMO_USERS.find(user => user.id === 'USER-005')!

function renderModal(
    currentUser: DemoUser = admin,
    users: DemoUser[] = DEMO_USERS,
) {
    const onClose = vi.fn()
    const onCreate = vi.fn()

    const result = render(
        <CreateInspectionModal
            currentUser={currentUser}
            users={users}
            onClose={onClose}
            onCreate={onCreate}
        />,
    )

    return { ...result, onClose, onCreate }
}

function selectSafetyTemplate() {
    fireEvent.click(
        screen.getByRole('button', { name: /general workplace safety/i }),
    )
}

function goToStepTwo() {
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
}

function getSiteSelect() {
    return screen.getAllByRole('combobox')[0] as HTMLSelectElement
}

function getAssigneeSelect() {
    return screen.getAllByRole('combobox')[1] as HTMLSelectElement
}

function getDueDateInput() {
    return document.querySelector(
        'input[type="date"]',
    ) as HTMLInputElement
}

function formatDate(date: Date) {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')

    return `${year}-${month}-${day}`
}

function getYesterday() {
    const date = new Date()
    date.setDate(date.getDate() - 1)
    return formatDate(date)
}

function getToday() {
    return formatDate(new Date())
}

describe('CreateInspectionModal', () => {
    it('renders the first step and active inspection templates', () => {
        renderModal()

        const dialog = screen.getByRole('dialog')

        expect(dialog).toBeInTheDocument()
        expect(dialog).toHaveTextContent('Step 1 of 2')

        expect(
            screen.getByRole('button', {
                name: /general workplace safety/i,
            }),
        ).toBeInTheDocument()

        expect(
            screen.getByRole('button', {
                name: /equipment inspection/i,
            }),
        ).toBeInTheDocument()

        expect(
            screen.getByRole('button', {
                name: /fire safety inspection/i,
            }),
        ).toBeInTheDocument()

        expect(
            screen.getByRole('button', {
                name: /housekeeping inspection/i,
            }),
        ).toBeInTheDocument()
    })

    it('populates title and description when a template is selected', () => {
        renderModal()

        selectSafetyTemplate()

        expect(
            screen.getByPlaceholderText('Enter inspection title'),
        ).toHaveValue('General Workplace Safety')

        expect(
            screen.getByPlaceholderText(
                'Describe the purpose of this inspection',
            ),
        ).toHaveValue(
            'Routine safety checks covering PPE, walkways and workplace hazards.',
        )
    })

    it('requires a title for a custom inspection', () => {
        renderModal()

        fireEvent.click(
            screen.getByRole('button', { name: /custom inspection/i }),
        )

        goToStepTwo()

        expect(screen.getByRole('alert')).toHaveTextContent(
            'Enter a title for your custom inspection.',
        )

        expect(screen.getByRole('dialog')).toHaveTextContent('Step 1 of 2')
    })

    it('allows administrators to select all sites', () => {
        renderModal()

        selectSafetyTemplate()
        goToStepTwo()

        const options = within(getSiteSelect()).getAllByRole('option')

        expect(options).toHaveLength(4)
        expect(options.map(option => option.textContent)).toContain(
            'North Warehouse',
        )
        expect(options.map(option => option.textContent)).toContain(
            'South Warehouse',
        )
        expect(options.map(option => option.textContent)).toContain(
            'Central Distribution Centre',
        )
    })

    it('restricts supervisors to their assigned site', () => {
        renderModal(supervisor)

        selectSafetyTemplate()
        goToStepTwo()

        const options = within(getSiteSelect()).getAllByRole('option')

        expect(options).toHaveLength(2)
        expect(options.map(option => option.textContent)).toContain(
            'North Warehouse',
        )
        expect(options.map(option => option.textContent)).not.toContain(
            'South Warehouse',
        )
    })

    it('shows managers only their own employees', () => {
        renderModal(manager)

        selectSafetyTemplate()
        goToStepTwo()

        const assigneeOptions = within(getAssigneeSelect())
            .getAllByRole('option')
            .map(option => option.textContent)

        expect(assigneeOptions).toContain('Noah Martin · employee')
        expect(assigneeOptions).toContain('Isabella Lee · employee')
        expect(assigneeOptions).toContain('Ethan Clark · employee')

        expect(assigneeOptions).not.toContain('Mia Rodriguez · employee')
    })

    it('excludes inactive users and administrator accounts from assignees', () => {
        const inactiveEmployee: DemoUser = {
            ...DEMO_USERS.find(user => user.id === 'USER-011')!,
            id: 'USER-099',
            name: 'Inactive Employee',
            isActive: false,
        }

        renderModal(admin, [...DEMO_USERS, inactiveEmployee])

        selectSafetyTemplate()
        goToStepTwo()

        // Admin must select a site before eligible assignees are displayed.
        fireEvent.change(getSiteSelect(), {
            target: { value: 'SITE-001' },
        })

        const assigneeOptions = within(getAssigneeSelect())
            .getAllByRole('option')
            .map(option => option.textContent)

        expect(assigneeOptions).not.toContain('Alex Morgan · admin')
        expect(assigneeOptions).not.toContain('Inactive Employee · employee')
        expect(assigneeOptions).toContain('James Wilson · manager')
    })

    it('rejects a past due date', () => {
        renderModal()

        selectSafetyTemplate()
        goToStepTwo()

        fireEvent.change(getSiteSelect(), {
            target: { value: 'SITE-001' },
        })

        fireEvent.change(getAssigneeSelect(), {
            target: { value: 'USER-011' },
        })

        fireEvent.change(
            screen.getByPlaceholderText(
                'e.g. Loading Bay, Storage Area',
            ),
            {
                target: { value: 'Loading Bay' },
            },
        )

        fireEvent.change(getDueDateInput(), {
            target: { value: getYesterday() },
        })

        fireEvent.click(
            screen.getByRole('button', { name: /create inspection/i }),
        )

        expect(screen.getByRole('alert')).toHaveTextContent(
            'Choose a valid due date.',
        )
    })

    it('creates an inspection with the correct data', () => {
        const { onCreate, onClose } = renderModal()

        fireEvent.click(
            screen.getByRole('button', { name: /fire safety inspection/i }),
        )

        goToStepTwo()

        fireEvent.change(getSiteSelect(), {
            target: { value: 'SITE-001' },
        })

        fireEvent.change(getAssigneeSelect(), {
            target: { value: 'USER-011' },
        })

        fireEvent.change(
            screen.getByPlaceholderText(
                'e.g. Loading Bay, Storage Area',
            ),
            {
                target: { value: 'Loading Bay' },
            },
        )

        fireEvent.change(getDueDateInput(), {
            target: { value: getToday() },
        })

        fireEvent.click(
            screen.getByRole('button', { name: /create inspection/i }),
        )

        expect(onCreate).toHaveBeenCalledTimes(1)

        const inspection = onCreate.mock.calls[0][0]

        expect(inspection).toMatchObject({
            title: 'Fire Safety Inspection',
            description:
                'Checks fire extinguishers, emergency routes and fire safety signage.',
            type: 'Fire Safety',
            templateId: 'TPL-FIRE-001',
            siteId: 'SITE-001',
            zone: 'Loading Bay',
            status: 'Scheduled',
            assignedToUserId: 'USER-011',
            assignedByUserId: admin.id,
            answers: [],
            observations: [],
            findingIds: [],
            evidenceIds: [],
        })

        expect(inspection.id).toMatch(/^INS-/)
        expect(inspection.createdAt).toBeTruthy()
        expect(inspection.scheduledAt).toBeTruthy()
        expect(inspection.dueDate).toBe(
            new Date(`${getToday()}T17:00:00`).toISOString(),
        )

        expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('closes the modal using Cancel and Close buttons', () => {
        const first = renderModal()

        fireEvent.click(screen.getByRole('button', { name: /cancel/i }))

        expect(first.onClose).toHaveBeenCalledTimes(1)

        first.unmount()

        const second = renderModal()

        fireEvent.click(
            screen.getByRole('button', { name: /close modal/i }),
        )

        expect(second.onClose).toHaveBeenCalledTimes(1)
    })
})
