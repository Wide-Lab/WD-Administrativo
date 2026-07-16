'use client'

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { useRef, useState, type ReactNode } from 'react'

import { sessionQueryKey } from '#/features/auth/use-session'
import { ApiError } from '#/lib/api'

/** Chamadas que tratam 401 por conta própria marcam `meta: { skipUnauthorizedRedirect: true }`
 *  — o login (401 = credenciais inválidas, erro inline) e o logout (401 = já saiu). */
function skipsRedirect(meta: Record<string, unknown> | undefined): boolean {
  return meta?.skipUnauthorizedRedirect === true
}

export function Providers({ children }: { children: ReactNode }) {
  const router = useRouter()

  // Refs pra que os handlers do cache — criados uma vez, junto do QueryClient — enxerguem
  // sempre a instância atual, sem recriar o client a cada render.
  const routerRef = useRef(router)
  routerRef.current = router
  const clientRef = useRef<QueryClient | null>(null)

  // QueryClient criado uma vez por montagem — estável entre re-renders.
  const [queryClient] = useState(() => {
    /** Sessão expirada ou cookie inválido: derruba a sessão e manda pro login preservando o
     *  destino, pra pessoa voltar exatamente pra onde estava depois de reautenticar.
     *
     *  `GET /api/me` não cai aqui: ele traduz 401 pra `null` (ver `features/auth/api.ts`),
     *  senão o próprio login entraria em laço de redirecionamento. */
    const handleUnauthorized = (error: unknown, meta: Record<string, unknown> | undefined) => {
      if (skipsRedirect(meta)) return
      if (!(error instanceof ApiError) || error.status !== 401) return

      clientRef.current?.setQueryData(sessionQueryKey, null)

      const { pathname, search } = window.location
      if (pathname === '/entrar') return
      routerRef.current.replace(`/entrar?next=${encodeURIComponent(pathname + search)}`)
    }

    return new QueryClient({
      defaultOptions: {
        queries: { retry: false, refetchOnWindowFocus: false },
      },
      queryCache: new QueryCache({
        onError: (error, query) => handleUnauthorized(error, query.meta),
      }),
      mutationCache: new MutationCache({
        onError: (error, _variables, _context, mutation) =>
          handleUnauthorized(error, mutation.meta),
      }),
    })
  })

  clientRef.current = queryClient

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}
