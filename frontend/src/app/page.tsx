'use client'

import { Wordmark } from '#/components/layout/wordmark'
import { Button } from '#/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '#/components/ui/card'
import { RequireSession } from '#/features/auth/components/require-session'
import { useLogout } from '#/features/auth/use-logout'
import { useSession } from '#/features/auth/use-session'

// Placeholder da área autenticada. Existe pra provar o ciclo de sessão da spec 03 (guarda,
// identidade, sair). A casca de verdade, os route groups por persona e a navegação derivada
// de vínculos + entitlements são da spec 04 — e é ela que decide o que é a home.
function Home() {
  const { user } = useSession()
  const logout = useLogout()

  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col justify-center gap-8 px-6 py-16">
      <Wordmark />

      <Card>
        <CardHeader>
          <CardTitle>Você está no Superapp</CardTitle>
          <CardDescription>
            Sua sessão está ativa. As suas organizações e serviços aparecem aqui na próxima entrega.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <dl className="space-y-1 text-sm">
            <dt className="text-muted">Nome</dt>
            <dd className="font-medium">{user?.name}</dd>
            <dt className="pt-3 text-muted">E-mail</dt>
            <dd className="font-mono">{user?.email}</dd>
          </dl>

          <Button variant="secondary" onClick={() => logout.mutate()} disabled={logout.isPending}>
            {logout.isPending ? 'Saindo…' : 'Sair'}
          </Button>
        </CardContent>
      </Card>
    </main>
  )
}

export default function Page() {
  return (
    <RequireSession>
      <Home />
    </RequireSession>
  )
}
