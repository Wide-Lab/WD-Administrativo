'use client'

import { LogOut } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, type ReactNode } from 'react'

import { Wordmark } from '#/components/layout/wordmark'
import { Button } from '#/components/ui/button'
import { Skeleton } from '#/components/ui/skeleton'
import { RequireSession } from '#/features/auth/components/require-session'
import { useLogout } from '#/features/auth/use-logout'
import { useSession } from '#/features/auth/use-session'
import {
  OrganizationSwitcher,
  useCanSwitchOrganization,
} from '#/features/context/components/organization-switcher'
import { homePathFor, isPlatformMembership } from '#/features/context/lib/home-path'
import { forgetLastOrgId, readLastOrgId } from '#/features/context/lib/last-org'
import { useMyContext } from '#/features/context/use-context'

/** A guarda de persona da área da Plataforma.
 *
 *  Ela é **cross-tenant** e não tem `orgId`, então não há `/me` pra perguntar — a fonte é o
 *  `/me/contexto`: ter vínculo numa organização do tipo `platform` é ser Widelab. Quem não
 *  tem vai pra home da própria persona, como a spec pede.
 *
 *  Continua sendo ergonomia: as rotas de plataforma do backend exigem `platform_admin`
 *  (`organizations.read`/`write`), e respondem 403 pra quem chegar por fora desta tela. */
export function PlatformShell({ children }: { children: ReactNode }) {
  return (
    <RequireSession>
      <PlatformGuard>{children}</PlatformGuard>
    </RequireSession>
  )
}

function PlatformGuard({ children }: { children: ReactNode }) {
  const { memberships, isLoading } = useMyContext()
  const router = useRouter()
  const isPlatform = memberships.some(isPlatformMembership)

  useEffect(() => {
    if (isLoading || isPlatform) return
    // `homePathFor` nunca devolve `/plataforma` aqui: quem não é da Widelab não tem o vínculo
    // que apontaria pra cá, então não há laço.
    router.replace(homePathFor(memberships, readLastOrgId()) ?? '/')
  }, [isLoading, isPlatform, memberships, router])

  // A mesa da Plataforma é cross-tenant: estar aqui é não estar em organização nenhuma, e é o
  // que o próximo login precisa saber. Sem isto, um `platform_admin` que visitou um tenant uma
  // vez cairia nele pra sempre — o `orgId` lembrado ganha do atalho da Plataforma.
  useEffect(() => {
    if (!isPlatform) return
    forgetLastOrgId()
  }, [isPlatform])

  if (isLoading || !isPlatform) {
    return (
      <div className="mx-auto w-full max-w-5xl space-y-4 px-6 py-16" aria-busy="true">
        <span className="sr-only">Carregando a área da Plataforma…</span>
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  return (
    <div className="min-h-dvh">
      <PlatformMasthead />
      <main className="mx-auto w-full max-w-5xl px-6 py-8">{children}</main>
    </div>
  )
}

function PlatformMasthead() {
  const { user } = useSession()
  const logout = useLogout()
  const { memberships } = useMyContext()
  const canSwitch = useCanSwitchOrganization()

  // O `PlatformGuard` só renderiza esta casca havendo vínculo de plataforma.
  const platform = memberships.find(isPlatformMembership)

  return (
    <header className="sticky top-0 z-10 border-b border-line bg-bg/80 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-3 px-6">
        <Wordmark />
        <span aria-hidden className="hidden text-line sm:inline">
          /
        </span>
        {/* Sem seletor, quem é da Widelab e também tem vínculo num tenant não teria como sair
            daqui a não ser editando a URL — era o que a `04` deixou em aberto. */}
        {canSwitch && (
          <OrganizationSwitcher
            activeOrgId={platform?.organization.id ?? null}
            organizationName={platform?.organization.name ?? null}
          />
        )}
        <span className="rounded-sm bg-surface-2 px-1.5 py-0.5 text-xs text-muted">Plataforma</span>

        <div className="ml-auto flex items-center gap-3">
          <span className="hidden text-sm text-muted md:inline">{user?.name}</span>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => logout.mutate()}
            disabled={logout.isPending}
            aria-label="Sair"
            title="Sair"
          >
            <LogOut aria-hidden />
          </Button>
        </div>
      </div>
    </header>
  )
}
