'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { Can } from '#/features/context/components/can'
import { useOrgId } from '#/features/context/use-org-context'
import { FrotaPermissions } from '#/features/frota/permissions'
import { frotaPath } from '#/features/frota/module'
import { cn } from '#/lib/utils'

/**
 * A navegação interna da frota — **um item no menu da casca, quatro telas dentro**.
 *
 * O `buildNav` monta um item por módulo, e não vamos mexer nisso pra encaixar quatro: a casca é do
 * kernel, e um módulo que precisa editar o menu da casca pra existir quebra a promessa de que
 * módulo pluga sem tocar o núcleo. A navegação interna é do módulo, e é isto aqui.
 *
 * São links, não um `Tabs` de Radix: cada aba é uma **rota** — compartilhável, com F5, com voltar
 * do navegador. Um painel de abas com estado local perderia as três coisas.
 *
 * **Quem vê o quê sai de capability, nunca de persona.** `company_admin` e `manager` recebem
 * grants idênticos da frota e são personas diferentes; o que separa o `collaborator` é
 * capability. Ramificar por persona acertaria por acidente hoje e erraria no primeiro papel novo.
 */
export function FrotaTabs() {
  const orgId = useOrgId()
  const pathname = usePathname()

  const tabs = [
    { href: frotaPath(orgId), label: 'Viagens', permission: null },
    {
      href: frotaPath(orgId, '/veiculos'),
      label: 'Veículos',
      permission: FrotaPermissions.VEHICLES_READ,
    },
    {
      href: frotaPath(orgId, '/condutores'),
      label: 'Condutores',
      permission: FrotaPermissions.DRIVERS_READ,
    },
    {
      href: frotaPath(orgId, '/relatorios'),
      label: 'Quilometragem',
      permission: FrotaPermissions.USAGES_READ,
    },
  ]

  const home = frotaPath(orgId)

  return (
    <nav aria-label="Seções da frota" className="border-b border-line">
      <ul className="-mb-px flex gap-1 overflow-x-auto">
        {tabs.map((tab) => {
          // Viagens casa exato; as demais casam por prefixo, pra uma tela de dentro manter a aba
          // acesa. Mesma regra do `isNavItemActive` da casca, e pelo mesmo motivo: a home é
          // prefixo de todas.
          const active = tab.href === home ? pathname === home : pathname.startsWith(tab.href)

          const link = (
            <li key={tab.href}>
              <Link
                href={tab.href}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'inline-block border-b-2 px-4 py-2.5 text-sm whitespace-nowrap transition-colors',
                  active
                    ? 'border-primary font-medium text-text'
                    : 'border-transparent text-muted hover:border-line hover:text-text',
                )}
              >
                {tab.label}
              </Link>
            </li>
          )

          if (tab.permission === null) return link

          return (
            <Can key={tab.href} permission={tab.permission}>
              {link}
            </Can>
          )
        })}
      </ul>
    </nav>
  )
}
