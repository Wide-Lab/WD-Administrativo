'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useEffect } from 'react'

import { safeNextPath } from '#/features/auth/lib/next-path'
import { useSession } from '#/features/auth/use-session'

/** Quem já tem sessão não precisa ver o login: manda pro destino guardado (ou pra raiz).
 *
 *  É o caso de quem volta a `/entrar` pelo histórico ou por link antigo depois de já ter
 *  entrado. Não renderiza nada — o formulário atrás continua visível durante a checagem,
 *  o que é seguro: login não é conteúdo autenticado. */
export function RedirectIfAuthenticated() {
  const { isAuthenticated } = useSession()
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (!isAuthenticated) return
    router.replace(safeNextPath(searchParams.get('next')))
  }, [isAuthenticated, router, searchParams])

  return null
}
