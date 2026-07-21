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
import { useSession } from '#/features/auth/use-session'
import { Can } from '#/features/context/components/can'
import { MEMBERSHIP_STATUS_LABEL, ROLE_LABEL } from '#/features/context/lib/labels'
import type { OrganizationType } from '#/features/context/types'
import { MemberRowForm } from '#/features/organization/components/member-row-form'
import { Pager } from '#/features/organization/components/pager'
import { useMembers } from '#/features/organization/use-members'

const PAGE_SIZE = 20

/** Quem tem acesso a esta organização.
 *
 *  **A coluna "Pessoa" mostra um id, e isso é uma lacuna do backend, não desta tela.** A
 *  `MemberResponse` devolve `user_id` e mais nada de identidade — não existe rota que traduza id
 *  de usuário em nome/e-mail (`/api/me` responde sobre quem pergunta, e o `/me/contexto`
 *  também). O efeito colateral é torto de propósito e vale registrar: **o e-mail de quem foi
 *  convidado aparece na aba ao lado, e some quando a pessoa aceita** — vira membro e perde o
 *  nome. Espelhar aqui o e-mail do convite não resolveria: o convite não devolve `user_id`, e o
 *  cruzamento seria um palpite. Ver o `Como ficou` da spec. */
export function MembersTable({
  orgId,
  organizationType,
  onInvite,
}: {
  orgId: string
  organizationType: OrganizationType
  onInvite: () => void
}) {
  const [page, setPage] = useState(1)
  const { data, isPending, isError } = useMembers(orgId, page, PAGE_SIZE)
  const { user } = useSession()

  if (isPending) {
    return (
      <div className="space-y-2" aria-busy="true">
        <span className="sr-only">Carregando os membros…</span>
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    )
  }

  if (isError) {
    return (
      <p role="alert" className="text-sm text-danger">
        Não foi possível carregar os membros desta organização. Recarregue a página.
      </p>
    )
  }

  if (data.items.length === 0) {
    return (
      <div className="rounded-lg border border-line bg-surface p-8 text-center">
        <p className="font-medium">Nenhum membro por aqui ainda</p>
        {/* O estado vazio diz o que o produto decidiu: criar membro é convite, não cadastro. */}
        <p className="mx-auto mt-1 max-w-md text-sm text-muted">
          Ninguém entra nesta organização por cadastro direto — quem entra é convidado, e vira
          membro ao aceitar.
        </p>
        <Can permission="invitations.write">
          <Button type="button" className="mt-4" onClick={onInvite}>
            Convidar alguém
          </Button>
        </Can>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-line bg-surface">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="px-4">Pessoa</TableHead>
            <TableHead>Papel</TableHead>
            <TableHead>Status</TableHead>
            <Can permission="members.write">
              <TableHead className="px-4 text-right">Editar</TableHead>
            </Can>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.items.map((member) => {
            const isSelf = user !== null && member.user_id === user.id

            return (
              <TableRow key={member.id}>
                <TableCell className="px-4">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-muted">{member.user_id}</span>
                    {isSelf ? <Badge variant="primary">Você</Badge> : null}
                  </div>
                </TableCell>
                <TableCell>{ROLE_LABEL[member.role]}</TableCell>
                <TableCell>
                  <Badge variant={member.status === 'active' ? 'success' : 'muted'}>
                    {MEMBERSHIP_STATUS_LABEL[member.status]}
                  </Badge>
                </TableCell>
                {/* Quem tem `members.read` e não `members.write` — o caso do `hr` — vê a lista
                    inteira e nenhum controle. Quem nega de verdade é o backend. */}
                <Can permission="members.write">
                  <TableCell className="px-4">
                    <MemberRowForm
                      member={member}
                      organizationType={organizationType}
                      isSelf={isSelf}
                    />
                  </TableCell>
                </Can>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>

      <Pager page={page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
    </div>
  )
}
