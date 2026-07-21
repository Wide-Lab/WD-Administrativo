'use client'

import { useRouter, useSearchParams } from 'next/navigation'

import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
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
import { useOrgId } from '#/features/context/use-org-context'
import { readMileageParams, mileageParamsToQueryString } from '#/features/frota/lib/mileage-params'
import { frotaPath } from '#/features/frota/module'
import type { MileageGroupBy } from '#/features/frota/types'
import { useMileageReport } from '#/features/frota/use-frota'

/**
 * Quilometragem — quantos quilômetros cada veículo (ou condutor) andou no período.
 *
 * `de` e `ate` são **obrigatórios na rota**, então não existe "relatório de tudo": a tela abre no
 * **mês corrente** e os dois parâmetros vão pra URL, como os filtros das viagens.
 *
 * **`open_usages` aparece sempre, mesmo zero.** É a nota de rodapé que explica por que o total não
 * bate com o que a pessoa esperava: viagem aberta não entra como zero km, entra como contagem à
 * parte. Escondê-la quando é zero faria a coluna sumir justamente quando ela vira notícia.
 */
export function MileageScreen() {
  const orgId = useOrgId()
  const router = useRouter()
  const searchParams = useSearchParams()

  const params = readMileageParams(new URLSearchParams(searchParams.toString()))
  const report = useMileageReport(orgId, params)

  function apply(next: Partial<typeof params>) {
    const merged = { ...params, ...next }
    router.replace(`${frotaPath(orgId, '/relatorios')}${mileageParamsToQueryString(merged)}`, {
      scroll: false,
    })
  }

  const totalKm = report.data?.groups.reduce((sum, group) => sum + group.total_km, 0) ?? 0
  const totalOpen = report.data?.groups.reduce((sum, group) => sum + group.open_usages, 0) ?? 0

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight">Quilometragem</h1>
        <p className="text-sm text-muted">
          Soma dos quilômetros das viagens <strong>encerradas</strong> no período.
        </p>
      </header>

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-line bg-surface p-4">
        <div className="space-y-2">
          <Label htmlFor="relatorio-de">De</Label>
          <Input
            id="relatorio-de"
            type="date"
            value={params.from}
            onChange={(event) => apply({ from: event.target.value })}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="relatorio-ate">Até</Label>
          <Input
            id="relatorio-ate"
            type="date"
            value={params.until}
            onChange={(event) => apply({ until: event.target.value })}
          />
        </div>

        <div className="min-w-44 space-y-2">
          <Label htmlFor="relatorio-agrupar">Agrupar por</Label>
          <Select
            id="relatorio-agrupar"
            value={params.groupBy}
            onChange={(event) => apply({ groupBy: event.target.value as MileageGroupBy })}
          >
            <option value="veiculo">Veículo</option>
            <option value="condutor">Condutor</option>
          </Select>
        </div>
      </div>

      {report.isPending ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : report.isError ? (
        <p
          role="alert"
          className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-text"
        >
          Não foi possível carregar o relatório. Confira o período e tente de novo.
        </p>
      ) : report.data.groups.length === 0 ? (
        <p className="rounded-lg border border-line bg-surface px-4 py-8 text-center text-sm text-muted">
          Nenhuma viagem no período escolhido.
        </p>
      ) : (
        <div className="rounded-lg border border-line bg-surface">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{params.groupBy === 'veiculo' ? 'Veículo' : 'Condutor'}</TableHead>
                <TableHead className="text-right">Quilometragem</TableHead>
                <TableHead className="text-right">Viagens encerradas</TableHead>
                <TableHead className="text-right">Em curso</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {report.data.groups.map((group) => (
                <TableRow key={group.id}>
                  <TableCell className="font-medium">{group.label || '—'}</TableCell>
                  <TableCell className="text-right font-medium">
                    {group.total_km.toLocaleString('pt-BR')} km
                  </TableCell>
                  <TableCell className="text-right">{group.closed_usages}</TableCell>
                  {/* Sempre visível, mesmo zero — ver o docstring da tela. */}
                  <TableCell className="text-right">
                    {group.open_usages > 0 ? (
                      <span className="text-warning">{group.open_usages}</span>
                    ) : (
                      <span className="text-muted">0</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {report.data && report.data.groups.length > 0 ? (
        <p className="text-sm text-muted">
          Total do período:{' '}
          <strong className="text-text">{totalKm.toLocaleString('pt-BR')} km</strong>
          {totalOpen > 0 ? (
            <>
              {' '}
              — e {totalOpen} {totalOpen === 1 ? 'viagem ainda em curso' : 'viagens ainda em curso'}
              , que não {totalOpen === 1 ? 'entra' : 'entram'} nesse total porque ainda não{' '}
              {totalOpen === 1 ? 'tem' : 'têm'} hodômetro de chegada.
            </>
          ) : null}
        </p>
      ) : null}
    </div>
  )
}
