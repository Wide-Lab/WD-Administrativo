'use client'

import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

import { Card, CardDescription, CardHeader, CardTitle } from '#/components/ui/card'
import { Skeleton } from '#/components/ui/skeleton'
import { RequireSession } from '#/features/auth/components/require-session'
import { homePathFor } from '#/features/context/lib/home-path'
import { useMyContext } from '#/features/context/use-context'

/** A `/` não tem tela: ela **roteia**. É o destino padrão do pós-login (`safeNextPath`) e o
 *  fallback de toda guarda, então precisa saber pra onde vai quem só disse "quero entrar".
 *
 *  Aposenta o placeholder da spec 03, que existia só pra provar o ciclo de sessão. Quem decide
 *  o destino é `homePathFor`, função pura e testada — a home de verdade é da persona. */
function ContextRouter() {
  const { memberships, isLoading } = useMyContext()
  const router = useRouter()
  const home = isLoading ? null : homePathFor(memberships)

  useEffect(() => {
    if (home === null) return
    router.replace(home)
  }, [home, router])

  // Sem vínculo nenhum: não é erro, e não há pra onde mandar. Um convite pendente (spec 06) ou
  // um vínculo desativado caem aqui — o backend omite do contexto o que não dá pra abrir.
  if (!isLoading && home === null) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-lg flex-col justify-center px-6">
        <Card>
          <CardHeader>
            <CardTitle>Você ainda não está em nenhuma organização</CardTitle>
            <CardDescription>
              Sua conta existe, mas nenhum vínculo ativo foi encontrado. Quem administra a sua
              organização pode incluir você.
            </CardDescription>
          </CardHeader>
        </Card>
      </main>
    )
  }

  return (
    <div className="mx-auto w-full max-w-4xl space-y-4 px-6 py-16" aria-busy="true">
      <span className="sr-only">Abrindo sua área…</span>
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-40 w-full" />
    </div>
  )
}

export default function Page() {
  return (
    <RequireSession>
      <ContextRouter />
    </RequireSession>
  )
}
