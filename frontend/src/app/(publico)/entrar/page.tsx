import { Suspense } from 'react'

import { Wordmark } from '#/components/layout/wordmark'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '#/components/ui/card'
import { Skeleton } from '#/components/ui/skeleton'
import { LedgerBackdrop } from '#/features/auth/components/ledger-backdrop'
import { LoginForm } from '#/features/auth/components/login-form'
import { RedirectIfAuthenticated } from '#/features/auth/components/redirect-if-authenticated'

export const metadata = {
  title: 'Entrar · Superapp Widelab',
}

export default function EntrarPage() {
  return (
    <main className="relative flex min-h-dvh items-center justify-center px-6 py-12">
      <LedgerBackdrop />

      <div className="relative w-full max-w-sm space-y-8">
        <div className="flex justify-center">
          <Wordmark />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Entrar</CardTitle>
            <CardDescription>Uma conta para todos os serviços da sua organização.</CardDescription>
          </CardHeader>
          <CardContent>
            {/* `useSearchParams` (o `?next=`) obriga uma fronteira de Suspense no App Router. */}
            <Suspense fallback={<Skeleton className="h-64 w-full" />}>
              <RedirectIfAuthenticated />
              <LoginForm />
            </Suspense>
          </CardContent>
        </Card>

        {/* Não há "esqueci minha senha": redefinição de senha está fora do escopo do
            backend 02. Um link morto seria pior que dizer a quem recorrer. */}
        <p className="text-center text-sm text-muted">
          Problemas para entrar? Fale com quem administra sua organização.
        </p>
      </div>
    </main>
  )
}
