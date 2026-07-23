'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'

import { updateMember } from '#/features/organization/api'
import type { UpdateMemberInput } from '#/features/organization/types'
import { MEMBERS_QUERY_PREFIX } from '#/features/organization/use-members'

/** Muda papel ou status de um membro (`members.write`).
 *
 *  **Invalidava também o `/me` desta organização, e não invalida mais.** Aquilo existia por um
 *  caso só: o auto-rebaixamento — quem se editava mudava as próprias permissões, e o menu, o
 *  `Can` e a casca inteira saem dali. O caso deixou de existir quando o backend passou a recusar
 *  a auto-edição com 422 (ver `components/member-row-form.tsx`), e o que sobrava era uma
 *  requisição por edição buscando um contexto que não pode ter mudado: editar **outra** pessoa
 *  não mexe no papel, na persona nem nos módulos de quem editou.
 *
 *  Se um dia alguém puder editar o próprio vínculo de novo, esta linha volta junto — e é por
 *  isso que ela está descrita aqui, e não apenas apagada. */
export function useUpdateMember(orgId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ membershipId, input }: { membershipId: string; input: UpdateMemberInput }) =>
      updateMember(orgId, membershipId, input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        predicate: (query) => query.queryKey[0] === MEMBERS_QUERY_PREFIX,
      })
    },
  })
}
