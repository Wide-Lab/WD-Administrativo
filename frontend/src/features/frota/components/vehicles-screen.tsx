'use client'

import { Plus } from 'lucide-react'
import { useState } from 'react'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Select } from '#/components/ui/select'
import { Skeleton } from '#/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import { Can } from '#/features/context/components/can'
import { useOrgId } from '#/features/context/use-org-context'
import { VehicleFormDialog } from '#/features/frota/components/vehicle-form-dialog'
import {
  formatOdometer,
  VEHICLE_STATUS_LABEL,
  vehicleStatusVariant,
} from '#/features/frota/lib/labels'
import { FrotaPermissions } from '#/features/frota/permissions'
import type { VehicleStatus } from '#/features/frota/types'
import { useSetVehicleStatus, useVehicles } from '#/features/frota/use-frota'

/**
 * Veículos — lista com filtro de status, cadastro/edição e **"Desativar"** em vez de apagar.
 *
 * O filtro é estado local, e não URL: diferente da lista de viagens, aqui não há caso de
 * compartilhar "os veículos em manutenção" com alguém, nem atalho que precise montar a URL. A
 * spec põe os filtros na URL para as **viagens**, que é onde o 409 de sobreposição precisa deles.
 */
export function VehiclesScreen() {
  const orgId = useOrgId()
  const [status, setStatus] = useState<VehicleStatus | ''>('')
  const vehicles = useVehicles(orgId, status || undefined)
  const setVehicleStatus = useSetVehicleStatus(orgId)

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Veículos</h1>
          <p className="text-sm text-muted">Os carros da frota desta Empresa.</p>
        </div>

        <Can permission={FrotaPermissions.VEHICLES_WRITE}>
          <VehicleFormDialog
            trigger={
              <Button>
                <Plus aria-hidden />
                Cadastrar veículo
              </Button>
            }
          />
        </Can>
      </header>

      <div className="flex items-center gap-3">
        <label htmlFor="filtro-status" className="text-sm text-muted">
          Situação
        </label>
        <Select
          id="filtro-status"
          className="w-48"
          value={status}
          onChange={(event) => setStatus(event.target.value as VehicleStatus | '')}
        >
          <option value="">Todas</option>
          {Object.entries(VEHICLE_STATUS_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </div>

      {vehicles.isPending ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : vehicles.isError ? (
        <p
          role="alert"
          className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-text"
        >
          Não foi possível carregar os veículos. Tente de novo em instantes.
        </p>
      ) : vehicles.data.items.length === 0 ? (
        <p className="rounded-lg border border-line bg-surface px-4 py-8 text-center text-sm text-muted">
          {status === '' ? 'Nenhum veículo cadastrado ainda.' : 'Nenhum veículo nessa situação.'}
        </p>
      ) : (
        <div className="rounded-lg border border-line bg-surface">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Placa</TableHead>
                <TableHead>Marca e modelo</TableHead>
                <TableHead>Ano</TableHead>
                <TableHead className="text-right">Hodômetro inicial</TableHead>
                <TableHead>Situação</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {vehicles.data.items.map((vehicle) => (
                <TableRow key={vehicle.id}>
                  <TableCell className="font-medium">{vehicle.plate}</TableCell>
                  <TableCell>
                    {vehicle.brand} {vehicle.model}
                  </TableCell>
                  <TableCell>{vehicle.model_year ?? '—'}</TableCell>
                  <TableCell className="text-right font-mono text-xs">
                    {formatOdometer(vehicle.initial_odometer)}
                  </TableCell>
                  <TableCell>
                    <Badge variant={vehicleStatusVariant(vehicle.status)}>
                      {VEHICLE_STATUS_LABEL[vehicle.status]}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Can permission={FrotaPermissions.VEHICLES_WRITE}>
                      <div className="flex justify-end gap-2">
                        <VehicleFormDialog
                          vehicle={vehicle}
                          trigger={
                            <Button variant="ghost" size="sm">
                              Editar
                            </Button>
                          }
                        />
                        {/* Nunca uma lixeira: não existe `DELETE`, e o carro vendido continua nos
                            relatórios do período em que rodou. */}
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={setVehicleStatus.isPending}
                          onClick={() =>
                            setVehicleStatus.mutate({
                              vehicleId: vehicle.id,
                              status: vehicle.status === 'inactive' ? 'active' : 'inactive',
                            })
                          }
                        >
                          {vehicle.status === 'inactive' ? 'Reativar' : 'Desativar'}
                        </Button>
                      </div>
                    </Can>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
