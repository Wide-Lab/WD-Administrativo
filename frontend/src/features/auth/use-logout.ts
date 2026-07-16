'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'

import { logout } from '#/features/auth/api'

export function useLogout() {
  const queryClient = useQueryClient()
  const router = useRouter()

  return useMutation({
    mutationFn: logout,
    meta: { skipUnauthorizedRedirect: true },
    // `onSettled`: se o cookie já expirou, a chamada falha — mas a intenção de sair vale do
    // mesmo jeito, e deixar dado de outro usuário no cache seria pior que o erro.
    onSettled: () => {
      router.replace('/entrar')
      queryClient.clear()
    },
  })
}
