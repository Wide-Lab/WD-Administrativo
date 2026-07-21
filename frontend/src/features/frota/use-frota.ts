'use client'

/**
 * As queries e mutations da frota.
 *
 * Um arquivo só pros quatro recursos porque eles se invalidam em cruz: encerrar uma viagem muda a
 * lista **e** o relatório; desativar um veículo muda a lista de veículos **e** o que o formulário
 * de viagem oferece. Espalhá-los por quatro arquivos faria cada `invalidateQueries` importar o
 * vizinho, e a chave de cache é justamente o que precisa ser lido de uma vez.
 *
 * Toda chave começa por `['frota', orgId]`: trocar de organização é navegar pra outro `orgId`, e
 * sem o `orgId` na chave a lista da Empresa anterior apareceria por um instante na nova.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  closeUsage,
  createDriver,
  createUsage,
  createVehicle,
  getMileageReport,
  listDrivers,
  listMembers,
  listUsages,
  listVehicles,
  setDriverStatus,
  setVehicleStatus,
  updateDriver,
  updateVehicle,
} from '#/features/frota/api'
import type { UsageFilters } from '#/features/frota/lib/filters'
import type {
  CloseUsageFormValues,
  DriverFormValues,
  DriverStatus,
  MileageGroupBy,
  UsageFormValues,
  VehicleFormValues,
  VehicleStatus,
} from '#/features/frota/types'

const root = (orgId: string) => ['frota', orgId] as const

export const vehiclesQueryKey = (orgId: string, status?: VehicleStatus) =>
  [...root(orgId), 'veiculos', status ?? 'todos'] as const
export const driversQueryKey = (orgId: string, status?: DriverStatus) =>
  [...root(orgId), 'condutores', status ?? 'todos'] as const
export const usagesQueryKey = (orgId: string, filters: UsageFilters) =>
  [...root(orgId), 'usos', filters] as const
export const mileageQueryKey = (orgId: string, from: string, until: string, by: MileageGroupBy) =>
  [...root(orgId), 'quilometragem', from, until, by] as const
export const membersQueryKey = (orgId: string) => [...root(orgId), 'membros'] as const

// ---------------------------------------------------------------------------------------------
// Leitura
// ---------------------------------------------------------------------------------------------

export function useVehicles(orgId: string, status?: VehicleStatus) {
  return useQuery({
    queryKey: vehiclesQueryKey(orgId, status),
    queryFn: () => listVehicles(orgId, { status, pageSize: 100 }),
    // 403 é resposta, não falha de rede: não melhora com nova tentativa.
    retry: false,
  })
}

export function useDrivers(
  orgId: string,
  status?: DriverStatus,
  options: { enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: driversQueryKey(orgId, status),
    queryFn: () => listDrivers(orgId, { status, pageSize: 100 }),
    // `enabled` é como o `frota.drivers.read` entra: sem a capability a tela não pergunta, em vez
    // de perguntar e engolir o 403.
    enabled: options.enabled ?? true,
    retry: false,
  })
}

export function useUsages(orgId: string, filters: UsageFilters) {
  return useQuery({
    queryKey: usagesQueryKey(orgId, filters),
    queryFn: () => listUsages(orgId, filters, { pageSize: 50 }),
    retry: false,
  })
}

export function useMileageReport(
  orgId: string,
  params: { from: string; until: string; groupBy: MileageGroupBy },
) {
  return useQuery({
    queryKey: mileageQueryKey(orgId, params.from, params.until, params.groupBy),
    queryFn: () => getMileageReport(orgId, params),
    retry: false,
  })
}

/** Os membros, pro select de vínculo do condutor. Opcional por desenho — ver `listMembers`. */
export function useMembers(orgId: string, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: membersQueryKey(orgId),
    queryFn: () => listMembers(orgId),
    enabled: options.enabled ?? true,
    retry: false,
  })
}

// ---------------------------------------------------------------------------------------------
// Escrita
// ---------------------------------------------------------------------------------------------

/** Invalida tudo da organização.
 *
 *  Grosso de propósito: as quatro listas se influenciam (um veículo desativado some do select de
 *  lançamento, uma viagem encerrada muda o relatório), e a alternativa — enumerar quais chaves
 *  cada mutation afeta — é a lista que envelhece errado no primeiro campo novo. São quatro
 *  requisições no pior caso, num módulo de dezenas de linhas. */
function useInvalidateFrota(orgId: string) {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: root(orgId) })
}

export function useCreateUsage(orgId: string) {
  const invalidate = useInvalidateFrota(orgId)

  return useMutation({
    mutationFn: (values: UsageFormValues) => createUsage(orgId, values),
    onSuccess: invalidate,
  })
}

export function useCloseUsage(orgId: string) {
  const invalidate = useInvalidateFrota(orgId)

  return useMutation({
    mutationFn: ({ usageId, values }: { usageId: string; values: CloseUsageFormValues }) =>
      closeUsage(orgId, usageId, values),
    onSuccess: invalidate,
  })
}

export function useSaveVehicle(orgId: string) {
  const invalidate = useInvalidateFrota(orgId)

  return useMutation({
    mutationFn: ({ vehicleId, values }: { vehicleId?: string; values: VehicleFormValues }) =>
      vehicleId === undefined
        ? createVehicle(orgId, values)
        : updateVehicle(orgId, vehicleId, values),
    onSuccess: invalidate,
  })
}

export function useSetVehicleStatus(orgId: string) {
  const invalidate = useInvalidateFrota(orgId)

  return useMutation({
    mutationFn: ({ vehicleId, status }: { vehicleId: string; status: VehicleStatus }) =>
      setVehicleStatus(orgId, vehicleId, status),
    onSuccess: invalidate,
  })
}

export function useSaveDriver(orgId: string) {
  const invalidate = useInvalidateFrota(orgId)

  return useMutation({
    mutationFn: ({ driverId, values }: { driverId?: string; values: DriverFormValues }) =>
      driverId === undefined ? createDriver(orgId, values) : updateDriver(orgId, driverId, values),
    onSuccess: invalidate,
  })
}

export function useSetDriverStatus(orgId: string) {
  const invalidate = useInvalidateFrota(orgId)

  return useMutation({
    mutationFn: ({ driverId, status }: { driverId: string; status: DriverStatus }) =>
      setDriverStatus(orgId, driverId, status),
    onSuccess: invalidate,
  })
}
