'use client'

import { useQuery } from '@tanstack/react-query'

import { getMe } from '#/features/auth/api'
import type { User } from '#/features/auth/types'

export const sessionQueryKey = ['session'] as const

type Session = {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
}

/** Fonte única de "estou logado?". Lê `GET /api/me` — a verdade mora no cookie httpOnly,
 *  então recarregar a página reidrata a sessão sem token no JS. */
export function useSession(): Session {
  const { data, isPending } = useQuery({
    queryKey: sessionQueryKey,
    queryFn: getMe,
    // Credencial inválida não melhora com nova tentativa.
    retry: false,
    staleTime: 30_000,
  })

  return {
    user: data ?? null,
    isLoading: isPending,
    isAuthenticated: data != null,
  }
}
