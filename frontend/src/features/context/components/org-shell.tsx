'use client'

import { useRouter } from 'next/navigation'
import { useEffect, type ReactNode } from 'react'

import { Card, CardDescription, CardHeader, CardTitle } from '#/components/ui/card'
import { Skeleton } from '#/components/ui/skeleton'
import { RequireSession } from '#/features/auth/components/require-session'
import { AppShell } from '#/features/context/components/app-shell'
import { homePathFor } from '#/features/context/lib/home-path'
import { readLastOrgId, rememberOrgId } from '#/features/context/lib/last-org'
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

/** Sem vínculo compatível nesta organização (403 no `/me`): manda pra home da persona real.
 *
 *  Redirecionar, e não mostrar "acesso negado", porque o caso comum não é invasão — é uma URL
 *  velha de um vínculo que acabou, ou um link colado de outra pessoa. Não há laço: o backend
 *  omite do `/me/contexto` o que a pessoa não pode abrir, então o destino nunca é esta org.
 *
 *  É isto que cumpre o critério 5 da `05`: o destino é uma organização real da pessoa, e o
 *  seletor do masthead está lá pra ela escolher outra — reseleção, não tela quebrada. A org que
 *  negou nunca foi lembrada (só se lembra o que o backend deixou abrir), então ela não volta a
 *  ser destino. */
function RedirectToOwnHome() {
  const { memberships, isLoading } = useMyContext()
  const router = useRouter()

  useEffect(() => {
    if (isLoading) return
    // Sem vínculo nenhum, a `/` é quem sabe explicar — não invente destino aqui.
    router.replace(homePathFor(memberships, readLastOrgId()) ?? '/')
  }, [isLoading, memberships, router])

  return <ShellSkeleton />
}

function OrgContextBoundary({ children }: { children: ReactNode }) {
  const orgId = useOrgId()
  const { orgContext, organization, persona, modules, isLoading, isForbidden } = useOrgContext()

  // Só se lembra da organização que o backend **deixou abrir**: um `orgId` que respondeu 403
  // nunca vira o destino do próximo login. Lembrar não escolhe nada — a organização ativa é a
  // URL; isto é só o palpite de pra onde ir quando ainda não há URL (`homePathFor`).
  useEffect(() => {
    if (orgContext === null) return
    rememberOrgId(orgId)
  }, [orgContext, orgId])

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
 *  login em vez de gastar um 401 no `/me`; o contexto depois, porque só faz sentido perguntar
 *  "quem sou eu aqui" havendo um "eu". */
export function OrgShell({ children }: { children: ReactNode }) {
  return (
    <RequireSession>
      <OrgContextBoundary>{children}</OrgContextBoundary>
    </RequireSession>
  )
}
