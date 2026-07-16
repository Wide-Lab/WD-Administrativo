/** A navegação da casca: função pura de `persona` × `modules` × catálogo.
 *
 *  Pura de propósito — é a regra que decide o que cada pessoa enxerga, e a única peça da casca
 *  que dá pra provar sem browser. Ela é **ergonomia, não segurança**: esconder o item não
 *  protege nada, quem nega é o `require_module` do backend (403). */

import { Home } from 'lucide-react'
import type { ComponentType } from 'react'

import type { ModuleNavDescriptor } from '#/features/context/modules'
import type { Persona } from '#/features/context/types'

export type NavIcon = ComponentType<{ className?: string }>

export type NavItem = {
  key: string
  label: string
  /** Absoluto, com o `orgId` já embutido — trocar de organização é navegar pra outro `orgId`. */
  href: string
  icon: NavIcon
}

export function organizationHomePath(orgId: string): string {
  return `/organizacoes/${encodeURIComponent(orgId)}`
}

type BuildNavParams = {
  orgId: string
  persona: Persona
  /** As chaves habilitadas **desta organização** (do `/me`). */
  modules: readonly string[]
  catalog: readonly ModuleNavDescriptor[]
}

/** Os itens de navegação da organização ativa.
 *
 *  Um módulo entra se passa nos **dois** filtros: o tenant o contratou (`modules`) e ele atende
 *  esta persona. Só o primeiro seria errado — Refeições não tem tela de Plataforma, e um
 *  `platform_admin` inspecionando o tenant veria um item que não é dele.
 *
 *  Uma chave habilitada que o catálogo não conhece é ignorada em silêncio: o backend pode ter
 *  um módulo que este deploy do frontend ainda não tem, e isso é o normal de um monólito que
 *  sobe em dois containers — não é erro que mereça quebrar o menu. */
export function buildNav({ orgId, persona, modules, catalog }: BuildNavParams): NavItem[] {
  const home = organizationHomePath(orgId)

  const items: NavItem[] = [{ key: 'inicio', label: 'Início', href: home, icon: Home }]

  for (const descriptor of catalog) {
    if (!modules.includes(descriptor.key)) continue
    if (!descriptor.personas.includes(persona)) continue

    items.push({
      key: descriptor.key,
      label: descriptor.label,
      href: `${home}${descriptor.path}`,
      icon: descriptor.icon,
    })
  }

  return items
}

/** Se o item corresponde à rota atual.
 *
 *  A home casa exato e o módulo casa por prefixo: a home é prefixo de **todo** item da
 *  organização, então compará-la por prefixo a deixaria acesa o tempo todo; já uma tela de
 *  dentro do módulo (`/refeicoes/tickets/1`, fase 2) tem de manter Refeições aceso. */
export function isNavItemActive(pathname: string, item: NavItem, orgId: string): boolean {
  const home = organizationHomePath(orgId)

  if (item.href === home) return pathname === home

  return pathname === item.href || pathname.startsWith(`${item.href}/`)
}
