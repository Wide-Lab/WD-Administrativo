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
import { DriverFormDialog } from '#/features/frota/components/driver-form-dialog'
import { DRIVER_STATUS_LABEL, formatDate } from '#/features/frota/lib/labels'
import { FrotaPermissions } from '#/features/frota/permissions'
import type { DriverStatus } from '#/features/frota/types'
import { useDrivers, useSetDriverStatus } from '#/features/frota/use-frota'

/**
 * Condutores — mesma forma da tela de veículos, e a mesma ausência de lixeira.
 *
 * `license_expires_at` é **dado e só dado**: a tela mostra a data e **não** pinta vencimento.
 * Alerta de CNH está fora de escopo na `backend/10`, e uma tarja vermelha aqui seria meia
 * implementação de compliance — a que faz a pessoa confiar num aviso que ninguém garantiu.
 */
export function DriversScreen() {
  const orgId = useOrgId()
  const [status, setStatus] = useState<DriverStatus | ''>('')
  const drivers = useDrivers(orgId, status || undefined)
  const setDriverStatus = useSetDriverStatus(orgId)

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Condutores</h1>
          <p className="text-sm text-muted">
            Quem dirige os carros desta Empresa — com ou sem acesso ao sistema.
          </p>
        </div>

        <Can permission={FrotaPermissions.DRIVERS_WRITE}>
          <DriverFormDialog
            trigger={
              <Button>
                <Plus aria-hidden />
                Cadastrar condutor
              </Button>
            }
          />
        </Can>
      </header>

      <div className="flex items-center gap-3">
        <label htmlFor="filtro-condutor-status" className="text-sm text-muted">
          Situação
        </label>
        <Select
          id="filtro-condutor-status"
          className="w-48"
          value={status}
          onChange={(event) => setStatus(event.target.value as DriverStatus | '')}
        >
          <option value="">Todas</option>
          {Object.entries(DRIVER_STATUS_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </div>

      {drivers.isPending ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : drivers.isError ? (
        <p
          role="alert"
          className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-text"
        >
          Não foi possível carregar os condutores. Tente de novo em instantes.
        </p>
      ) : drivers.data.items.length === 0 ? (
        <p className="rounded-lg border border-line bg-surface px-4 py-8 text-center text-sm text-muted">
          {status === '' ? 'Nenhum condutor cadastrado ainda.' : 'Nenhum condutor nessa situação.'}
        </p>
      ) : (
        <div className="rounded-lg border border-line bg-surface">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>CNH</TableHead>
                <TableHead>Categoria</TableHead>
                <TableHead>Validade</TableHead>
                <TableHead>Acesso</TableHead>
                <TableHead>Situação</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {drivers.data.items.map((driver) => (
                <TableRow key={driver.id}>
                  <TableCell className="font-medium">{driver.name}</TableCell>
                  <TableCell className="font-mono text-xs">
                    {driver.license_number ?? '—'}
                  </TableCell>
                  <TableCell>{driver.license_category ?? '—'}</TableCell>
                  {/* Data crua, sem cor: alerta de CNH está fora de escopo. */}
                  <TableCell className="whitespace-nowrap">
                    {driver.license_expires_at ? formatDate(driver.license_expires_at) : '—'}
                  </TableCell>
                  <TableCell>
                    {driver.user_id ? (
                      <Badge variant="primary">Vinculado</Badge>
                    ) : (
                      <Badge variant="muted">Sem vínculo</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={driver.status === 'active' ? 'success' : 'muted'}>
                      {DRIVER_STATUS_LABEL[driver.status]}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Can permission={FrotaPermissions.DRIVERS_WRITE}>
                      <div className="flex justify-end gap-2">
                        <DriverFormDialog
                          driver={driver}
                          trigger={
                            <Button variant="ghost" size="sm">
                              Editar
                            </Button>
                          }
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={setDriverStatus.isPending}
                          onClick={() =>
                            setDriverStatus.mutate({
                              driverId: driver.id,
                              status: driver.status === 'inactive' ? 'active' : 'inactive',
                            })
                          }
                        >
                          {driver.status === 'inactive' ? 'Reativar' : 'Desativar'}
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
