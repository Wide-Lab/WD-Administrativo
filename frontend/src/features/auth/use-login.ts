'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter, useSearchParams } from 'next/navigation'

import { login } from '#/features/auth/api'
import { safeNextPath } from '#/features/auth/lib/next-path'
import type { LoginInput } from '#/features/auth/types'

export function useLogin() {
  const queryClient = useQueryClient()
  const router = useRouter()
  const searchParams = useSearchParams()

  return useMutation({
    mutationFn: (input: LoginInput) => login(input),
    // 401 aqui é "credenciais inválidas", tratado inline no formulário: não deve acionar o
    // redirecionamento global de sessão expirada.
    meta: { skipUnauthorizedRedirect: true },
    onSuccess: async () => {
      // O cookie mudou: tudo que foi lido como visitante está velho. Invalida a sessão e o
      // contexto (spec 04) antes de navegar, pra área autenticada não montar com cache frio.
      await queryClient.invalidateQueries()
      router.replace(safeNextPath(searchParams.get('next')))
    },
  })
}
