'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createAgreement, listAgreements, updateAgreementStatus } from '#/features/organization/api'
import type { AgreementStatus, CreateAgreementInput } from '#/features/organization/types'

export const AGREEMENTS_QUERY_PREFIX = 'agreements'

export const agreementsQueryKey = (orgId: string, page: number) =>
  [AGREEMENTS_QUERY_PREFIX, orgId, page] as const

/** Os convênios da organização ativa — **sem capability**, só o vínculo.
 *
 *  Uma consulta, dois sentidos de leitura: numa Empresa são os Parceiros dela, num Parceiro são
 *  as Empresas que ele atende. Quem sabe de que lado se está é o rótulo, não a query. */
export function useAgreements(orgId: string, page: number, pageSize: number) {
  return useQuery({
    queryKey: agreementsQueryKey(orgId, page),
    queryFn: () => listAgreements(orgId, { page, pageSize }),
    retry: false,
  })
}

function useInvalidateAgreements(orgId: string) {
  const queryClient = useQueryClient()

  return () =>
    queryClient.invalidateQueries({
      predicate: (query) =>
        query.queryKey[0] === AGREEMENTS_QUERY_PREFIX && query.queryKey[1] === orgId,
    })
}

/** Convenia um Parceiro (`agreements.write` — só `company_admin`, nem `platform_admin`). */
export function useCreateAgreement(orgId: string) {
  const invalidate = useInvalidateAgreements(orgId)

  return useMutation({
    mutationFn: (input: CreateAgreementInput) => createAgreement(orgId, input),
    onSuccess: () => invalidate(),
  })
}

/** Suspende ou reativa um convênio. Diferente de revogar convite, isto **não** é terminal. */
export function useUpdateAgreement(orgId: string) {
  const invalidate = useInvalidateAgreements(orgId)

  return useMutation({
    mutationFn: ({ agreementId, status }: { agreementId: string; status: AgreementStatus }) =>
      updateAgreementStatus(orgId, agreementId, status),
    onSuccess: () => invalidate(),
  })
}
