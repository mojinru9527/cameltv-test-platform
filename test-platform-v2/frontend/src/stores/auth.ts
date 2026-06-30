import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { LoginResult, Project, User } from '@/types'

export type ColorTheme = "blue" | "green" | "purple" | "orange" | "rose" | "cyan" | "amber" | "indigo"

interface AuthState {
  token: string | null
  user: User | null
  projects: Project[]
  permissions: string[]
  currentProjectId: number | null
  /** projectId → colorTheme mapping for per-project theme switching */
  projectThemeMap: Record<number, ColorTheme>

  setLogin: (data: LoginResult) => void
  setProjects: (projects: Project[]) => void
  setPermissions: (permissions: string[]) => void
  setCurrentProject: (id: number) => void
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
      projectThemeMap: {},

      setLogin: (data) =>
        set({
          token: data.access_token,
          user: data.user,
          projects: data.projects,
          permissions: data.permissions,
          currentProjectId: data.projects[0]?.id ?? null,
        }),
      setProjects: (projects) => set({ projects }),
      setPermissions: (permissions) => set({ permissions }),
      setCurrentProject: (id) => set({ currentProjectId: id }),
      setProjectTheme: (projectId, theme) =>
        set((s) => ({ projectThemeMap: { ...s.projectThemeMap, [projectId]: theme } })),
      logout: () =>
        set({ token: null, user: null, projects: [], permissions: [], currentProjectId: null, projectThemeMap: {} }),
      hasPerm: (code) => {
        const perms = get().permissions
        return perms.includes('*') || perms.includes(code)
      },
    }),
    { name: 'cameltv-auth' },
  ),
)
