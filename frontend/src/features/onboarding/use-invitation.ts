'use client'

import { useQuery } from '@tanstack/react-query'

import { getInvitation } from '#/features/onboarding/api'
import type { PublicInvitation } from '#/features/onboarding/types'

/** O prefixo é exportado porque o aceite precisa **excluir** esta query do `invalidateQueries`
 *  (ver `use-accept-invitation.ts`) — sem uma chave estável pra apontar, aquela exclusão viraria
 *  uma string solta em dois arquivos. */
export const INVITATION_QUERY_PREFIX = 'invitation'

export const invitationQueryKey = (token: string) => [INVITATION_QUERY_PREFIX, token] as const

type UseInvitationResult = {
  invitation: PublicInvitation | null
  isLoading: boolean
  error: unknown
}

/** O convite por trás do token da URL.
 *
 *  A única query do app que roda **sem sessão** — o que autoriza é o token. 404/410 são erro de
 *  verdade aqui (diferente do 401 do `GET /api/me`, que é um estado): não há convite pra pintar,
 *  e a tela troca de cara. Nenhum deles é 401, então o redirecionamento global de sessão
 *  (`providers.tsx`) não se mete. */
export function useInvitation(token: string): UseInvitationResult {
  const { data, isPending, error } = useQuery({
    queryKey: invitationQueryKey(token),
    queryFn: () => getInvitation(token),
    // Token inválido não melhora com nova tentativa (e o global já é `retry: false`).
    retry: false,
  })

  return {
    invitation: data ?? null,
    isLoading: isPending,
    error,
  }
}
