/**
 * Traduz as falhas da frota pro campo certo do formulário.
 *
 * **Por que isto existe:** o backend distingue casos que a tela não pode achatar em "erro ao
 * salvar" — período sobreposto, data futura, veículo inativo, placa duplicada. Cada um tem uma
 * saída diferente pro usuário, e um toast genérico esconde qual.
 *
 * **Por que ele casa em texto, e o que isso custa.** O `core` do backend responde
 * `{code, message}`, mas o `code` é do *tipo* do erro (`conflict`, `validation_error`), não do
 * caso: todos os cinco 409 de `vehicle_usages` chegam como `conflict`. O único sinal que separa
 * "período sobreposto" de "hodômetro invertido" é a frase, que mora em `_USAGE_CONFLICTS` no
 * repositório. Casar em trecho de frase é frágil e eu sei disso — mas a alternativa era exibir a
 * mesma mensagem pros cinco, e o critério 2 da spec cobra o contrário.
 *
 * A fragilidade fica **contida e testada**: os trechos estão todos neste arquivo, e o teste
 * ao lado usa as frases reais do backend, copiadas de `frota/adapters/db/repository.py` e
 * `application/use_cases/create_usage.py`. Backend que reescrever uma frase quebra um teste daqui
 * — que é exatamente onde eu quero descobrir. O caminho definitivo é um `code` por constraint, e
 * é spec de backend.
 */

import { ApiError } from '#/lib/api'

/** Onde a mensagem pode pousar no formulário de viagem. `null` = o formulário inteiro. */
export type UsageErrorField = 'vehicleId' | 'driverId' | 'startedAt' | 'endedAt' | 'endOdometer'

export type FrotaErrorTranslation<FieldT extends string> = {
  /** O campo que recebe a mensagem, ou `null` quando o erro não é de um campo só. */
  field: FieldT | null
  message: string
}

/** O que serve a qualquer chamada da frota. Mesma escada do `onboarding-error.ts`: a mensagem do
 *  backend por último, porque ela é melhor que um chute meu. */
function fallbackMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return 'Não foi possível conectar. Verifique sua conexão e tente de novo.'
  }

  if (error.status >= 500) return 'O servidor não respondeu. Tente de novo em instantes.'

  return error.message
}

function messageOf(error: unknown): string {
  return error instanceof ApiError ? error.message : ''
}

/** O 409 de período sobreposto — **a mensagem mais importante desta spec**.
 *
 *  É o único erro que fala de um dado que não está na tela: a viagem que colide é de outra pessoa,
 *  possivelmente de outro dia. Por isso é o único que a tela **reescreve** em vez de repassar — o
 *  backend não sabe qual veículo o usuário escolheu nem que período ele digitou (ele tem os ids;
 *  a tela tem os rótulos), e um "já existe uma viagem nesse período" sem nomes deixa a pessoa sem
 *  ter o que procurar. */
export function isOverlapConflict(error: unknown): boolean {
  return error instanceof ApiError && error.status === 409 && /sobrep/i.test(error.message)
}

/** A placa duplicada (409) — vai pro campo placa, nunca pro topo do formulário. */
export function isPlateConflict(error: unknown): boolean {
  return error instanceof ApiError && error.status === 409 && /placa/i.test(error.message)
}

/** A pessoa já é condutora nesta Empresa (409 do `uq_drivers_organization_user`). */
export function isDriverUserConflict(error: unknown): boolean {
  return (
    error instanceof ApiError && error.status === 409 && /já está cadastrada/i.test(error.message)
  )
}

/** Quem só tem `write_own` não é condutor cadastrado (422).
 *
 *  É o outro lado do critério 5: lá a lista vem vazia porque não há `drivers.user_id` apontando
 *  pra pessoa; aqui o lançamento é recusado pelo mesmo motivo. As duas telas dizem a mesma coisa,
 *  e as duas dizem a quem pedir — senão a pessoa procura permissão que ela já tem. */
export function isNotADriver(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    error.status === 422 &&
    /não está cadastrado como condutor/i.test(error.message)
  )
}

/**
 * O erro de lançar ou corrigir uma viagem, já endereçado a um campo.
 *
 * A ordem das checagens é a da especificidade, e não é arbitrária: "O veículo ABC1D23 está
 * 'inactive'…" contém tanto `veículo` quanto nada mais, mas "Veículo não encontrado nesta
 * Empresa." também casa `veículo` — as duas vão pro mesmo campo, então a ambiguidade não custa.
 * Já a sobreposição precisa vir **antes** de qualquer coisa, porque é a única que não é de campo.
 */
