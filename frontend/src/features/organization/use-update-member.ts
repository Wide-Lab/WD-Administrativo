'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'

import { orgContextQueryKey } from '#/features/context/use-org-context'
import { updateMember } from '#/features/organization/api'
import type { UpdateMemberInput } from '#/features/organization/types'
import { MEMBERS_QUERY_PREFIX } from '#/features/organization/use-members'

/** Muda papel ou status de um membro (`members.write`).
 *
 *  Invalida **também** o `/me` desta organização, e não só a lista: quem se edita muda as
 *  próprias permissões, e o menu, o `Can` e a casca inteira saem dali. Sem isso, um
 *  `company_admin` que se rebaixasse continuaria vendo os botões que acabou de perder até
 *  recarregar a página — a tela mentindo sobre o que o backend já nega. Ver o comentário sobre
 *  auto-rebaixamento em `components/member-row-form.tsx`. */
export function useUpdateMember(orgId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ membershipId, input }: { membershipId: string; input: UpdateMemberInput }) =>
      updateMember(orgId, membershipId, input),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          predicate: (query) => query.queryKey[0] === MEMBERS_QUERY_PREFIX,
        }),
        queryClient.invalidateQueries({ queryKey: orgContextQueryKey(orgId) }),
      ])
    },
  })
}
