import { create } from 'zustand'

interface PlanLimitState {
  show: boolean
  resource: string
  current: number
  limit: number
  message: string
  open: (data: { resource: string; current: number; limit: number; message: string }) => void
  close: () => void
}

export const usePlanLimitStore = create<PlanLimitState>((set) => ({
  show: false,
  resource: '',
  current: 0,
  limit: 0,
  message: '',
  open: (data) => set({ show: true, ...data }),
  close: () => set({ show: false, resource: '', current: 0, limit: 0, message: '' }),
}))
