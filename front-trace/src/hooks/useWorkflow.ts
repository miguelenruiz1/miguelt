import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type {
  WorkflowState, WorkflowStateCreate, WorkflowStateUpdate,
  WorkflowTransition, WorkflowTransitionCreate,
  WorkflowEventType, WorkflowEventTypeCreate, WorkflowEventTypeUpdate,
} from '@/types/api'

// ─── Query keys ──────────────────────────────────────────────────────────────

const KEYS = {
  states: ['workflow-states'] as const,
  transitions: ['workflow-transitions'] as const,
  eventTypes: ['workflow-event-types'] as const,
  presets: ['workflow-presets'] as const,
}

// ─── States ──────────────────────────────────────────────────────────────────

export function useWorkflowStates() {
  return useQuery({
    queryKey: KEYS.states,
    queryFn: () => api.workflow.listStates(),
    staleTime: 30_000,
  })
}

export function useCreateWorkflowState() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WorkflowStateCreate) => api.workflow.createState(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.states }),
  })
}

export function useUpdateWorkflowState() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: WorkflowStateUpdate }) =>
      api.workflow.updateState(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.states }),
  })
}

export function useDeleteWorkflowState() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.workflow.deleteState(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.states })
      qc.invalidateQueries({ queryKey: KEYS.transitions })
    },
  })
}

export function useReorderWorkflowStates() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (stateIds: string[]) => api.workflow.reorderStates(stateIds),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.states }),
  })
}

// ─── Transitions ─────────────────────────────────────────────────────────────

export function useWorkflowTransitions() {
  return useQuery({
    queryKey: KEYS.transitions,
    queryFn: () => api.workflow.listTransitions(),
    staleTime: 30_000,
  })
}

export function useCreateWorkflowTransition() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WorkflowTransitionCreate) => api.workflow.createTransition(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.transitions }),
  })
}

export function useDeleteWorkflowTransition() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.workflow.deleteTransition(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.transitions }),
  })
}

// ─── Event Types ─────────────────────────────────────────────────────────────

export function useWorkflowEventTypes(activeOnly = true) {
  return useQuery({
    queryKey: [...KEYS.eventTypes, activeOnly],
    queryFn: () => api.workflow.listEventTypes({ active_only: activeOnly }),
    staleTime: 30_000,
  })
}

export function useCreateWorkflowEventType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WorkflowEventTypeCreate) => api.workflow.createEventType(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.eventTypes }),
  })
}

export function useUpdateWorkflowEventType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: WorkflowEventTypeUpdate }) =>
      api.workflow.updateEventType(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.eventTypes }),
  })
}

export function useDeleteWorkflowEventType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.workflow.deleteEventType(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.eventTypes }),
  })
}

// ─── Available Actions ───────────────────────────────────────────────────────

export function useAvailableActions(stateSlug: string | undefined) {
  return useQuery({
    queryKey: [...KEYS.transitions, 'actions', stateSlug],
    queryFn: () => api.workflow.getAvailableActions(stateSlug!),
    enabled: Boolean(stateSlug),
    staleTime: 30_000,
  })
}

// ─── Presets ─────────────────────────────────────────────────────────────────

export function useWorkflowPresets() {
  return useQuery({
    queryKey: KEYS.presets,
    queryFn: () => api.workflow.listPresets(),
    staleTime: 60_000,
  })
}

export function useSeedWorkflowPreset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (presetName: string) => api.workflow.seedPreset(presetName),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.states })
      qc.invalidateQueries({ queryKey: KEYS.transitions })
      qc.invalidateQueries({ queryKey: KEYS.eventTypes })
    },
  })
}
