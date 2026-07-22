/**
 * A tradução de hora **digitada** para instante **absoluto**.
 *
 * `<input type="datetime-local">` devolve uma parede de relógio sem fuso (`2026-07-20T08:30`), e
 * o backend guarda `timestamptz`. Alguém tem que dizer "08:30 de onde" — e é aqui, no único lugar
 * do sistema que sabe a resposta: o navegador de quem digitou.
 *
 * Mandar a string crua era o que se fazia antes, e custou duas coisas: um **500** no lançamento
 * (o `started_at` ingênuo batia contra o `now()` aware do use case) e, quando não explodia, uma
 * viagem gravada no fuso do servidor — três horas fora, calada. Hoje a borda do backend recusa
 * instante sem fuso com 422, então esquecer de passar por aqui falha alto em vez de mentir baixo.
 */

/** Um `datetime-local` (`2026-07-20T08:30`) como instante ISO com fuso.
 *
 *  `new Date(...)` sobre uma string **sem** offset é interpretado como hora local — que é
 *  exatamente o que se quer aqui, e o oposto do que se quer no `formatMoment` e no `isoDatePart`,
 *  onde a mesma string é só texto a ser recortado. Devolve a string original se não for uma data
 *  reconhecível: quem valida o campo é o zod, e engolir o valor aqui esconderia o erro dele. */
export function toInstant(local: string): string {
  const moment = new Date(local)
  if (Number.isNaN(moment.getTime())) return local

  return moment.toISOString()
}

/** O mesmo, para o campo opcional: vazio continua vazio (o backend lê `undefined` como "viagem
 *  aberta", e um `null` carimbado com fuso seria outra coisa). */
export function toInstantOrUndefined(local: string | null | undefined): string | undefined {
  if (!local) return undefined
  return toInstant(local)
}
