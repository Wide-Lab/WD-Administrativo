'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createInvitation, listInvitations, revokeInvitation } from '#/features/organization/api'
import type { CreateInvitationInput, InvitationStatus } from '#/features/organization/types'

export const INVITATIONS_QUERY_PREFIX = 'invitations'

export const invitationsQueryKey = (orgId: string, page: number, status: InvitationStatus | null) =>
  [INVITATIONS_QUERY_PREFIX, orgId, page, status] as const

/** A fila de quem foi chamado e ainda não entrou (`invitations.read`).
 *
 *  O `status` entra na chave — inclusive quando é `null`. `null` **não** é "sem filtro
 *  qualquer": é o default do backend, que devolve só os pendentes, e ele é uma lista diferente
 *  de `?status=pending` no cache só por acidente de serem iguais hoje. Chaveá-lo mantém o
 *  histórico e a fila em entradas separadas. */
export function useInvitations(
  orgId: string,
  page: number,
  pageSize: number,
  status: InvitationStatus | null,
) {
  return useQuery({
    queryKey: invitationsQueryKey(orgId, page, status),
    queryFn: () => listInvitations(orgId, { page, pageSize, status }),
    retry: false,
  })
}

/** Invalida toda listagem de convite desta organização, qualquer filtro.
 *
 *  Convidar e revogar mudam o que **cada** filtro devolve, não só o da aba aberta: um convite
 *  revogado sai de `pending` e entra em `revoked`. Invalidar só a chave atual deixaria a outra
 *  lista mentindo na próxima troca de filtro. */
function useInvalidateInvitations(orgId: string) {
  const queryClient = useQueryClient()

  return () =>
    queryClient.invalidateQueries({
      predicate: (query) =>
        query.queryKey[0] === INVITATIONS_QUERY_PREFIX && query.queryKey[1] === orgId,
    })
}

/** Convida por e-mail e papel (`invitations.write`). 201, e a lista recarrega. */
export function useCreateInvitation(orgId: string) {
  const invalidate = useInvalidateInvitations(orgId)

  return useMutation({
    mutationFn: (input: CreateInvitationInput) => createInvitation(orgId, input),
    onSuccess: () => invalidate(),
  })
}

/** Revoga um convite pendente (`invitations.write`) — terminal e idempotente.
 *
 *  O 204 sobre um convite **já revogado** é sucesso e cai aqui como sucesso: o `DELETE` afirma um
 *  estado, e ele já é esse. Tratá-lo como erro faria a tela reclamar de algo que deu certo. */
export function useRevokeInvitation(orgId: string) {
  const invalidate = useInvalidateInvitations(orgId)

  return useMutation({
    mutationFn: (invitationId: string) => revokeInvitation(orgId, invitationId),
    onSuccess: () => invalidate(),
  })
}
