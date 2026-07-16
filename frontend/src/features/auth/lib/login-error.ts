import { ApiError } from '#/lib/api'

/** Traduz a falha do login pra uma frase que a pessoa possa agir em cima.
 *
 *  401 é deliberadamente genérico: dizer "essa senha está errada" confirmaria que o e-mail
 *  existe, entregando de graça uma lista de usuários válidos a quem estiver sondando. */
export function loginErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return 'E-mail ou senha incorretos.'
    if (error.status === 422) return 'Confira o e-mail e a senha e tente de novo.'
    if (error.status === 429) return 'Muitas tentativas. Espere um instante e tente de novo.'
    if (error.status >= 500) return 'O servidor não respondeu. Tente de novo em instantes.'
    return error.message
  }

  // `fetch` só rejeita por falha de rede — o backend fora do ar, DNS, offline.
  return 'Não foi possível conectar. Verifique sua conexão e tente de novo.'
}
