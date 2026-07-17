'use client'

import { ChevronsUpDown } from 'lucide-react'
import { useRouter } from 'next/navigation'

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '#/components/ui/dropdown-menu'
import { membershipHomePath } from '#/features/context/lib/home-path'
import { ORGANIZATION_TYPE_LABEL, ROLE_LABEL } from '#/features/context/lib/labels'
import type { ContextMembership } from '#/features/context/types'
import { useMyContext } from '#/features/context/use-context'
import { cn } from '#/lib/utils'

/** "Empresa · Colaborador" — o tipo **e** o papel.
 *
 *  A spec pede "tipo e nome" mas exemplifica com o papel ("Widelab — Colaborador"). Os dois
 *  entram porque cada um resolve metade do problema: o tipo separa "Acme, a Empresa" de
 *  "Gomes, o Parceiro", e o papel separa os dois vínculos que a `Entrega` desta spec cita —
 *  "Colaborador aqui e admin ali", que numa lista só de tipos seriam duas linhas idênticas. */
function membershipDescription(membership: ContextMembership): string {
  return `${ORGANIZATION_TYPE_LABEL[membership.organization.type]} · ${ROLE_LABEL[membership.role]}`
}

/** Há escolha a fazer? Com um vínculo só não há seletor — a spec é explícita, e um menu de uma
 *  opção é ruído que sugere uma decisão inexistente. */
export function useCanSwitchOrganization(): boolean {
  const { memberships } = useMyContext()
  return memberships.length > 1
}

type OrganizationSwitcherProps = {
  /** A organização ativa — o `orgId` da URL. `null` na área da Plataforma, que é cross-tenant. */
  activeOrgId: string | null
  /** O nome a mostrar no gatilho. Vem do `/{orgId}` e não dos vínculos, porque um
   *  `platform_admin` alcança tenant em que não tem vínculo — ele não estaria na lista. */
  organizationName: string | null
}

/** O seletor de organização do masthead.
 *
 *  Trocar de organização é **navegar**: o `orgId` da URL é a organização ativa, então este
 *  controle não guarda estado nenhum — ele só empurra pra outra rota. É o que faz o cache do
 *  TanStack se separar sozinho (as chaves incluem `orgId`) e o `layout` re-resolver a persona,
 *  que pode mudar na troca (Colaborador numa Empresa → admin num Parceiro).
 *
 *  Lista só vínculo — quem escolhe **entre** organizações que já são suas. Provisionar tenant e
 *  entrar por convênio são outras specs (03 e 06). */
export function OrganizationSwitcher({ activeOrgId, organizationName }: OrganizationSwitcherProps) {
  const { memberships } = useMyContext()
  const router = useRouter()

  if (memberships.length < 2) return null

  const active = memberships.find((membership) => membership.organization.id === activeOrgId)
  const label = organizationName ?? active?.organization.name ?? 'Escolher organização'

  function handleChange(orgId: string) {
    const target = memberships.find((membership) => membership.organization.id === orgId)
    if (target === undefined || orgId === activeOrgId) return

    router.push(membershipHomePath(target))
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          'flex min-w-0 items-center gap-1.5 rounded-sm px-1.5 py-1 text-sm font-medium',
          'transition-colors hover:bg-surface-2 data-[state=open]:bg-surface-2',
        )}
        aria-label={`Organização ativa: ${label}. Trocar de organização`}
      >
        <span className="min-w-0 truncate">{label}</span>
        <ChevronsUpDown aria-hidden className="size-3.5 shrink-0 text-muted" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start">
        <DropdownMenuLabel>Suas organizações</DropdownMenuLabel>
        <DropdownMenuSeparator />

        {/* `activeOrgId ?? ''` porque o Radix trata `undefined` como não-controlado: na área da
            Plataforma não há `orgId`, e o certo é nenhum item marcado. */}
        <DropdownMenuRadioGroup value={activeOrgId ?? ''} onValueChange={handleChange}>
          {memberships.map((membership) => (
            <DropdownMenuRadioItem
              key={membership.organization.id}
              value={membership.organization.id}
            >
              <span className="flex min-w-0 flex-col">
                <span className="truncate">{membership.organization.name}</span>
                <span className="truncate text-xs text-muted">
                  {membershipDescription(membership)}
                </span>
              </span>
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
