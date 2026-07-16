'use client'

import { useQuery } from '@tanstack/react-query'
import { useParams } from 'next/navigation'

import { getOrganization, getOrgContext } from '#/features/context/api'
import type { OrgContext, Organization, Persona } from '#/features/context/types'
import { ApiError } from '#/lib/api'

export const orgContextQueryKey = (orgId: string) => ['org-context', orgId] as const
export const organizationQueryKey = (orgId: string) => ['organization', orgId] as const

/** A organização ativa **é o `orgId` do path** — nunca header, nunca sessão. Trocar de
 *  organização é navegar pra outra URL, e é isso que a torna compartilhável. */
export function useOrgId(): string {
  const params = useParams<{ orgId: string }>()
  return params.orgId
}

type UseOrgContextResult = {
  orgContext: OrgContext | null
  organization: Organization | null
  persona: Persona | null
  permissions: readonly string[]
  modules: readonly string[]
  isLoading: boolean
  /** O backend recusou este tenant pra esta pessoa (403) — sem vínculo, ou vínculo desativado. */
  isForbidden: boolean
}

/** Eu na organização da URL: persona, permissões e módulos habilitados dela.
 *
 *  Fonte única de autorização no cliente. Duas queries em vez de uma porque são duas perguntas
 *  com donos diferentes — "quem sou eu aqui" (`/me`) e "que organização é esta" (`/{orgId}`);
 *  o TanStack as cacheia por chave e a segunda serve toda persona que abrir o mesmo tenant. */
export function useOrgContext(): UseOrgContextResult {
  const orgId = useOrgId()

  const context = useQuery({
    queryKey: orgContextQueryKey(orgId),
    queryFn: () => getOrgContext(orgId),
    staleTime: 30_000,
    // 403 é resposta, não falha de rede: não melhora com nova tentativa.
    retry: false,
  })

  const organization = useQuery({
    queryKey: organizationQueryKey(orgId),
    queryFn: () => getOrganization(orgId),
    staleTime: 30_000,
    retry: false,
  })

  const isForbidden = context.error instanceof ApiError && context.error.status === 403

  return {
    orgContext: context.data ?? null,
    organization: organization.data ?? null,
    persona: context.data?.persona ?? null,
    permissions: context.data?.permissions ?? [],
    modules: context.data?.modules ?? [],
    isLoading: context.isPending || organization.isPending,
    isForbidden,
  }
}
