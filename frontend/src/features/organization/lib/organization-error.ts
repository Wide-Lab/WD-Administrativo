/** Traduz as falhas das telas de gestão pra frases que quem administra possa agir em cima.
 *
 *  Puras e testadas pelo mesmo motivo do `onboarding-error.ts`: é a camada onde um descuido vira
 *  uma mensagem que manda a pessoa pro lugar errado. Aqui o caso que mais importa é o **409 do
 *  convite já aceito** — a saída dele não é "tente de novo", é "essa pessoa já entrou, mexa na
 *  aba ao lado". Uma mensagem genérica faria alguém revogar em loop um convite que não é mais o
 *  problema. */

import { ApiError } from '#/lib/api'

function fallbackMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return 'Não foi possível conectar. Verifique sua conexão e tente de novo.'
  }

  if (error.status >= 500) return 'O servidor não respondeu. Tente de novo em instantes.'
  if (error.status === 403) return 'Você não tem permissão para isso nesta organização.'

  return error.message
}

/** Por que a edição de um membro não passou (`PATCH .../membros/{id}`).
 *
 *  O 422 é repassado **como veio**: a mensagem do backend nomeia o papel recusado e lista os
 *  papéis válidos daquele tipo de organização (`update_membership.py`), e nenhuma frase que eu
 *  escrevesse aqui seria mais útil que essa. É também o que faz o critério 7 se observar: se o
 *  espelho de `ROLES_BY_ORGANIZATION_TYPE` divergir do backend, é esta mensagem que conta. */
export function updateMemberErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 404) {
    return 'Este vínculo não existe mais nesta organização. Recarregue a lista.'
  }

  return fallbackMessage(error)
}

export function createInvitationErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 422) {
    // O papel pode não valer neste tipo de organização — convidar um `hr` pra um Parceiro, por
    // exemplo. A aplicação explica; o `CHECK` do banco é quem impede.
    return error.message
  }

  return fallbackMessage(error)
}

/** Por que a revogação não passou (`DELETE .../convites/{id}`).
 *
 *  O 409 **não deveria chegar pela tela** — a linha de um convite aceito não tem o botão —, mas
 *  chega quando a lista envelheceu numa aba aberta e a pessoa aceitou nesse meio-tempo. A
 *  mensagem tem de dizer o que de fato aconteceu e pra onde ir: revogar aquele convite não
 *  tiraria acesso nenhum, porque ele já virou vínculo.
 *
 *  O 204 sobre um convite já revogado **não** passa por aqui: é sucesso, e idempotente de
 *  propósito (o `DELETE` afirma um estado que já foi alcançado). */
export function revokeInvitationErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      return 'Esta pessoa já aceitou o convite e virou membro — revogá-lo não tiraria o acesso dela. Use a aba Membros para desativar o vínculo.'
    }
    if (error.status === 404) {
      return 'Este convite não existe mais nesta organização. Recarregue a lista.'
    }
  }

  return fallbackMessage(error)
}

/** Por que o convênio não nasceu (`POST .../convenios`).
 *
 *  O 422 aqui cobre dois casos que a tela não tem como distinguir sozinha — o id não existe, ou
 *  existe e não é um Parceiro —, e o backend já os separa na mensagem. O 409 é o convênio que já
 *  existe, e a saída dele é olhar a lista, não tentar de novo. */
export function createAgreementErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      return 'Já existe um convênio com este parceiro. Ele deve estar na lista abaixo — talvez suspenso.'
    }
    if (error.status === 422) {
      return error.message
    }
  }

  return fallbackMessage(error)
}

export function updateAgreementErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 404) {
    return 'Este convênio não existe mais nesta organização. Recarregue a lista.'
  }

  return fallbackMessage(error)
}
