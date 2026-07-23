/** O que a aba Convites lê da URL e o que ela oferece por status.
 *
 *  Puro e testado porque é a única regra desta tela que não depende de browser — e porque o
 *  filtro é contrato compartilhado com o backend: o `?status=` daqui é o mesmo `?status=` que a
 *  rota lê (`backend/08`), com o mesmo default. */

import { invitationStatusSchema } from '#/features/organization/schema'
import type { InvitationStatus } from '#/features/organization/types'

/** O que a linha oferece, por status **efetivo**.
 *
 *  A tabela é a da spec, e o `accepted` sem ação é a parte que importa: aquele convite virou
 *  membro, e revogá-lo não removeria acesso nenhum — daria a falsa impressão de ter removido.
 *  Tirar o acesso de quem já entrou é `members.write`, na aba ao lado. É por isso que o 409 do
 *  backend não deveria acontecer pela tela; se acontecer, é a lista que envelheceu numa aba
 *  aberta, e a mensagem diz exatamente isso. */
export type InvitationAction = 'revoke' | 'reinvite' | 'none'

export const INVITATION_ACTION: Record<InvitationStatus, InvitationAction> = {
  pending: 'revoke',
  expired: 'reinvite',
  revoked: 'reinvite',
  accepted: 'none',
}

export function actionFor(status: InvitationStatus): InvitationAction {
  return INVITATION_ACTION[status]
}

/** As opções do filtro da aba, em ordem de tela.
 *
 *  **`pending` não está aqui, e a ausência é o conserto de um bug de tela**: a lista nasceu como
 *  "Pendentes" (o default, sem parâmetro) seguido dos quatro valores do enum, e o resultado era
 *  uma barra com `Pendentes · Pendente · Aceito · Revogado · Expirado` — duas opções diferentes
 *  no nome e idênticas no efeito, porque sem `?status=` o backend devolve exatamente os
 *  pendentes. Quem clicasse numa e depois na outra veria a mesma lista e ficaria sem saber o que
 *  havia entendido errado.
 *
 *  Sobrou uma pergunta por status, e a de "pendentes" é a ausência de filtro — que é como o
 *  backend a expressa (`backend/08`). **Não há "Todos"**: a rota não sabe dizer "sem filtro
 *  nenhum", e inventar aqui um valor que ela não aceita daria 422 num clique.
 *
 *  Os rótulos estão no plural, e por isso não saem do `INVITATION_STATUS_LABEL`: lá eles
 *  descrevem **um** convite numa linha da tabela ("Aceito"), aqui nomeiam um recorte da lista
 *  ("Aceitos"). Mesma palavra, número diferente. */
export const STATUS_FILTER_OPTIONS: readonly { value: InvitationStatus | null; label: string }[] = [
  { value: null, label: 'Pendentes' },
  { value: 'accepted', label: 'Aceitos' },
  { value: 'revoked', label: 'Revogados' },
  { value: 'expired', label: 'Expirados' },
]

/** O `?status=` da URL virando filtro.
 *
 *  **`null` é a ausência do parâmetro, e ela é significativa**: sem `?status=` o backend devolve
 *  só os pendentes, que é como a aba abre. Não traduzimos ausência pra `'pending'` aqui — isso
 *  mandaria `?status=pending` na query e daria o mesmo resultado por um caminho diferente,
 *  escondendo de quem lê o código que o default é do servidor.
 *
 *  Um valor que o enum não conhece (link velho, URL editada à mão, `?status=todos`) também vira
 *  `null`: cair no default é melhor que quebrar a tela ou mandar lixo ao backend, que
 *  responderia 422 por um parâmetro que a pessoa nem sabe que existe. */
export function parseStatusFilter(raw: string | null | undefined): InvitationStatus | null {
  if (raw === null || raw === undefined || raw === '') return null

  const parsed = invitationStatusSchema.safeParse(raw)

  return parsed.success ? parsed.data : null
}

/** A query string da aba, pro `<Link>` de cada opção do filtro. Sem filtro, **nenhum**
 *  parâmetro — a URL limpa é a que descreve o estado limpo. */
export function statusFilterHref(pathname: string, status: InvitationStatus | null): string {
  const base = `${pathname}?aba=convites`

  return status === null ? base : `${base}&status=${status}`
}
