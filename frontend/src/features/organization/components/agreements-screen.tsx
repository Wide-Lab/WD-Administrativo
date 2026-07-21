'use client'

import { useState } from 'react'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Skeleton } from '#/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import { Can } from '#/features/context/components/can'
import { AGREEMENT_STATUS_LABEL } from '#/features/context/lib/labels'
import type { OrganizationType } from '#/features/context/types'
import { useOrgContext, useOrgId } from '#/features/context/use-org-context'
import { AccessDenied } from '#/features/organization/components/access-denied'
import { CreateAgreementForm } from '#/features/organization/components/create-agreement-form'
import { Pager } from '#/features/organization/components/pager'
import { updateAgreementErrorMessage } from '#/features/organization/lib/organization-error'
import { useAgreements, useUpdateAgreement } from '#/features/organization/use-agreements'

const PAGE_SIZE = 20

/** Uma tela, dois sentidos de leitura. O `GET .../convenios` é o mesmo dos dois lados — serve à
 *  Empresa e ao Parceiro —, e só o rótulo sabe de que lado se está. */
const COPY: Record<'company' | 'partner', { title: string; description: string; column: string }> =
  {
    company: {
      title: 'Parceiros',
      description: 'Os parceiros conveniados com esta empresa.',
      column: 'Parceiro',
    },
    partner: {
      title: 'Empresas atendidas',
      description: 'As empresas que mantêm convênio com você.',
      column: 'Empresa',
    },
  }

function AgreementsTable({ orgId, side }: { orgId: string; side: 'company' | 'partner' }) {
  const [page, setPage] = useState(1)
  const { data, isPending, isError } = useAgreements(orgId, page, PAGE_SIZE)
  const update = useUpdateAgreement(orgId)

  if (isPending) {
    return (
      <div className="space-y-2" aria-busy="true">
        <span className="sr-only">Carregando os convênios…</span>
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    )
  }

  if (isError) {
    return (
      <p role="alert" className="text-sm text-danger">
        Não foi possível carregar os convênios. Recarregue a página.
      </p>
    )
  }

  if (data.items.length === 0) {
    return (
      <div className="rounded-lg border border-line bg-surface p-8 text-center">
        <p className="font-medium">Nenhum convênio ainda</p>
        <p className="mx-auto mt-1 max-w-md text-sm text-muted">
          {side === 'company'
            ? 'Convenie um parceiro para que ele passe a atender esta empresa.'
            : 'Quando uma empresa conveniar você, ela aparece aqui. Conveniar é ato da empresa — não há como pedir daqui.'}
        </p>
      </div>
    )
  }

  // Numa Empresa a coluna interessante é o Parceiro; num Parceiro, a Empresa. Mesmo dado, lado
  // oposto da linha.
  const counterpartOf = (agreement: { company_id: string; partner_id: string }) =>
    side === 'company' ? agreement.partner_id : agreement.company_id

  return (
    <div className="rounded-lg border border-line bg-surface">
      {update.isError ? (
        <p role="alert" className="border-b border-line px-4 py-3 text-sm text-danger">
          {updateAgreementErrorMessage(update.error)}
        </p>
      ) : null}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="px-4">{COPY[side].column}</TableHead>
            <TableHead>Status</TableHead>
            <Can permission="agreements.write">
              <TableHead className="px-4 text-right">Ação</TableHead>
            </Can>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.items.map((agreement) => (
            <TableRow key={agreement.id}>
              <TableCell className="px-4 font-mono text-xs text-muted">
                {counterpartOf(agreement)}
              </TableCell>
              <TableCell>
                <Badge variant={agreement.status === 'active' ? 'success' : 'warning'}>
                  {AGREEMENT_STATUS_LABEL[agreement.status]}
                </Badge>
              </TableCell>
              {/* `agreements.write` só o `company_admin` tem — nem `platform_admin`. Num Parceiro
                  este `Can` nunca abre, e é o que faz a tela dele ser leitura pura sem um `if`
                  de persona: quem decide é a capability que o vínculo dá. */}
              <Can permission="agreements.write">
                <TableCell className="px-4 text-right">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={update.isPending}
                    onClick={() =>
                      update.mutate({
                        agreementId: agreement.id,
                        status: agreement.status === 'active' ? 'suspended' : 'active',
                      })
                    }
                  >
                    {agreement.status === 'active' ? 'Suspender' : 'Reativar'}
                  </Button>
                </TableCell>
              </Can>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Pager page={page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
    </div>
  )
}

/** Os convênios da organização ativa.
 *
 *  A rota `GET .../convenios` **não exige capability** — só o vínculo —, então nada aqui é
 *  negado pelo backend por papel. O recorte por persona abaixo é ergonomia declarada: convênio é
 *  assunto de quem administra a organização, e um `collaborator` que digite a URL alcança o dado
 *  do mesmo jeito. Ver `KERNEL_NAV` em `features/context/nav.ts`. */
export function AgreementsScreen() {
  const orgId = useOrgId()
  const { organization, persona, isLoading } = useOrgContext()

  if (isLoading || organization === null || persona === null) return null

  const side: OrganizationType = organization.type

  if (side !== 'company' && side !== 'partner') {
    return (
      <AccessDenied
        title="Esta organização não mantém convênios"
        description="Convênio liga uma Empresa a um Parceiro. A organização da Plataforma não é nenhum dos dois."
      />
    )
  }

  if (persona === 'collaborator') {
    return (
      <AccessDenied
        title="Esta tela não é sua"
        description="Os convênios da sua empresa são assunto de quem a administra. Os serviços que eles habilitam aparecem no seu menu."
      />
    )
  }

  const copy = COPY[side]

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{copy.title}</h1>
        <p className="text-sm text-muted">{copy.description}</p>
      </div>

      {/* Num Parceiro isto nunca renderiza, e não há botão "pedir convênio" em lugar nenhum:
          conveniar é ato da Empresa (`backend/03`), e um botão que só produz 403 é pior que a
          ausência dele. */}
      <Can permission="agreements.write">
        <CreateAgreementForm orgId={orgId} />
      </Can>

      <AgreementsTable orgId={orgId} side={side} />
    </div>
  )
}
