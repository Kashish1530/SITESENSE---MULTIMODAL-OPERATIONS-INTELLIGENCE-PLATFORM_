
import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DEMO_USERS, type DemoUser } from '../../src/data/users'
import { useOrganizationUsers } from '../../src/hooks/useOrganizationUsers'

const STORAGE_KEY = 'sitesense_demo_organization'

describe('useOrganizationUsers', () => {
    beforeEach(() => {
        vi.restoreAllMocks()
        sessionStorage.clear()
    })

    afterEach(() => {
        cleanup()
        vi.restoreAllMocks()
    })

    it('initializes with DEMO_USERS when no stored organization exists', () => {
        const { result } = renderHook(() => useOrganizationUsers())

        expect(result.current.users).toEqual(DEMO_USERS)
    })

    it('restores valid users from sessionStorage', () => {
        const storedUsers = DEMO_USERS.slice(0, 2)

        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(storedUsers))

        const { result } = renderHook(() => useOrganizationUsers())

        expect(result.current.users).toEqual(storedUsers)
    })

    it('falls back to DEMO_USERS when stored JSON is malformed', () => {
        sessionStorage.setItem(STORAGE_KEY, '{invalid json')

        const { result } = renderHook(() => useOrganizationUsers())

        expect(result.current.users).toEqual(DEMO_USERS)
    })

    it('falls back when stored data is not an array', () => {
        sessionStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({ users: DEMO_USERS }),
        )

        const { result } = renderHook(() => useOrganizationUsers())

        expect(result.current.users).toEqual(DEMO_USERS)
    })

    it('falls back when a stored user has an invalid role', () => {
        const invalidUsers = [
            {
                ...DEMO_USERS[0],
                role: 'owner',
            },
        ]

        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(invalidUsers))

        const { result } = renderHook(() => useOrganizationUsers())

        expect(result.current.users).toEqual(DEMO_USERS)
    })

    it('falls back when a stored user is missing a required field', () => {
        const invalidUser = { ...DEMO_USERS[0] } as Partial<DemoUser>
        delete invalidUser.employeeId

        sessionStorage.setItem(
            STORAGE_KEY,
            JSON.stringify([invalidUser]),
        )

        const { result } = renderHook(() => useOrganizationUsers())

        expect(result.current.users).toEqual(DEMO_USERS)
    })

    it('accepts an empty stored organization as valid', () => {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify([]))

        const { result } = renderHook(() => useOrganizationUsers())

        expect(result.current.users).toEqual([])
    })

    it('persists the initial organization users to sessionStorage', () => {
        renderHook(() => useOrganizationUsers())

        expect(sessionStorage.getItem(STORAGE_KEY)).toBe(
            JSON.stringify(DEMO_USERS),
        )
    })

    it('persists updated organization users to sessionStorage', () => {
        const { result } = renderHook(() => useOrganizationUsers())

        const updatedUsers = DEMO_USERS.slice(0, 2)

        act(() => {
            result.current.setUsers(updatedUsers)
        })

        expect(result.current.users).toEqual(updatedUsers)

        expect(sessionStorage.getItem(STORAGE_KEY)).toBe(
            JSON.stringify(updatedUsers),
        )
    })

    it('keeps users in memory when sessionStorage writing fails', () => {
        vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
            throw new Error('Storage unavailable')
        })

        const { result } = renderHook(() => useOrganizationUsers())

        expect(result.current.users).toEqual(DEMO_USERS)

        const updatedUsers = DEMO_USERS.slice(0, 1)

        act(() => {
            result.current.setUsers(updatedUsers)
        })

        expect(result.current.users).toEqual(updatedUsers)
    })

    it('falls back to DEMO_USERS when sessionStorage reading fails', () => {
        vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
            throw new Error('Storage unavailable')
        })

        const { result } = renderHook(() => useOrganizationUsers())

        expect(result.current.users).toEqual(DEMO_USERS)
    })
})
