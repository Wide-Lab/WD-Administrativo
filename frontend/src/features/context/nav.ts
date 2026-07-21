/** A navegação da casca: função pura de `persona` × `modules` × catálogo.
 *
 *  Pura de propósito — é a regra que decide o que cada pessoa enxerga, e a única peça da casca
 *  que dá pra provar sem browser. Ela é **ergonomia, não segurança**: esconder o item não
 *  protege nada, quem nega é o `require_module` do backend (403). */

import { Handshake, Home, Users } from 'lucide-react'
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

type NavAudience = {
  persona: Persona
  /** As capabilities desta pessoa **nesta** organização (do `/me`). */
  permissions: readonly string[]
}

type KernelNavDescriptor = {
  key: string
  label: string
  /** Relativo à organização ativa, como o do módulo. */
  path: string
  icon: NavIcon
  isVisible: (audience: NavAudience) => boolean
}

/** As telas de **kernel** da organização — não são módulos, e é por isso que não saem do
 *  catálogo: ninguém as contrata, elas existem em todo tenant (`frontend/08`).
 *
 *  **Pessoas entra por capability, não por persona**, e a razão é que persona acertaria por
 *  acidente: `company_admin`, `hr` e `partner_admin` são personas diferentes que precisam da
 *  tela, e `finance` e `manager` compartilham a persona `company_admin` com o `hr` sem precisar
 *  dela. Só `members.read` separa esses dois grupos.
 *
 *  **Parceiros não tem capability pra usar** — `GET .../convenios` exige só o vínculo com a
 *  organização do path, porque "serve à Empresa e ao Parceiro". Então o filtro aqui é a persona,
 *  e ele é mais estreito do que a rota permite: um `collaborator` **conseguiria** ler os
 *  convênios da Empresa dele, mas o critério 1 da spec diz que ele não vê o item — convênio é
 *  assunto de quem administra a organização, não de quem consome os serviços dela. Isto é
 *  ergonomia declarada, não segurança: quem digitar a URL alcança a rota, e é o backend, não
 *  esta linha, quem decide o que ela devolve. */
const KERNEL_NAV: readonly KernelNavDescriptor[] = [
  {
    key: 'pessoas',
    label: 'Pessoas',
    path: '/pessoas',
    icon: Users,
    isVisible: ({ permissions }) => permissions.includes('members.read'),
  },
  {
    key: 'parceiros',
    label: 'Parceiros',
    path: '/parceiros',
    icon: Handshake,
    isVisible: ({ persona }) => persona === 'company_admin' || persona === 'partner',
  },
]

type BuildNavParams = {
  orgId: string
  persona: Persona
  /** As chaves habilitadas **desta organização** (do `/me`). */
  modules: readonly string[]
  catalog: readonly ModuleNavDescriptor[]
  /** As capabilities desta pessoa nesta organização (do `/me`) — o que decide o grupo do kernel. */
  permissions: readonly string[]
}

/** Os itens de navegação da organização ativa, em três grupos: a home, os módulos contratados e
 *  as telas de kernel da organização.
 *
 *  Um módulo entra se passa nos **dois** filtros: o tenant o contratou (`modules`) e ele atende
 *  esta persona. Só o primeiro seria errado — Refeições não tem tela de Plataforma, e um
 *  `platform_admin` inspecionando o tenant veria um item que não é dele.
 *
 *  Uma chave habilitada que o catálogo não conhece é ignorada em silêncio: o backend pode ter
 *  um módulo que este deploy do frontend ainda não tem, e isso é o normal de um monólito que
 *  sobe em dois containers — não é erro que mereça quebrar o menu.
 *
 *  O grupo do kernel vem por último de propósito: ele é administração da organização, e o que a
 *  pessoa abriu o sistema pra fazer são os módulos. */
export function buildNav({
  orgId,
  persona,
  modules,
  catalog,
  permissions,
}: BuildNavParams): NavItem[] {
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

  for (const descriptor of KERNEL_NAV) {
    if (!descriptor.isVisible({ persona, permissions })) continue

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