export function translateUsageError(
  error: unknown,
  context: { vehicleLabel?: string; startedAt?: string; endedAt?: string } = {},
): FrotaErrorTranslation<UsageErrorField> {
  if (isOverlapConflict(error)) {
    return { field: null, message: overlapMessage(context) }
  }

  const message = messageOf(error)

  if (error instanceof ApiError && error.status === 403) {
    // Pela tela isto não acontece: quem só tem `write_own` não vê o campo de condutor. Se
    // aparecer, é bug — e aparece inteiro, em vez de virar "erro ao salvar".
    return { field: null, message: error.message }
  }

  if (isNotADriver(error)) return { field: null, message }

  // O par indivisível e a ordem dos instantes são do banco (`ck_vehicle_usages_*`). O schema já
  // impede o primeiro; o segundo chega aqui e cai no campo de chegada, que é o editável.
  if (/hora de volta/i.test(message)) return { field: 'endedAt', message }
  if (/hodômetro/i.test(message)) return { field: 'endOdometer', message }
  if (/futuro/i.test(message)) return { field: 'startedAt', message }
  if (/condutor/i.test(message)) return { field: 'driverId', message }
  if (/ve[íi]culo/i.test(message)) return { field: 'vehicleId', message }

  return { field: null, message: fallbackMessage(error) }
}

/** A frase do conflito de período, com o veículo e o intervalo que a pessoa tentou.
 *
 *  Separada da tradução porque é a única mensagem composta pela tela, e porque o critério 2 cobra
 *  os nomes explicitamente. Sem o rótulo do veículo (a lista ainda carregando, por exemplo) a
 *  frase degrada pra "Este veículo" e continua verdadeira. */
export function overlapMessage({
  vehicleLabel,
  startedAt,
  endedAt,
}: {
  vehicleLabel?: string
  startedAt?: string
  endedAt?: string
}): string {
  const vehicle = vehicleLabel ? `O veículo ${vehicleLabel}` : 'Este veículo'
  const period = describePeriod(startedAt, endedAt)

  return `${vehicle} já tem uma viagem registrada${period}. Duas viagens do mesmo veículo não podem se sobrepor.`
}

/** O intervalo em português, pra entrar na frase acima. Vazio quando não há o que dizer. */
function describePeriod(startedAt?: string, endedAt?: string): string {
  if (!startedAt) return ' nesse período'
  if (!endedAt) return ` a partir de ${formatMoment(startedAt)}`

  return ` entre ${formatMoment(startedAt)} e ${formatMoment(endedAt)}`
}

/** Um `datetime-local` (`2026-07-20T08:30`) em `20/07/2026 08:30`.
 *
 *  Formatação à mão, sem `Date`: a string do input não tem fuso, e passá-la por `Date` a
 *  deslocaria — ver o mesmo cuidado em `isoDatePart`. */
export function formatMoment(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(value.trim())
  if (!match) return value

  const [, year, month, day, hour, minute] = match
  return `${day}/${month}/${year} ${hour}:${minute}`
}

/** O erro do formulário de veículo. Só a placa tem campo próprio; o resto é do formulário. */
export function translateVehicleError(error: unknown): FrotaErrorTranslation<'plate'> {
  if (isPlateConflict(error)) {
    return { field: 'plate', message: messageOf(error) }
  }

  return { field: null, message: fallbackMessage(error) }
}

/** O erro do formulário de condutor. O 409 do vínculo duplicado vai pro select de pessoa. */
export function translateDriverError(error: unknown): FrotaErrorTranslation<'userId'> {
  if (isDriverUserConflict(error)) {
    return { field: 'userId', message: messageOf(error) }
  }

  return { field: null, message: fallbackMessage(error) }
}

/** O erro de encerrar uma viagem (`POST /usos/{id}/encerrar`).
 *
 *  O 409 daqui **não** é sobreposição: é "esta viagem já foi encerrada", que acontece quando duas
 *  pessoas encerram a mesma viagem (o `UPDATE ... WHERE ended_at IS NULL` deixa uma ganhar). A
 *  saída é recarregar a lista, e a mensagem do backend já diz isso. */
export function translateCloseUsageError(
  error: unknown,
): FrotaErrorTranslation<'endedAt' | 'endOdometer'> {
  const message = messageOf(error)

  if (error instanceof ApiError && error.status === 409 && /já foi encerrada/i.test(message)) {
    return { field: null, message }
  }

  if (/hora de volta/i.test(message)) return { field: 'endedAt', message }
  if (/hodômetro/i.test(message)) return { field: 'endOdometer', message }
  if (isOverlapConflict(error)) return { field: 'endedAt', message: overlapMessage({}) }

  return { field: null, message: fallbackMessage(error) }
}
