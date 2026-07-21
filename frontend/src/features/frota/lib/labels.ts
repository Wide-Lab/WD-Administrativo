/** Rótulos e formatação da frota — o vocabulário do módulo em português.
 *
 *  Mesma ideia do `features/context/lib/labels.ts`: os valores de enum do backend seguem em
 *  inglês (é coluna de banco), e a tela nunca os mostra crus. */

import type { DriverStatus, VehicleStatus } from '#/features/frota/types'

export const VEHICLE_STATUS_LABEL: Record<VehicleStatus, string> = {
  active: 'Ativo',
  maintenance: 'Em manutenção',
  inactive: 'Inativo',
}

export const DRIVER_STATUS_LABEL: Record<DriverStatus, string> = {
  active: 'Ativo',
  inactive: 'Inativo',
}

/** A cor do status. `maintenance` é `warning` e não `danger`: o carro volta — e um vermelho aqui
 *  o faria parecer problema, quando é rotina. */
export function vehicleStatusVariant(status: VehicleStatus): 'success' | 'warning' | 'muted' {
  if (status === 'active') return 'success'
  if (status === 'maintenance') return 'warning'
  return 'muted'
}

/** Um instante ISO do backend em `20/07/2026 08:30`.
 *
 *  `Date` aqui é correto — diferente do `formatMoment` do `frota-error.ts`: o que vem do backend
 *  **tem** fuso (o Pydantic serializa com offset), então converter pro fuso de quem lê é o
 *  comportamento certo. É a string do `<input datetime-local>`, sem fuso, que não pode passar
 *  por `Date`. */
export function formatDateTime(iso: string): string {
  const moment = new Date(iso)
  if (Number.isNaN(moment.getTime())) return iso

  return moment.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Uma data `YYYY-MM-DD` em `20/07/2026`, sem passar por `Date`.
 *
 *  `license_expires_at` é `date` puro no backend, e `new Date('2026-07-20')` é interpretado como
 *  **UTC** meia-noite — que em fuso negativo volta um dia. O corte de string não erra. */
export function formatDate(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  if (!match) return value

  const [, year, month, day] = match
  return `${day}/${month}/${year}`
}

/** Os quilômetros de uma viagem, ou "Em curso" quando ela ainda está aberta.
 *
 *  **`null` nunca vira "0 km"** — "não sei" e "não rodou" não podem virar o mesmo número. É a
 *  mesma regra que faz o relatório contar viagem aberta à parte, e ela vale na coluna também. */
export function formatDistance(distance: number | null): string {
  if (distance === null) return 'Em curso'
  return `${distance.toLocaleString('pt-BR')} km`
}

export function formatOdometer(value: number): string {
  return `${value.toLocaleString('pt-BR')} km`
}

/** Um veículo como a tela o chama: placa e o modelo entre parênteses. */
export function vehicleLabel(vehicle: { plate: string; brand: string; model: string }): string {
  return `${vehicle.plate} — ${vehicle.brand} ${vehicle.model}`
}

/** O valor inicial de um `<input type="datetime-local">`: o agora, no fuso de quem digita.
 *
 *  **Só valor inicial, e editável** — retroativo é o caso normal da frota, e a tela não pode
 *  sugerir o contrário. É por isso que não existe botão "usar horário atual" em destaque: ele
 *  transformaria o caso raro no caminho fácil.
 *
 *  `toISOString()` não serve: ele devolve UTC, e o campo pediria a hora errada pra qualquer um
 *  fora de Greenwich. */
export function nowForInput(now: Date = new Date()): string {
  const pad = (value: number) => String(value).padStart(2, '0')

  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`
}

/** O primeiro e o último dia do mês corrente, em `YYYY-MM-DD` — o período que o relatório abre. */
export function currentMonthRange(now: Date = new Date()): { from: string; until: string } {
  const pad = (value: number) => String(value).padStart(2, '0')
  const year = now.getFullYear()
  const month = now.getMonth()
  const lastDay = new Date(year, month + 1, 0).getDate()

  return {
    from: `${year}-${pad(month + 1)}-01`,
    until: `${year}-${pad(month + 1)}-${pad(lastDay)}`,
  }
}
