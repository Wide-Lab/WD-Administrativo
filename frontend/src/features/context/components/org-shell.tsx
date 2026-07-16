'use client'

import { useRouter } from 'next/navigation'
import { useEffect, type ReactNode } from 'react'

import { Card, CardDescription, CardHeader, CardTitle } from '#/components/ui/card'
import { Skeleton } from '#/components/ui/skeleton'
import { RequireSession } from '#/features/auth/components/require-session'
import { AppShell } from '#/features/context/components/app-shell'
import { homePathFor } from '#/features/context/lib/home-path'
import { MODULE_CATALOG } from '#/features/context/modules'
import { buildNav } from '#/features/context/nav'
import { useMyContext } from '#/features/context/use-context'
import { useOrgContext, useOrgId } from '#/features/context/use-org-context'

function ShellSkeleton() {
  return (
    <div className="mx-auto w-full max-w-7xl space-y-6 px-6 py-8" aria-busy="true">
      <span className="sr-only">Carregando esta organização…</span>
      <Skeleton className="h-8 w-56" />
      <Skeleton className="h-4 w-full max-w-sm" />
      <Skeleton className="h-40 w-full" />
    </div>
  )
}

/** Sem vínculo compatível nesta organização (403 no `/eu`): manda pra home da persona real.
 *
 *  Redirecionar, e não mostrar "acesso negado", porque o caso comum não é invasão — é uma URL
 *  velha de um vínculo que acabou, ou um link colado de outra pessoa. Não há laço: o backend
 *  omite do `/me/contexto` o que a pessoa não pode abrir, então o destino nunca é esta org. */
function RedirectToOwnHome() {
  const { memberships, isLoading } = useMyContext()
  const router = useRouter()

  useEffect(() => {
    if (isLoading) return
    // Sem vínculo nenhum, a `/` é quem sabe explicar — não invente destino aqui.
    router.replace(homePathFor(memberships) ?? '/')
  }, [isLoading, memberships, router])

  return <ShellSkeleton />
}

function OrgContextBoundary({ children }: { children: ReactNode }) {
  const orgId = useOrgId()
  const { orgContext, organization, persona, modules, isLoading, isForbidden } = useOrgContext()

  if (isForbidden) return <RedirectToOwnHome />
  if (isLoading) return <ShellSkeleton />

  if (orgContext === null || persona === null) {
    return (
      <Card className="mx-auto mt-12 max-w-lg">
        <CardHeader>
          <CardTitle>Não foi possível abrir esta organização</CardTitle>
          <CardDescription>Tente recarregar a página em instantes.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <AppShell
      orgId={orgId}
      organizationName={organization?.name ?? null}
      persona={persona}
      nav={buildNav({ orgId, persona, modules, catalog: MODULE_CATALOG })}
    >
      {children}
    </AppShell>
  )
}

/** A casca de tudo que vive sob `/organizacoes/[orgId]`.
 *
 *  Duas camadas, e a ordem importa: `RequireSession` primeiro, pra quem não está logado ir pro
 *  login em vez de gastar um 401 no `/eu`; o contexto depois, porque só faz sentido perguntar
 *  "quem sou eu aqui" havendo um "eu". */
export function OrgShell({ children }: { children: ReactNode }) {
  return (
    <RequireSession>
      <OrgContextBoundary>{children}</OrgContextBoundary>
    </RequireSession>
  )
}
