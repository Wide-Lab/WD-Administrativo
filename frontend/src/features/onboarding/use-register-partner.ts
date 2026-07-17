'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'

import { registerPartner } from '#/features/onboarding/api'
import type { RegisterPartnerInput } from '#/features/onboarding/types'

/** Cadastrar-se é entrar: organização, admin, vínculo e sessão saem da mesma requisição.
 *
 *  Aqui a `/` acerta sempre, e não por sorte: o Parceiro recém-criado tem **um** vínculo — o
 *  `partner_admin` da organização que acabou de nascer —, então `homePathFor` só tem uma
 *  resposta possível. Nem um `orgId` lembrado de outra sessão neste navegador o desvia: ele só
 *  vale se for um vínculo desta pessoa, e ela ainda não tem outro. */
export function useRegisterPartner() {
  const queryClient = useQueryClient()
  const router = useRouter()

  return useMutation({
    mutationFn: (input: RegisterPartnerInput) => registerPartner(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries()
      router.replace('/')
    },
  })
}
