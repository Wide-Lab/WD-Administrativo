'use client'

import { useQuery } from '@tanstack/react-query'

import { getContext } from '#/features/context/api'
import type { ContextMembership, MyContext } from '#/features/context/types'

export const contextQueryKey = ['context'] as const

type UseContextResult = {
  context: MyContext | null
  memberships: readonly ContextMembership[]
  isLoading: boolean
}

/** Meus vínculos — o bootstrap de roteamento. Quem já sabe o `orgId` quer `useOrgContext`:
 *  papel, permissões e módulos são sempre *dentro de* uma organização. */
export function useMyContext(): UseContextResult {
  const { data, isPending } = useQuery({
    queryKey: contextQueryKey,
    queryFn: getContext,
    staleTime: 30_000,
  })

  return {
    context: data ?? null,
    memberships: data?.memberships ?? [],
    isLoading: isPending,
  }
}
