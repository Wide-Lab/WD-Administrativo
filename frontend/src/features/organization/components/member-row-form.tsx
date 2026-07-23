'use client'

import { useState } from 'react'

import { Button } from '#/components/ui/button'
import { MEMBERSHIP_STATUS_LABEL } from '#/features/context/lib/labels'
import type { OrganizationType } from '#/features/context/types'
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

/** Os controles de edição de um membro — papel e status.
 *
 *  ## A própria linha não tem controle, e desta vez isso não é um cadeado pintado
 *
 *  Enquanto a regra não existia no backend, esconder os controles aqui teria sido pior que
 *  mostrá-los: sumiria no primeiro `curl` e faria todo mundo achar que o caso estava tratado. A
 *  tela então marcava a linha e **nomeava a consequência** num diálogo de confirmação, que era o
 *  máximo que lhe cabia honestamente.
 *
 *  O `UpdateMembershipUseCase` passou a recusar a auto-edição com 422 — papel e status, porque
 *  `members.write` só existe em papel de administrador e toda mudança na própria linha é um
 *  rebaixamento ou uma desativação. Só **por causa disso** os controles somem daqui: o que a
 *  tela esconde agora é algo que o backend nega, que é a única condição em que esconder é
 *  informar em vez de mentir. A frase no lugar deles diz para onde ir, porque "não pode" sem
 *  saída é o que faz alguém tentar de novo.
 *
 *  O diálogo de confirmação foi junto: ele existia pra pesar um risco que hoje não é possível
 *  correr. */
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
  const update = useUpdateMember(member.organization_id)

  const isDirty = values.role !== member.role || values.status !== member.status

  function handleSubmit() {
    const parsed = updateMemberSchema.safeParse(values)
    if (!parsed.success) return

    update.mutate({ membershipId: member.id, input: parsed.data })
  }

  if (isSelf) {
    return (
      <p className="text-right text-sm text-muted">Só outro administrador edita o seu vínculo.</p>
    )
  }

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
    </div>
  )
}
