'use client'

import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'

import { Button } from '#/components/ui/button'
import { Can } from '#/features/context/components/can'
import { INVITATION_STATUS_LABEL } from '#/features/context/lib/labels'
import { useOrgContext, useOrgId } from '#/features/context/use-org-context'
import { AccessDenied } from '#/features/organization/components/access-denied'
import { InvitationsTable } from '#/features/organization/components/invitations-table'
import { InviteForm } from '#/features/organization/components/invite-form'
import { MembersTable } from '#/features/organization/components/members-table'
import { parseStatusFilter, statusFilterHref } from '#/features/organization/lib/invitation-status'
import { invitationStatusSchema } from '#/features/organization/schema'
import { cn } from '#/lib/utils'

/** Membros e Convites são **a mesma pergunta em dois tempos** — quem tem acesso, e quem foi
 *  chamado e ainda não entrou —, então são abas de uma tela só e não dois itens de menu.
 *
 *  As abas vivem na URL (`?aba=`) em vez de num `useState`: a aba é estado navegável, e é o que
 *  faz o botão "Convidar" da lista de membros ser um link honesto, o voltar do navegador
 *  funcionar e a tela ser compartilhável — a mesma razão pela qual o filtro de status vai pro
 *  `?status=`, e o `orgId` pro path. */
type Tab = 'membros' | 'convites'

function parseTab(raw: string | null): Tab {
  return raw === 'convites' ? 'convites' : 'membros'
}

function TabLink({
  href,
  isActive,
  children,
}: {
  href: string
  isActive: boolean
  children: string
}) {
  return (
    <Link
      href={href}
      aria-current={isActive ? 'page' : undefined}
      className={cn(
        'border-b-2 px-1 pb-3 text-sm font-medium transition-colors',
        isActive
          ? 'border-primary text-text'
          : 'border-transparent text-muted hover:border-line hover:text-text',
      )}
    >
      {children}
    </Link>
  )
}

/** O filtro de status da aba Convites. Vai pra URL como `?status=`, igual ao backend — e a opção
 *  "Pendentes" é a **ausência** do parâmetro, não `?status=pending`: o default de devolver só os
 *  pendentes é do servidor, e reescrevê-lo aqui criaria uma segunda verdade sobre o mesmo. */
function StatusFilter({ current }: { current: ReturnType<typeof parseStatusFilter> }) {
  const pathname = usePathname()

  const options = [
    { value: null, label: 'Pendentes' },
    ...invitationStatusSchema.options.map((status) => ({
      value: status,
      label: INVITATION_STATUS_LABEL[status],
    })),
  ]

  return (
    <nav aria-label="Filtrar convites por status" className="flex flex-wrap gap-2">
      {options.map((option) => {
        const isActive = option.value === current

        return (
          <Link
            key={option.label}
            href={statusFilterHref(pathname, option.value)}
            aria-current={isActive ? 'true' : undefined}
            className={cn(
              'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
              isActive
                ? 'border-transparent bg-primary/15 text-primary-fg'
                : 'border-line bg-transparent text-muted hover:bg-surface-2 hover:text-text',
            )}
          >
            {option.label}
          </Link>
        )
      })}
    </nav>
  )
}

export function PeopleScreen() {
  const orgId = useOrgId()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { organization, permissions, isLoading } = useOrgContext()

  const tab = parseTab(searchParams.get('aba'))
  const status = parseStatusFilter(searchParams.get('status'))

  if (isLoading || organization === null) return null

  // O eco de uma negação **real**: sem `members.read` o `GET .../membros` responde 403. Um `hr`
  // sem `members.write` passa por aqui e vê a lista — o que ele não vê são os controles.
  if (!permissions.includes('members.read') && !permissions.includes('invitations.read')) {
    return (
      <AccessDenied
        title="Esta tela não é sua"
        description="Administrar as pessoas desta organização depende de um papel que o seu vínculo aqui não tem. Se isso parece errado, fale com quem administra a organização."
      />
    )
  }

  const goToInvites = () => router.push(`${pathname}?aba=convites`)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Pessoas</h1>
          <p className="text-sm text-muted">
            Quem tem acesso a {organization.name} e quem foi chamado e ainda não entrou.
          </p>
        </div>

        {/* O botão que as pessoas vão procurar chama-se "Convidar", e não "Adicionar", porque é
            o que o produto faz: criar membro é convite (`backend/06`), não cadastro direto. */}
        {tab === 'membros' ? (
          <Can permission="invitations.write">
            <Button type="button" onClick={goToInvites}>
              Convidar
            </Button>
          </Can>
        ) : null}
      </div>

      <div className="flex gap-6 border-b border-line">
        <TabLink href={pathname} isActive={tab === 'membros'}>
          Membros
        </TabLink>
        <TabLink href={`${pathname}?aba=convites`} isActive={tab === 'convites'}>
          Convites
        </TabLink>
      </div>

      {tab === 'membros' ? (
        permissions.includes('members.read') ? (
          <MembersTable orgId={orgId} organizationType={organization.type} onInvite={goToInvites} />
        ) : (
          <p className="text-sm text-muted">
            Você não tem permissão para ver os membros desta organização — só os convites.
          </p>
        )
      ) : (
        <div className="space-y-4">
          <Can permission="invitations.write">
            <InviteForm orgId={orgId} organizationType={organization.type} />
          </Can>
          <StatusFilter current={status} />
          <InvitationsTable orgId={orgId} status={status} onReinvite={goToInvites} />
        </div>
      )}
    </div>
  )
}
