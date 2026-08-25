import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { LoginResult, Project, User } from '@/types'

import type { ColorTheme } from '@/lib/themes'
export type { ColorTheme }

interface AuthState {
  token: string | null
  user: User | null
  projects: Project[]
  permissions: string[]
  currentProjectId: number | null
  mustChangePassword: boolean
  /** projectId → colorTheme mapping for per-project theme switching */
  projectThemeMap: Record<number, ColorTheme>

  setLogin: (data: LoginResult) => void
  setProjects: (projects: Project[]) => void
  setPermissions: (permissions: string[]) => void
  setCurrentProject: (id: number) => void
  completePasswordChange: () => void
  setProjectTheme: (projectId: number, theme: ColorTheme) => void
  logout: () => void
  hasPerm: (code: string) => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      projects: [],
      permissions: [],
      currentProjectId: null,
      mustChangePassword: false,
      projectThemeMap: {},

      setLogin: (data) =>
        set({
          token: data.access_token,
          user: data.user,
          projects: data.projects,
          permissions: data.permissions,
          currentProjectId: data.projects[0]?.id ?? null,
          mustChangePassword: Boolean(
            (data as LoginResult & { must_change_password?: boolean }).must_change_password,
          ),
        }),
      setProjects: (projects) =>
        set((state) => ({
          projects,
          currentProjectId: projects.some((project) => project.id === state.currentProjectId)
            ? state.currentProjectId
            : (projects[0]?.id ?? null),
        })),
      setPermissions: (permissions) => set({ permissions }),
      setCurrentProject: (id) =>
        set((state) => state.projects.some((project) => project.id === id)
          ? { currentProjectId: id }
          : state),
      completePasswordChange: () => set({ mustChangePassword: false }),
      setProjectTheme: (projectId, theme) =>
        set((s) => ({ projectThemeMap: { ...s.projectThemeMap, [projectId]: theme } })),
      logout: () =>
        set({
          token: null,
          user: null,
          projects: [],
          permissions: [],
          currentProjectId: null,
          mustChangePassword: false,
          projectThemeMap: {},
        }),
      hasPerm: (code) => {
        const perms = get().permissions
        return perms.includes('*') || perms.includes(code)
      },
    }),
    { name: 'test-platform-auth',
      // P1-1: token 不再持久化到 localStorage（防 XSS 窃取），鉴权由 httpOnly cookie 承载。
      // token 仅保留在内存中，供过渡期 Authorization 头回退使用；刷新后为 null，由 cookie 鉴权。
      partialize: (s) => ({
        user: s.user,
        projects: s.projects,
        permissions: s.permissions,
        currentProjectId: s.currentProjectId,
        mustChangePassword: s.mustChangePassword,
        projectThemeMap: s.projectThemeMap,
      }),
    },
  ),
)
