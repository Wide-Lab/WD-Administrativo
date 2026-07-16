import type { ReactNode } from 'react'

import { PlatformShell } from '#/features/context/components/platform-shell'

/** A área da Widelab como operadora: **cross-tenant, sem `orgId`**. Administrar tenants é o
 *  que se faz antes de haver um tenant ativo — por isso ela não vive sob `/organizacoes/[orgId]`. */
export default function PlatformLayout({ children }: { children: ReactNode }) {
  return <PlatformShell>{children}</PlatformShell>
}
