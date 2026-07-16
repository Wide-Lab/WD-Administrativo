'use client'

import type { ReactNode } from 'react'

import { useOrgContext } from '#/features/context/use-org-context'

/** Mostra `children` só se a permissão estiver no contexto desta organização.
 *
 *  **Espelha um guard real do backend, nunca substitui um.** Esconder o botão é ergonomia:
 *  quem chamar a rota na mão leva 403 igual. Um `<Can>` sem `require_permission` do outro lado
 *  é um cadeado pintado — se não existe o guard, não use isto, escreva o guard.
 *
 *  A permissão é `string` pelo mesmo motivo que `Permission` é `str` no backend: o kernel
 *  declara as dele e cada módulo de negócio declara as suas, então um enum fechado aqui
 *  obrigaria a casca a mudar a cada módulo novo. */
export function Can({
  permission,
  children,
  fallback = null,
}: {
  permission: string
  children: ReactNode
  fallback?: ReactNode
}) {
  const { permissions } = useOrgContext()

  return <>{permissions.includes(permission) ? children : fallback}</>
}
