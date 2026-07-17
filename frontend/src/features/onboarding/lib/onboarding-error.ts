/** Traduz as falhas do onboarding pra frases que a pessoa possa agir em cima.
 *
 *  Puras e testadas pelo mesmo motivo do `login-error.ts`: é a camada onde um descuido vira
 *  vazamento. Aqui o cuidado tem um nome — o critério 4 da spec ("nenhuma tela de onboarding
 *  revela existência prévia de conta por e-mail"). Nenhuma mensagem do **convite** distingue
 *  quem já tinha conta de quem não tinha, porque o backend também não distingue: ele responde
 *  byte a byte igual pros dois casos (backend 06).
 */

import { ApiError } from '#/lib/api'

/** O que serve a qualquer uma das três chamadas. `error.message` por último: o `core` do backend
 *  manda `{code, message}`, e a mensagem dele é melhor que um chute genérico meu. */
function fallbackMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    // `fetch` só rejeita por falha de rede — backend fora do ar, DNS, offline.
    return 'Não foi possível conectar. Verifique sua conexão e tente de novo.'
  }

  if (error.status >= 500) return 'O servidor não respondeu. Tente de novo em instantes.'
  if (error.status === 422) return 'Confira os dados e tente de novo.'

  return error.message
}

/** Por que a tela de aceite não abriu (`GET /api/convites/{token}`).
 *
 *  404 e 410 são coisas diferentes pro backend — nunca existiu × existiu e não vale mais — e a
 *  tela diz as duas, porque a saída é diferente: link torto se copia de novo, convite gasto se
 *  pede de novo. Nenhuma das duas fala de conta: um convite é do e-mail, não de quem o tem. */
export function invitationErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return 'Este link de convite não é válido. Confira se ele foi copiado inteiro.'
    }
    if (error.status === 410) {
      return 'Este convite expirou ou já foi usado. Peça um novo a quem convidou você.'
    }
  }

  return fallbackMessage(error)
}

/** Por que o aceite não passou (`POST /api/convites/{token}/aceitar`).
 *
 *  O 410 aqui é o caso que a tela de cima já não pega: o convite valia quando a página abriu e
 *  não vale mais agora — venceu com a aba aberta, ou alguém o usou primeiro. O token é de uso
 *  único, e um segundo aceite do mesmo token cai exatamente aqui. */
export function acceptInvitationErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 410) {
    return 'Este convite não vale mais — ele pode ter expirado ou já ter sido usado. Peça um novo a quem convidou você.'
  }

  return fallbackMessage(error)
}

/** O e-mail do auto-cadastro já tem conta (409).
 *
 *  É a única falha do onboarding com um caminho de saída — entrar —, e é o que a tela precisa
 *  saber pra oferecer o link. Separado da mensagem porque um link é JSX, não string. */
export function isEmailConflict(error: unknown): boolean {
  return error instanceof ApiError && error.status === 409
}

/** Por que o auto-cadastro de Parceiro não passou (`POST /api/parceiros/cadastro`).
 *
 *  O 409 **conta** que o e-mail já tem conta, e isso é uma exceção consciente à resposta
 *  uniforme do convite: aqui quem está do outro lado é a dona do e-mail, tentando criar a
 *  própria conta, e o critério 2 da spec cobra o conflito com caminho pro login. Quem escolheu
 *  isso foi a `backend/06`, que já responde 409 — a tela só não mente sobre o que ouviu. */
export function registerPartnerErrorMessage(error: unknown): string {
  if (isEmailConflict(error)) {
    return 'Este e-mail já tem uma conta no Superapp.'
  }

  return fallbackMessage(error)
}
