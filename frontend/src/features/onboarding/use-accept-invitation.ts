'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'

import { acceptInvitation } from '#/features/onboarding/api'
import type { AcceptInvitationInput } from '#/features/onboarding/types'
import { INVITATION_QUERY_PREFIX } from '#/features/onboarding/use-invitation'

/** Aceitar é entrar: o backend emite a sessão na mesma resposta, então daqui pra frente esta
 *  pessoa é um usuário logado como qualquer outro.
 *
 *  O destino é a **`/`**, e não a organização do convite, porque a tela não tem o `orgId` pra
 *  montar a rota: o `GET /api/convites/{token}` devolve o *nome* da organização, nunca o id —
 *  quem ainda não aceitou não é membro de nada (backend 06). E a `/` é justamente quem sabe
 *  responder isso: ela lê o `/me/contexto` já com o vínculo novo dentro e roteia pra home da
 *  persona (`homePathFor`). Pra quem foi convidado e não tinha conta — o caso da esmagadora
 *  maioria — há um vínculo só, e esse vínculo é o do papel aceito. Ver `Como ficou`. */
export function useAcceptInvitation(token: string) {
  const queryClient = useQueryClient()
  const router = useRouter()

  return useMutation({
    mutationFn: (input: AcceptInvitationInput) => acceptInvitation(token, input),
    onSuccess: async () => {
      // O cookie mudou: tudo que foi lido como visitante está velho — a mesma razão do login.
      // O convite fica **de fora** de propósito: ele acabou de virar `accepted`, e buscá-lo de
      // novo responderia 410, piscando "convite inválido" no exato instante em que ele
      // funcionou. Ele já não interessa — o que interessa agora é o contexto.
      await queryClient.invalidateQueries({
        predicate: (query) => query.queryKey[0] !== INVITATION_QUERY_PREFIX,
      })
      router.replace('/')
    },
  })
}
