'use client'

import { LogOut } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { ReactNode } from 'react'

import { Wordmark } from '#/components/layout/wordmark'
import { Button } from '#/components/ui/button'
import { useLogout } from '#/features/auth/use-logout'
import { useSession } from '#/features/auth/use-session'
import { isNavItemActive, type NavItem } from '#/features/context/nav'
import type { Persona } from '#/features/context/types'
import { cn } from '#/lib/utils'

/** Como cada persona se chama pra quem a está usando. `company_admin` vira "Administração"
 *  porque a pessoa não se apresenta pelo papel — `hr` e `finance` também caem aqui. */
const PERSONA_LABEL: Record<Persona, string> = {
  platform: 'Plataforma',
  company_admin: 'Administração',
  collaborator: 'Colaborador',
  partner: 'Parceiro',
}

function Masthead({
  organizationName,
  persona,
  compact = false,
}: {
  organizationName: string | null
  persona: Persona
  compact?: boolean
}) {
  const { user } = useSession()
  const logout = useLogout()

  return (
    <header className="sticky top-0 z-10 border-b border-line bg-bg/80 backdrop-blur-sm">
      <div
        className={cn(
          'mx-auto flex h-14 items-center gap-3 px-4',
          compact ? 'max-w-2xl' : 'max-w-7xl px-6',
        )}
      >
        <Wordmark className={compact ? 'hidden sm:inline-flex' : ''} />

        {organizationName !== null && (
          <>
            <span aria-hidden className="hidden text-line sm:inline">
              /
            </span>
            <span className="min-w-0 truncate text-sm font-medium">{organizationName}</span>
            <span className="rounded-sm bg-surface-2 px-1.5 py-0.5 text-xs text-muted">
              {PERSONA_LABEL[persona]}
            </span>
          </>
        )}

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

function navLinkClass(active: boolean): string {
  return cn(
    'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
    active ? 'bg-surface-2 font-medium text-text' : 'text-muted hover:bg-surface hover:text-text',
  )
}

function SideNav({ items, orgId }: { items: readonly NavItem[]; orgId: string }) {
  const pathname = usePathname()

  return (
    <nav aria-label="Navegação principal" className="hidden w-56 shrink-0 md:block">
      <ul className="sticky top-20 space-y-1">
        {items.map((item) => {
          const active = isNavItemActive(pathname, item, orgId)
          return (
            <li key={item.key}>
              <Link
                href={item.href}
                aria-current={active ? 'page' : undefined}
                className={navLinkClass(active)}
              >
                <item.icon className="size-4 shrink-0" />
                {item.label}
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

/** A navegação do Colaborador, e a de qualquer persona no celular.
 *
 *  Barra inferior porque é onde o polegar alcança — a persona Colaborador é mobile-first, e é
 *  ela que usa o produto de pé, na fila do restaurante. `pb-[env(safe-area-inset-bottom)]`
 *  mantém os alvos acima da barra de gestos do iOS. */
function BottomNav({
  items,
  orgId,
  className,
}: {
  items: readonly NavItem[]
  orgId: string
  className?: string
}) {
  const pathname = usePathname()

  return (
    <nav
      aria-label="Navegação principal"
      className={cn(
        'fixed inset-x-0 bottom-0 z-10 border-t border-line bg-surface pb-[env(safe-area-inset-bottom)]',
        className,
      )}
    >
      <ul className="mx-auto flex max-w-2xl items-stretch justify-around">
        {items.map((item) => {
          const active = isNavItemActive(pathname, item, orgId)
          return (
            <li key={item.key} className="flex-1">
              <Link
                href={item.href}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'flex min-h-14 flex-col items-center justify-center gap-1 px-2 py-2 text-xs transition-colors',
                  active ? 'text-primary-fg' : 'text-muted hover:text-text',
                )}
              >
                <item.icon className="size-5 shrink-0" />
                {item.label}
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

type AppShellProps = {
  orgId: string
  organizationName: string | null
  persona: Persona
  nav: readonly NavItem[]
  children: ReactNode
}

/** A casca de uma organização: masthead + navegação + conteúdo.
 *
 *  Duas formas, não quatro: o Colaborador é **mobile-first** e vive na barra inferior; as
 *  personas de mesa (Plataforma, Administração, Parceiro) ganham barra lateral no desktop e
 *  caem na mesma barra inferior no celular. O que muda entre elas é o *conteúdo* e a
 *  navegação — que já vêm resolvidos de `buildNav`. */
export function AppShell({ orgId, organizationName, persona, nav, children }: AppShellProps) {
  const isCollaborator = persona === 'collaborator'

  if (isCollaborator) {
    return (
      <div className="flex min-h-dvh flex-col">
        <Masthead organizationName={organizationName} persona={persona} compact />
        <main className="mx-auto w-full max-w-2xl flex-1 px-4 pt-6 pb-24">{children}</main>
        <BottomNav items={nav} orgId={orgId} />
      </div>
    )
  }

  return (
    <div className="min-h-dvh">
      <Masthead organizationName={organizationName} persona={persona} />
      <div className="mx-auto flex w-full max-w-7xl gap-8 px-6 py-8">
        <SideNav items={nav} orgId={orgId} />
        <main className="min-w-0 flex-1 pb-24 md:pb-0">{children}</main>
      </div>
      {/* Só vale a pena no celular quando há pra onde ir — "Início" sozinho não é navegação. */}
      {nav.length > 1 && <BottomNav items={nav} orgId={orgId} className="md:hidden" />}
    </div>
  )
}
