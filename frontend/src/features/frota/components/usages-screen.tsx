'use client'

import { Plus } from 'lucide-react'
import { useRouter, useSearchParams } from 'next/navigation'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
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
import { useOrgContext, useOrgId } from '#/features/context/use-org-context'
import { CloseUsageDialog } from '#/features/frota/components/close-usage-dialog'
import { UsageFiltersBar } from '#/features/frota/components/usage-filters-bar'
import { UsageFormDialog } from '#/features/frota/components/usage-form-dialog'
import {
  hasAnyUsageFilter,
  readUsageFilters,
  usageFiltersToQueryString,
  type UsageFilters,
} from '#/features/frota/lib/filters'
import { formatDateTime, formatDistance, formatOdometer } from '#/features/frota/lib/labels'
import { frotaPath } from '#/features/frota/module'
import { FrotaPermissions } from '#/features/frota/permissions'
import { useDrivers, useUsages, useVehicles } from '#/features/frota/use-frota'

/**
 * Viagens — a home do módulo, e **não um dashboard**.
 *
 * É a única das quatro telas que um `collaborator` enxerga com conteúdo: ele tem `vehicles.read` e
 * `usages.write_own`, e nada mais. Um dashboard com três cartões vazios seria a primeira coisa que
 * a maior persona do produto veria.
 */
export function UsagesScreen() {
  const orgId = useOrgId()
  const router = useRouter()
  const searchParams = useSearchParams()
  const { permissions } = useOrgContext()

  // Os filtros **são** a URL — não há `useState` aqui de propósito. Um estado paralelo seria uma
  // segunda verdade que diverge no botão "voltar" do navegador.
  const filters = readUsageFilters(new URLSearchParams(searchParams.toString()))

  const canReadAll = permissions.includes(FrotaPermissions.USAGES_READ)
  const canSeeDrivers = permissions.includes(FrotaPermissions.DRIVERS_READ)

  const usages = useUsages(orgId, filters)
  const vehicles = useVehicles(orgId)
  const drivers = useDrivers(orgId, undefined, { enabled: canSeeDrivers })

  function applyFilters(next: UsageFilters) {
    router.replace(`${frotaPath(orgId)}${usageFiltersToQueryString(next)}`, { scroll: false })
  }

  const plateOf = (vehicleId: string) =>
    vehicles.data?.items.find((item) => item.id === vehicleId)?.plate ?? '—'

  const driverNameOf = (driverId: string) =>
    drivers.data?.items.find((item) => item.id === driverId)?.name ?? null

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Viagens</h1>
          <p className="text-sm text-muted">
            {canReadAll
              ? 'Todas as viagens registradas nesta Empresa.'
              : 'As viagens lançadas em seu nome.'}
          </p>
        </div>

        {/* Lançar exige `write` **ou** `write_own` — as duas abrem o mesmo formulário, e o que
            muda entre elas é o campo de condutor, lá dentro. Dois `Can` porque o `Can` decide
            sobre uma capability, e aqui são alternativas. */}
        <Can
          permission={FrotaPermissions.USAGES_WRITE}
          fallback={
            <Can permission={FrotaPermissions.USAGES_WRITE_OWN}>
              <UsageFormDialog trigger={<NewUsageButton />} />
            </Can>
          }
        >
          <UsageFormDialog trigger={<NewUsageButton />} />
        </Can>
      </header>

      <UsageFiltersBar filters={filters} onChange={applyFilters} />

      {usages.isPending ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : usages.isError ? (
        <p
          role="alert"
          className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-text"
        >
          Não foi possível carregar as viagens. Tente de novo em instantes.
        </p>
      ) : usages.data.items.length === 0 ? (
        <EmptyUsages canReadAll={canReadAll} isFiltered={hasAnyUsageFilter(filters)} />
      ) : (
        <div className="rounded-lg border border-line bg-surface">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Veículo</TableHead>
                {canSeeDrivers ? <TableHead>Condutor</TableHead> : null}
                <TableHead>Saída</TableHead>
                <TableHead>Chegada</TableHead>
                <TableHead className="text-right">Hodômetro</TableHead>
                <TableHead className="text-right">Distância</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {usages.data.items.map((usage) => (
                <TableRow key={usage.id}>
                  <TableCell className="font-medium">{plateOf(usage.vehicle_id)}</TableCell>
                  {canSeeDrivers ? (
                    <TableCell>{driverNameOf(usage.driver_id) ?? '—'}</TableCell>
                  ) : null}
                  <TableCell className="whitespace-nowrap">
                    {formatDateTime(usage.started_at)}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {usage.ended_at ? (
                      formatDateTime(usage.ended_at)
                    ) : (
                      <Badge variant="warning">Em curso</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs whitespace-nowrap">
                    {formatOdometer(usage.start_odometer)}
                    {usage.end_odometer === null ? '' : ` → ${formatOdometer(usage.end_odometer)}`}
                  </TableCell>
                  {/* `distance` vem do backend e é `null` na viagem aberta. **Nunca** calculada
                      aqui, mesmo sendo trivial: a segunda conta é a que diverge no dia em que a
                      regra ganhar um caso. */}
                  <TableCell className="text-right font-medium whitespace-nowrap">
                    {formatDistance(usage.distance)}
                  </TableCell>
                  <TableCell className="text-right">
                    {usage.ended_at === null ? <CloseUsageDialog usage={usage} /> : null}
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

function NewUsageButton() {
  return (
    <Button>
      <Plus aria-hidden />
      Lançar viagem
    </Button>
  )
}

/**
 * O vazio da lista de viagens — e ele **não é um só**.
 *
 * `GET /usos` já vem escopado pelo backend: quem não tem `frota.usages.read` recebe apenas as
 * viagens do próprio condutor, e **lista vazia se não houver `drivers.user_id` apontando pra
 * ele**. Vazio-por-escopo não é vazio-por-falta-de-dado, e dizer "nenhuma viagem registrada" pra
 * quem está no primeiro caso faria a pessoa concluir que o sistema perdeu as viagens dela.
 *
 * Por isso o texto de quem não tem `usages.read` fala do vínculo que pode estar faltando, e diz a
 * quem pedir. É o critério 5 da spec.
 */
function EmptyUsages({ canReadAll, isFiltered }: { canReadAll: boolean; isFiltered: boolean }) {
  if (isFiltered) {
    return (
      <p className="rounded-lg border border-line bg-surface px-4 py-8 text-center text-sm text-muted">
        Nenhuma viagem no período ou nos filtros escolhidos.
      </p>
    )
  }

  if (canReadAll) {
    return (
      <p className="rounded-lg border border-line bg-surface px-4 py-8 text-center text-sm text-muted">
        Nenhuma viagem registrada ainda. Lance a primeira para começar o histórico da frota.
      </p>
    )
  }

  return (
    <div className="space-y-2 rounded-lg border border-line bg-surface px-4 py-8 text-center">
      <p className="text-sm text-text">Nenhuma viagem aparece aqui para você.</p>
      <p className="mx-auto max-w-prose text-sm text-muted">
        Você vê apenas as viagens em que é o condutor. Se já dirigiu e nada aparece, é possível que
        seu cadastro de condutor ainda não tenha sido vinculado ao seu acesso — peça ao gestor da
        frota para fazer o vínculo.
      </p>
    </div>
  )
}
