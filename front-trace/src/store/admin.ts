import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AdminStore {
  adminKey: string
  setAdminKey: (key: string) => void
  clearAdminKey: () => void
}

export const useAdminStore = create<AdminStore>()(
  persist(
    (set) => ({
      adminKey: '',
      setAdminKey: (key) => set({ adminKey: key }),
      clearAdminKey: () => set({ adminKey: '' }),
    }),
    { name: 'trace-admin-key' },
  ),
)
