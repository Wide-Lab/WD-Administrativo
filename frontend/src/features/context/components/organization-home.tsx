'use client'

import { ArrowRight, Check } from 'lucide-react'
import Link from 'next/link'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '#/components/ui/card'
import { Can } from '#/features/context/components/can'
import { MODULE_CATALOG } from '#/features/context/modules'
import { buildNav } from '#/features/context/nav'
import type { Persona } from '#/features/context/types'
import { useOrgContext, useOrgId } from '#/features/context/use-org-context'

/** O título da home de cada persona. É o mínimo que a spec pede — o conteúdo de verdade chega
 *  com os módulos (fases 2+). */
const HEADLINE: Record<Persona, { title: string; description: string }> = {
  platform: {
    title: 'Visão da Plataforma',
    description:
      'Você está abrindo este tenant como Widelab. A operação cross-tenant fica na área da Plataforma.',
  },
  company_admin: {
    title: 'Administração',
    description: 'A gestão da sua Empresa e os serviços que ela contratou.',
  },
  collaborator: {
    title: 'Seus serviços',
    description: 'O que a sua Empresa disponibilizou pra você.',
  },
  partner: {
    title: 'Portal do Parceiro',
    description: 'As Empresas que você atende e os serviços conveniados.',
  },
}

/** As capabilities de kernel, em português. **Só entram aqui as que têm um guard de verdade do
 *  outro lado** (`access/domain/permissions.py`) — uma linha nesta lista sem
 *  `require_permission` no backend seria uma promessa que a API não cumpre. */
const CAPABILITY_LABEL: Record<string, string> = {
  'organizations.read': 'Ver as organizações da plataforma',
  'organizations.write': 'Provisionar Empresas e Parceiros',
  'members.read': 'Ver os membros desta organização',
  'members.write': 'Mudar papel e status dos membros',
  'agreements.write': 'Conveniar Parceiros e suspender convênios',
  'modules.read': 'Ver os módulos contratados e o catálogo',
  'modules.write': 'Habilitar e desabilitar módulos',
}

/** O que esta pessoa pode fazer nesta organização.
 *
 *  Cada linha passa por `<Can>`, que é o critério 5 da spec em exercício: um `hr` e um
 *  `company_admin` abrem a mesma casca, na mesma Empresa, e esta lista é uma das coisas que os
 *  separa — o outro eixo, os módulos, é do tenant e é igual pros dois. */
function Capabilities() {
  const { permissions } = useOrgContext()

  const known = Object.keys(CAPABILITY_LABEL).filter((permission) =>
    permissions.includes(permission),
  )

  if (known.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Nesta organização você pode</CardTitle>
        <CardDescription>
          Vem do seu papel aqui. O backend confere de novo a cada ação — esconder não é negar.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2 text-sm">
          {known.map((permission) => (
            <Can key={permission} permission={permission}>
              <li className="flex items-start gap-2">
                <Check className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
                {CAPABILITY_LABEL[permission]}
              </li>
            </Can>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

/** Os módulos que esta Empresa contratou **e** que esta persona usa. Mesma regra do menu —
 *  `buildNav` —, porque duas regras divergiriam no primeiro módulo novo. */
function Modules() {
  const orgId = useOrgId()
  const { persona, modules, permissions } = useOrgContext()

  if (persona === null) return null

  // Só os **módulos**: a `buildNav` passou a devolver também o grupo de kernel (Pessoas,
  // Parceiros), e esta seção é a dos serviços que a Empresa contratou. Filtrar pelo catálogo, e
  // não por uma lista de exclusão, é o que mantém isto certo quando um módulo novo entrar.
  const moduleKeys = new Set(MODULE_CATALOG.map((descriptor) => descriptor.key))
  const items = buildNav({
    orgId,
    persona,
    modules,
    catalog: MODULE_CATALOG,
    permissions,
  }).filter((item) => moduleKeys.has(item.key))

  if (items.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Nenhum serviço por aqui ainda</CardTitle>
          <CardDescription>
            Os módulos que esta organização contratar aparecem aqui e no menu.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <ul className="grid gap-4 sm:grid-cols-2">
      {items.map((item) => (
        <li key={item.key}>
          <Link
            href={item.href}
            className="group flex h-full items-center gap-4 rounded-lg border border-line bg-surface p-4 transition-colors hover:bg-surface-2"
          >
            <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-md bg-surface-2 text-primary-fg group-hover:bg-surface">
              <item.icon className="size-5" />
            </span>
            <span className="font-medium">{item.label}</span>
            <ArrowRight className="ml-auto size-4 shrink-0 text-muted" aria-hidden />
          </Link>
        </li>
      ))}
    </ul>
  )
}

/** A home de uma organização — a mesma rota pra toda persona, conteúdo resolvido por ela.
 *
 *  Placeholder por decisão da spec: navegação, nome da org ativa e o que a pessoa pode fazer.
 *  O conteúdo real chega com os módulos. */
export function OrganizationHome() {
  const { persona, organization } = useOrgContext()

  if (persona === null) return null

  const headline = HEADLINE[persona]

  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{headline.title}</h1>
        <p className="text-sm text-muted">
          {organization?.name ?? 'Esta organização'} — {headline.description}
        </p>
      </div>

      <Modules />
      <Capabilities />
    </div>
  )
}
