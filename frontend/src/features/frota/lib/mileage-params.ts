/**
 * Os parâmetros do relatório de quilometragem, na URL.
 *
 * Mesma disciplina dos filtros de viagem, e pela mesma razão: um relatório é a coisa que mais se
 * cola num e-mail ("olha o mês passado"), e um período em estado de componente morre no F5.
 *
 * A diferença é que aqui **não existe ausência**: `de` e `ate` são obrigatórios na rota do backend
 * (não há relatório "de tudo"), então a leitura sempre devolve um período — o do mês corrente,
 * quando a URL não traz outro. É isso que faz a tela abrir pronta em vez de pedir que a pessoa
 * escolha antes de ver qualquer coisa.
 */

import { currentMonthRange } from '#/features/frota/lib/labels'
import type { MileageGroupBy } from '#/features/frota/types'

export type MileageParams = {
  /** `YYYY-MM-DD`. */
  from: string
  until: string
  groupBy: MileageGroupBy
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/

/** Lê os parâmetros da URL, caindo no mês corrente quando ela não os traz.
 *
 *  Uma data malformada é tratada como ausente, e não como erro: a URL é editável à mão e vem de
 *  e-mail colado, então um `?de=ontem` deve abrir o relatório do mês — não uma tela de erro nem um
 *  422 do backend.
 *
 *  `agrupar_por` só aceita os dois valores que o `MileageGroupBy` do backend define. Qualquer
 *  outra coisa vira `veiculo`, que é o default da rota. */
export function readMileageParams(params: URLSearchParams, now: Date = new Date()): MileageParams {
  const fallback = currentMonthRange(now)
  const from = params.get('de')
  const until = params.get('ate')
  const groupBy = params.get('agrupar_por')

  return {
    from: from && ISO_DATE.test(from) ? from : fallback.from,
    until: until && ISO_DATE.test(until) ? until : fallback.until,
    groupBy: groupBy === 'condutor' ? 'condutor' : 'veiculo',
  }
}

/** Os parâmetros de volta pra query string, **com** a `?`.
 *
 *  Os três sempre aparecem, ao contrário dos filtros de viagem: aqui não há "sem valor", e uma URL
 *  parcial (`?de=…` sem `ate=…`) deixaria o outro lado dependendo do relógio de quem abre — o link
 *  compartilhado mostraria um período diferente no mês seguinte. */
export function mileageParamsToQueryString(params: MileageParams): string {
  const search = new URLSearchParams({
    de: params.from,
    ate: params.until,
    agrupar_por: params.groupBy,
  })

  return `?${search.toString()}`
}
