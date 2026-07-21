'use client'

import { useState } from 'react'

import { Button } from '#/components/ui/button'
import { MEMBERSHIP_STATUS_LABEL } from '#/features/context/lib/labels'
import type { OrganizationType } from '#/features/context/types'
import { ConfirmDialog } from '#/features/organization/components/confirm-dialog'
import { RoleSelect } from '#/features/organization/components/role-select'
import { updateMemberErrorMessage } from '#/features/organization/lib/organization-error'
import { membershipStatusSchema, updateMemberSchema } from '#/features/organization/schema'
import type { Member, MembershipStatus, UpdateMemberInput } from '#/features/organization/types'
import { useUpdateMember } from '#/features/organization/use-update-member'
import { cn } from '#/lib/utils'

const selectClassName = cn(
  'flex h-9 w-full rounded-md border border-line bg-surface px-2 text-sm text-text',
  'focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
  'disabled:cursor-not-allowed disabled:opacity-50',
)

/** A consequência de editar a **própria** linha, dita por extenso.
 *
 *  Duas frases porque são dois estragos diferentes: perder o papel é perder capabilities (e
 *  possivelmente esta tela), desativar o vínculo é perder a organização inteira. */
function selfEditWarning(next: UpdateMemberInput, current: Member): string | null {
  if (next.status === 'disabled' && current.status !== 'disabled') {
    return 'Você está desativando o seu próprio vínculo com esta organização. Ao confirmar, você perde o acesso a ela — inclusive a esta tela. Só outro administrador, ou a Widelab, consegue reativá-lo.'
  }

  if (next.role !== current.role) {
    return 'Você está mudando o seu próprio papel nesta organização. Se o papel novo não administrar membros, você perde o acesso a esta tela ao confirmar — e voltar atrás depende de outro administrador, ou da Widelab.'
  }

  return null
}

/** Os controles de edição de um membro — papel e status.
 *
 *  ## Por que não há `if (membership.id === meuId) return` aqui
 *
 *  Porque seria um cadeado pintado, e a spec (`frontend/08`) decidiu não pintá-lo. O
 *  `UpdateMembershipUseCase` **não guarda nada** além de papel×tipo: um `company_admin` pode se
 *  rebaixar pra `collaborator` ou desativar o próprio vínculo, e a organização fica sem quem a
 *  administre — sem erro e sem caminho de volta que não seja `platform_admin` ou CLI. Vale igual
 *  pro último `partner_admin`.
 *
 *  Um `return` nesta linha **pareceria** proteção e sumiria no primeiro `curl`, com o efeito
 *  colateral de fazer todo mundo achar que o caso está tratado — que é exatamente o que a regra
 *  do `Can` diz sobre esconder botão sem `require_permission` do outro lado. O conserto de
 *  verdade é regra de domínio (422 no auto-rebaixamento e na remoção do último administrador
 *  ativo) e é **spec de backend**, achada ao escrever a de frontend. Não "conserte" isto aqui:
 *  fechar o buraco na tela é o que faria ninguém fechá-lo onde ele existe.
 *
 *  O que esta tela faz é o que lhe cabe: marca a própria linha e **nomeia a consequência** antes
 *  de agir. Confirmação é honestidade sobre um risco real, não guard. */
export function MemberRowForm({
  member,
  organizationType,
  isSelf,
}: {
  member: Member
  organizationType: OrganizationType
  isSelf: boolean
}) {
  const [values, setValues] = useState<UpdateMemberInput>({
    role: member.role,
    status: member.status,
  })
  const [pendingConfirmation, setPendingConfirmation] = useState<UpdateMemberInput | null>(null)
  const update = useUpdateMember(member.organization_id)

  const isDirty = values.role !== member.role || values.status !== member.status

  function apply(input: UpdateMemberInput) {
    update.mutate({ membershipId: member.id, input })
  }

  function handleSubmit() {
    const parsed = updateMemberSchema.safeParse(values)
    if (!parsed.success) return

    // A confirmação é só sobre si mesmo — e ela não decide nada, só pergunta.
    if (isSelf && selfEditWarning(parsed.data, member) !== null) {
      setPendingConfirmation(parsed.data)
      return
    }

    apply(parsed.data)
  }

  const warning = pendingConfirmation === null ? null : selfEditWarning(pendingConfirmation, member)

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <label className="sr-only" htmlFor={`role-${member.id}`}>
          Papel
        </label>
        <RoleSelect
          id={`role-${member.id}`}
          organizationType={organizationType}
          value={values.role}
          onValueChange={(role) => setValues((current) => ({ ...current, role }))}
          disabled={update.isPending}
          className="h-9 w-auto min-w-36"
        />

        <label className="sr-only" htmlFor={`status-${member.id}`}>
          Status
        </label>
        <select
          id={`status-${member.id}`}
          value={values.status}
          onChange={(event) =>
            setValues((current) => ({
              ...current,
              status: event.target.value as MembershipStatus,
            }))
          }
          disabled={update.isPending}
          className={cn(selectClassName, 'w-auto min-w-32')}
        >
          {membershipStatusSchema.options.map((status) => (
            <option key={status} value={status}>
              {MEMBERSHIP_STATUS_LABEL[status]}
            </option>
          ))}
        </select>

        {/* Só aparece havendo mudança: um botão sempre aceso convida a salvar o que já está
            salvo, e cada clique desses é um `PATCH` que o backend atende. */}
        {isDirty ? (
          <Button type="button" size="sm" onClick={handleSubmit} disabled={update.isPending}>
            {update.isPending ? 'Salvando…' : 'Salvar'}
          </Button>
        ) : null}
      </div>

      {update.isError ? (
        <p role="alert" className="text-sm text-danger">
          {updateMemberErrorMessage(update.error)}
        </p>
      ) : null}

      <ConfirmDialog
        open={pendingConfirmation !== null}
        title="Você está editando o seu próprio acesso"
        description={warning ?? ''}
        confirmLabel="Editar mesmo assim"
        destructive
        isPending={update.isPending}
        onCancel={() => setPendingConfirmation(null)}
        onConfirm={() => {
          if (pendingConfirmation === null) return
          apply(pendingConfirmation)
          setPendingConfirmation(null)
        }}
      />
    </div>
  )
}
