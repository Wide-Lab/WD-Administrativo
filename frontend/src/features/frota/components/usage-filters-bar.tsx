'use client'

import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import { Select } from '#/components/ui/select'
import { useOrgContext, useOrgId } from '#/features/context/use-org-context'
import {
  EMPTY_USAGE_FILTERS,
  hasAnyUsageFilter,
  type UsageFilters,
} from '#/features/frota/lib/filters'
import { vehicleLabel } from '#/features/frota/lib/labels'
import { FrotaPermissions } from '#/features/frota/permissions'
import { useDrivers, useVehicles } from '#/features/frota/use-frota'

/**
 * Os filtros da lista de viagens.
 *
 * Não guardam estado: recebem o valor de quem leu a URL e devolvem o novo pra quem a escreve. É o
 * que faz uma lista filtrada ser compartilhável e sobreviver ao F5 — e é o que deixa o atalho do
 * 409 de sobreposição funcionar, porque ele só monta a mesma URL.
 *
 * O select de **condutor** só aparece com `frota.drivers.read`: sem a capability a pessoa vê só as
 * próprias viagens (o escopo é do backend), e um filtro de condutor ali ofereceria recortar uma
 * lista que já tem um dono só.
 *
 * Os veículos vêm **sem** filtro de status, ao contrário do formulário de lançamento: filtrar o
 * histórico por um carro que foi desativado é caso legítimo — o carro saiu da frota, as viagens
 * dele não.
 */
export function UsageFiltersBar({
  filters,
  onChange,
}: {
  filters: UsageFilters
  onChange: (filters: UsageFilters) => void
}) {
  const orgId = useOrgId()
  const { permissions } = useOrgContext()
  const canSeeDrivers = permissions.includes(FrotaPermissions.DRIVERS_READ)

  const vehicles = useVehicles(orgId)
  const drivers = useDrivers(orgId, undefined, { enabled: canSeeDrivers })

  const set = <K extends keyof UsageFilters>(key: K, value: UsageFilters[K]) =>
    onChange({ ...filters, [key]: value })

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-lg border border-line bg-surface p-4">
      <div className="min-w-48 flex-1 space-y-2">
        <Label htmlFor="filtro-veiculo">Veículo</Label>
        <Select
          id="filtro-veiculo"
          value={filters.vehicleId ?? ''}
          onChange={(event) => set('vehicleId', event.target.value || null)}
        >
          <option value="">Todos</option>
          {vehicles.data?.items.map((vehicle) => (
            <option key={vehicle.id} value={vehicle.id}>
              {vehicleLabel(vehicle)}
            </option>
          ))}
        </Select>
      </div>

      {canSeeDrivers ? (
        <div className="min-w-40 flex-1 space-y-2">
          <Label htmlFor="filtro-condutor">Condutor</Label>
          <Select
            id="filtro-condutor"
            value={filters.driverId ?? ''}
            onChange={(event) => set('driverId', event.target.value || null)}
          >
            <option value="">Todos</option>
            {drivers.data?.items.map((driver) => (
              <option key={driver.id} value={driver.id}>
                {driver.name}
              </option>
            ))}
          </Select>
        </div>
      ) : null}

      <div className="space-y-2">
        <Label htmlFor="filtro-de">De</Label>
        <Input
          id="filtro-de"
          type="date"
          value={filters.from ?? ''}
          onChange={(event) => set('from', event.target.value || null)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="filtro-ate">Até</Label>
        <Input
          id="filtro-ate"
          type="date"
          value={filters.until ?? ''}
          onChange={(event) => set('until', event.target.value || null)}
        />
      </div>

      <label className="flex h-10 items-center gap-2 text-sm text-text">
        <input
          type="checkbox"
          checked={filters.onlyOpen}
          onChange={(event) => set('onlyOpen', event.target.checked)}
          className="size-4 rounded-sm border-line accent-primary"
        />
        Só em curso
      </label>

      {hasAnyUsageFilter(filters) ? (
        <Button variant="ghost" size="sm" onClick={() => onChange(EMPTY_USAGE_FILTERS)}>
          Limpar
        </Button>
      ) : null}
    </div>
  )
}
