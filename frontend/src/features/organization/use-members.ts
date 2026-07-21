'use client'

import { useQuery } from '@tanstack/react-query'

import { listMembers } from '#/features/organization/api'

export const MEMBERS_QUERY_PREFIX = 'members'

export const membersQueryKey = (orgId: string, page: number) =>
  [MEMBERS_QUERY_PREFIX, orgId, page] as const

/** Quem tem acesso a esta organização (`members.read`).
 *
 *  O `orgId` entra na chave porque a lista é de um tenant: sem ele, trocar de organização pelo
 *  seletor mostraria o quadro da anterior enquanto o novo carrega. */
export function useMembers(orgId: string, page: number, pageSize: number) {
  return useQuery({
    queryKey: membersQueryKey(orgId, page),
    queryFn: () => listMembers(orgId, { page, pageSize }),
    // 403 é resposta, não falha de rede.
    retry: false,
  })
}
