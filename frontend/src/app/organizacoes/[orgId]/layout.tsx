import type { ReactNode } from 'react'

import { OrgShell } from '#/features/context/components/org-shell'

/** Tudo que é de uma organização vive sob `/organizacoes/[orgId]` — o mesmo tenant-no-path da
 *  API (`/api/organizacoes/{orgId}/...`). Este layout carrega o contexto uma vez, resolve a
 *  persona e monta a casca; as páginas de dentro já nascem sabendo quem está olhando. */
export default function OrganizationLayout({ children }: { children: ReactNode }) {
  return <OrgShell>{children}</OrgShell>
}
