'use client'

import { usePathname, useRouter } from 'next/navigation'
import { useEffect, type ReactNode } from 'react'

import { useSession } from '#/features/auth/use-session'
import { Skeleton } from '#/components/ui/skeleton'

/** Guarda das áreas autenticadas: sem sessão, manda pro login guardando o destino.
 *
 *  Enquanto a sessão carrega, renderiza esqueleto — nunca o conteúdo. Mostrar a área
 *  autenticada "otimista" e retirá-la depois vazaria, ainda que por um quadro, algo que a
 *  pessoa pode não ter direito de ver. */
export function RequireSession({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useSession()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (isLoading || isAuthenticated) return
    router.replace(`/entrar?next=${encodeURIComponent(pathname)}`)
  }, [isAuthenticated, isLoading, pathname, router])

  if (isLoading || !isAuthenticated) {
    return (
      <div className="mx-auto w-full max-w-4xl space-y-4 px-6 py-16" aria-busy="true">
        <span className="sr-only">Verificando sua sessão…</span>
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full max-w-sm" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  return <>{children}</>
}
