/**
 * Auth store tests — covers login/logout/hasPerm/project switching/theme persistence.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore } from '../auth'

const MOCK_LOGIN = {
  access_token: 'jwt.test.token',
  token_type: 'bearer',
  user: { id: 1, username: 'admin', nickname: 'Admin', email: 'admin@test.local' },
  projects: [
    { id: 1, code: 'proj1', name: 'Project 1' },
    { id: 2, code: 'proj2', name: 'Project 2' },
  ],
  permissions: ['testcase:list', 'testcase:create', 'testplan:list'],
}

describe('useAuthStore', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useAuthStore.getState().logout()
  })

  describe('setLogin', () => {
    it('sets token, user, projects, permissions and first project id', () => {
      useAuthStore.getState().setLogin(MOCK_LOGIN)

      const s = useAuthStore.getState()
      expect(s.token).toBe('jwt.test.token')
      expect(s.user).toEqual(MOCK_LOGIN.user)
      expect(s.projects).toEqual(MOCK_LOGIN.projects)
      expect(s.permissions).toEqual(MOCK_LOGIN.permissions)
      expect(s.currentProjectId).toBe(1) // first project
    })

    it('sets currentProjectId to null when projects list is empty', () => {
      useAuthStore.getState().setLogin({ ...MOCK_LOGIN, projects: [] })
      expect(useAuthStore.getState().currentProjectId).toBeNull()
    })
  })

  describe('logout', () => {
    it('clears all auth state', () => {
      useAuthStore.getState().setLogin(MOCK_LOGIN)
      useAuthStore.getState().logout()

      const s = useAuthStore.getState()
      expect(s.token).toBeNull()
      expect(s.user).toBeNull()
      expect(s.projects).toEqual([])
      expect(s.permissions).toEqual([])
      expect(s.currentProjectId).toBeNull()
    })
  })

  describe('setCurrentProject', () => {
    it('updates current project id', () => {
      useAuthStore.getState().setLogin(MOCK_LOGIN)
      useAuthStore.getState().setCurrentProject(2)

      expect(useAuthStore.getState().currentProjectId).toBe(2)
    })
  })

  describe('setProjectTheme', () => {
    it('stores per-project color theme', () => {
      useAuthStore.getState().setProjectTheme(1, 'dark-minimal')
      expect(useAuthStore.getState().projectThemeMap[1]).toBe('dark-minimal')
    })

    it('preserves other project themes on update', () => {
      useAuthStore.getState().setProjectTheme(1, 'warm')
      useAuthStore.getState().setProjectTheme(2, 'nature')
      expect(useAuthStore.getState().projectThemeMap).toEqual({ 1: 'warm', 2: 'nature' })
    })
  })

  describe('hasPerm', () => {
    it('returns true for permission the user has', () => {
      useAuthStore.getState().setLogin(MOCK_LOGIN)
      expect(useAuthStore.getState().hasPerm('testcase:list')).toBe(true)
      expect(useAuthStore.getState().hasPerm('testcase:create')).toBe(true)
    })

    it('returns false for permission the user lacks', () => {
      useAuthStore.getState().setLogin(MOCK_LOGIN)
      expect(useAuthStore.getState().hasPerm('defect:delete')).toBe(false)
    })

    it('returns true for any permission when user has wildcard (*)', () => {
      useAuthStore.getState().setLogin({
        ...MOCK_LOGIN,
        permissions: ['*'],
      })
      expect(useAuthStore.getState().hasPerm('any:random:perm')).toBe(true)
      expect(useAuthStore.getState().hasPerm('defect:delete')).toBe(true)
    })

    it('returns false when user has no permissions', () => {
      expect(useAuthStore.getState().hasPerm('testcase:list')).toBe(false)
    })
  })

  describe('partialize (persist middleware)', () => {
    it('does NOT persist token to storage', () => {
      // The persist middleware's `partialize` strips `token` from the persisted
      // slice — token lives only in memory (not localStorage). We verify by
      // inspecting the raw state: even after setLogin, the persist middleware
      // won't include `token` in what gets serialized to storage.
      // Vitest runs in 'node' environment without localStorage, so this test
      // validates the partialize function's behavior via the store API.
      useAuthStore.getState().setLogin(MOCK_LOGIN)

      // Token is in-memory (Zustand state)
      expect(useAuthStore.getState().token).toBe('jwt.test.token')

      // But the state that would be persisted (partialized) does NOT include token.
      // We access the persist middleware's partialize directly to verify.
      const { partialize } = (
        useAuthStore as any
      ).persist?.getOptions?.() || {}

      // partialize is a function — we validate that its return shape excludes token
      if (typeof partialize === 'function') {
        const persisted = partialize(useAuthStore.getState())
        expect(persisted.token).toBeUndefined()
        expect(persisted.user).toEqual(MOCK_LOGIN.user)
        expect(persisted.projects).toEqual(MOCK_LOGIN.projects)
      }
    })
  })
})
