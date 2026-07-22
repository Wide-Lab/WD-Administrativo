/**
 * Os filtros da lista de viagens, e a ponte entre a URL e a query do backend.
 *
 * **Filtro vive na URL, não em estado de componente**, com os mesmos nomes que o backend usa
 * (`veiculo`, `condutor`, `de`, `ate`, `abertos`). Uma lista filtrada é compartilhável e sobrevive
 * ao F5 — a mesma razão pela qual a organização ativa é o `orgId` do path e não uma store. É
 * também o que faz o atalho do 409 de sobreposição existir: a mensagem de conflito monta uma URL,
 * e a URL é a tela.
 *
 * Tudo aqui é função pura, e é a terceira coisa que a spec manda testar nesta entrega.
 */

import { toInstant } from '#/features/frota/lib/instants'

/** Os filtros como a tela os pensa. `null` é "sem filtro" — nunca `''`, que num `URLSearchParams`
 *  vira um parâmetro presente e vazio, e o backend o leria como valor. */
export type UsageFilters = {
  vehicleId: string | null
  driverId: string | null
  /** `YYYY-MM-DD`, o que um `<input type="date">` devolve. */
  from: string | null
  until: string | null
  onlyOpen: boolean
}

export const EMPTY_USAGE_FILTERS: UsageFilters = {
  vehicleId: null,
  driverId: null,
  from: null,
  until: null,
  onlyOpen: false,
}

/** Um parâmetro que só conta se tiver conteúdo. String vazia é ausência, não valor. */
function read(params: URLSearchParams, key: string): string | null {
  const value = params.get(key)
  if (value === null) return null

  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

/** Lê os filtros da query string da URL.
 *
 *  `abertos` é o único booleano, e só `true`/`1` o ligam: qualquer outra coisa é `false`. Ser
 *  permissivo aqui (tratar a mera presença como verdadeiro) faria `?abertos=false` ligar o
 *  filtro, que é o oposto do que a URL diz. */
export function readUsageFilters(params: URLSearchParams): UsageFilters {
  const abertos = read(params, 'abertos')

  return {
    vehicleId: read(params, 'veiculo'),
    driverId: read(params, 'condutor'),
    from: read(params, 'de'),
    until: read(params, 'ate'),
    onlyOpen: abertos === 'true' || abertos === '1',
  }
}

/** Os filtros de volta pra query string — a operação inversa da de cima.
 *
 *  Filtro ausente **não aparece**: uma URL com `?veiculo=&condutor=&de=` é ruído pra quem a
 *  copia, e some a diferença entre "sem filtro" e "filtro vazio". `abertos=false` também some,
 *  porque `false` é o padrão. */
export function usageFiltersToSearchParams(filters: UsageFilters): URLSearchParams {
  const params = new URLSearchParams()

  if (filters.vehicleId) params.set('veiculo', filters.vehicleId)
  if (filters.driverId) params.set('condutor', filters.driverId)
  if (filters.from) params.set('de', filters.from)
  if (filters.until) params.set('ate', filters.until)
  if (filters.onlyOpen) params.set('abertos', 'true')

  return params
}

/** A query string pronta pra `router.replace`, **com** a `?` — ou vazia, quando não há filtro.
 *
 *  Vazia e não `'?'`: um `?` solto na barra de endereço é sujeira que sobrevive a cada
 *  interação. */
export function usageFiltersToQueryString(filters: UsageFilters): string {
  const query = usageFiltersToSearchParams(filters).toString()
  return query === '' ? '' : `?${query}`
}

export function hasAnyUsageFilter(filters: UsageFilters): boolean {
  return usageFiltersToSearchParams(filters).toString() !== ''
}

/**
 * Uma data `YYYY-MM-DD` esticada até cobrir o dia inteiro, **no fuso de quem filtra**.
 *
 * **É a correção que faz o filtro de período dizer a verdade.** O backend compara
 * `started_at >= de` e `started_at <= ate` com `timestamptz`, e uma data crua vira meia-noite:
 * pedir `ate=2026-07-20` excluiria toda viagem do próprio dia 20, e a pessoa juraria que o sistema
 * perdeu os lançamentos dela. `de` continua na meia-noite (é o começo do dia mesmo); `ate` vai
 * pro último instante.
 *
 * **Com fuso na string** — e antes era sem, o que era o mesmo bug uma vez mais. O comentário que
 * estava aqui dizia que "o backend interpreta o horário como o dele", e essa era exatamente a
 * falha: o dele é UTC, então "até 20/07 23:59" virava 20:59 em São Paulo e escondia as viagens do
 * fim da tarde. O dia é o dia de quem lê a tela, e é `toInstant` que o carimba.
 */
export function startOfDay(date: string): string {
  return toInstant(`${date}T00:00:00`)
}

export function endOfDay(date: string): string {
  return toInstant(`${date}T23:59:59.999`)
}

/** Os filtros como o backend os quer em `GET /usos`.
 *
 *  Mesmos nomes da URL — não há tradução, e é assim de propósito: a URL da tela e a query da API
 *  falam a mesma língua, então um filtro novo se lê num lugar só. O que muda é só o período, que
 *  ganha a hora. */
export function usageFiltersToApiQuery(filters: UsageFilters): URLSearchParams {
  const params = new URLSearchParams()

  if (filters.vehicleId) params.set('veiculo', filters.vehicleId)
  if (filters.driverId) params.set('condutor', filters.driverId)
  if (filters.from) params.set('de', startOfDay(filters.from))
  if (filters.until) params.set('ate', endOfDay(filters.until))
  if (filters.onlyOpen) params.set('abertos', 'true')

  return params
}

/**
 * O atalho que a mensagem de sobreposição oferece: as viagens **daquele** veículo **naquele**
 * intervalo.
 *
 * É a peça que fecha o critério 2. O 409 fala de um dado que não está na tela — a viagem que
 * colide é de outra pessoa, possivelmente de outro dia —, e sem um caminho até ela o usuário fica
 * com um "não pode" sem saber por quê. A URL sai da mesma função que os filtros normais usam,
 * então o atalho não pode divergir da tela que ele abre.
 *
 * O intervalo é o do lançamento recusado, em dia cheio: a viagem que colide pode ter começado
 * horas antes da que se tentou lançar, e um recorte por hora a esconderia.
 */
export function overlapFilters(
  vehicleId: string,
  startedAt: string,
  endedAt?: string,
): UsageFilters {
  const from = isoDatePart(startedAt)

  return {
    ...EMPTY_USAGE_FILTERS,
    vehicleId,
    from,
    until: isoDatePart(endedAt ?? startedAt) ?? from,
  }
}

/** O `YYYY-MM-DD` de um instante digitado (`datetime-local` dá `2026-07-20T08:30`).
 *
 *  Corta a string em vez de passar por `Date` porque `datetime-local` **não tem fuso**: um
 *  `new Date(...)` o interpretaria como hora local e o `toISOString()` o devolveria em UTC, o que
 *  vira o dia anterior pra quem digita de madrugada em fuso negativo. */
export function isoDatePart(moment: string): string | null {
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(moment.trim())
  return match ? match[1] : null
}
