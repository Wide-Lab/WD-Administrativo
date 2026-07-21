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
import { INVITATION_STATUS_LABEL, ROLE_LABEL } from '#/features/context/lib/labels'
import { ConfirmDialog } from '#/features/organization/components/confirm-dialog'
import { Pager } from '#/features/organization/components/pager'
import { actionFor } from '#/features/organization/lib/invitation-status'
import { revokeInvitationErrorMessage } from '#/features/organization/lib/organization-error'
import type { Invitation, InvitationStatus } from '#/features/organization/types'
import { useInvitations, useRevokeInvitation } from '#/features/organization/use-invitations'

const PAGE_SIZE = 20

const STATUS_VARIANT: Record<InvitationStatus, 'success' | 'warning' | 'muted' | 'danger'> = {
  pending: 'warning',
  accepted: 'success',
  revoked: 'muted',
  expired: 'muted',
}

/** A fila de quem foi chamado e ainda não entrou.
 *
 *  ## Por que não há "copiar link" aqui
 *
 *  Porque **a resposta não traz o token**, e a ausência é o contrato, não uma limitação a
 *  contornar. O `InvitationResponse` foi desenhado sem ele (`backend/06`): o token é credencial
 *  do convidado e sai por e-mail **pra ele**. Devolvê-lo a quem convidou deixaria um `hr` aceitar
 *  no lugar da pessoa, e o e-mail deixaria de ser a prova de que quem aceitou controla a caixa.
 *
 *  Então não "conserte" isto adicionando um botão de copiar: não há o que copiar, e fazer o
 *  backend devolver o token pra alimentá-lo destruiria a única garantia que o fluxo de aceite
 *  tem. Quem precisa do link de novo revoga e convida outra vez — token novo, que é o certo,
 *  porque o token é de uso único.
 *
 *  ## O status vem pronto
 *
 *  Cada item chega com o status **efetivo**: um convite vencido é `expired` mesmo com a coluna
 *  em `pending`. A tela exibe o que recebeu e **não** compara `expires_at` com o relógio do
 *  navegador — seria a terceira escrita de uma regra que o backend já mantém duas vezes (Python
 *  e SQL), e a única das três rodando num relógio que o servidor não controla. É isso que faz o
 *  critério 5 valer com o relógio da máquina adiantado. */
export function InvitationsTable({
  orgId,
  status,
  onReinvite,
}: {
  orgId: string
  status: InvitationStatus | null
  onReinvite: () => void
}) {
  const [page, setPage] = useState(1)
  const [pendingRevocation, setPendingRevocation] = useState<Invitation | null>(null)
  const { data, isPending, isError } = useInvitations(orgId, page, PAGE_SIZE, status)
  const revoke = useRevokeInvitation(orgId)

  if (isPending) {
    return (
      <div className="space-y-2" aria-busy="true">
        <span className="sr-only">Carregando os convites…</span>
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    )
  }

  if (isError) {
    return (
      <p role="alert" className="text-sm text-danger">
        Não foi possível carregar os convites desta organização. Recarregue a página.
      </p>
    )
  }

  if (data.items.length === 0) {
    return (
      <div className="rounded-lg border border-line bg-surface p-8 text-center">
        <p className="font-medium">
          {status === null
            ? 'Nenhum convite pendente'
            : `Nenhum convite com status "${INVITATION_STATUS_LABEL[status]}"`}
        </p>
        <p className="mx-auto mt-1 max-w-md text-sm text-muted">
          {status === null
            ? 'Todo mundo que foi chamado já respondeu. Convide alguém pelo formulário acima.'
            : 'Troque o filtro para ver os convites em outro estado.'}
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-line bg-surface">
      {revoke.isError ? (
        <p role="alert" className="border-b border-line px-4 py-3 text-sm text-danger">
          {revokeInvitationErrorMessage(revoke.error)}
        </p>
      ) : null}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="px-4">E-mail</TableHead>
            <TableHead>Papel</TableHead>
            <TableHead>Status</TableHead>
            <Can permission="invitations.write">
              <TableHead className="px-4 text-right">Ação</TableHead>
            </Can>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.items.map((invitation) => {
            const action = actionFor(invitation.status)

            return (
              <TableRow key={invitation.id}>
                <TableCell className="px-4 font-medium">{invitation.email}</TableCell>
                <TableCell>{ROLE_LABEL[invitation.role]}</TableCell>
                <TableCell>
                  <Badge variant={STATUS_VARIANT[invitation.status]}>
                    {INVITATION_STATUS_LABEL[invitation.status]}
                  </Badge>
                </TableCell>
                <Can permission="invitations.write">
                  <TableCell className="px-4 text-right">
                    {action === 'revoke' ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setPendingRevocation(invitation)}
                        disabled={revoke.isPending}
                      >
                        Revogar
                      </Button>
                    ) : null}
                    {action === 'reinvite' ? (
                      <Button type="button" variant="ghost" size="sm" onClick={onReinvite}>
                        Convidar de novo
                      </Button>
                    ) : null}
                    {/* `accepted` não ganha ação: aquele convite virou membro, e revogá-lo não
                        tiraria acesso nenhum. Tirar acesso é `members.write`, na outra aba. */}
                  </TableCell>
                </Can>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>

      <Pager page={page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />

      <ConfirmDialog
        open={pendingRevocation !== null}
        title="Revogar este convite?"
        description={
          <>
            <p>
              O convite de <span className="font-medium text-text">{pendingRevocation?.email}</span>{' '}
              deixa de valer imediatamente, e o link que já foi enviado para de funcionar.
            </p>
            {/* O diálogo diz que é terminal porque é: não há "reativar" do outro lado. */}
            <p className="mt-2">
              Isso não tem volta — um convite revogado não reativa. Para chamar a mesma pessoa de
              novo, convide outra vez: nasce um convite novo, com um link novo.
            </p>
          </>
        }
        confirmLabel="Revogar convite"
        destructive
        isPending={revoke.isPending}
        onCancel={() => setPendingRevocation(null)}
        onConfirm={() => {
          if (pendingRevocation === null) return
          revoke.mutate(pendingRevocation.id)
          setPendingRevocation(null)
        }}
      />
    </div>
  )
}
