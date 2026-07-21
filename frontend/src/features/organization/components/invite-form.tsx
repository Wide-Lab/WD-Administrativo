'use client'

import { useState, type FormEvent } from 'react'

import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import { rolesFor } from '#/features/context/lib/roles'
import type { OrganizationType } from '#/features/context/types'
import { RoleSelect } from '#/features/organization/components/role-select'
import { createInvitationErrorMessage } from '#/features/organization/lib/organization-error'
import { createInvitationSchema } from '#/features/organization/schema'
import type { CreateInvitationInput } from '#/features/organization/types'
import { useCreateInvitation } from '#/features/organization/use-invitations'

type FieldErrors = Partial<Record<keyof CreateInvitationInput, string>>

/** Convidar: e-mail e papel, e nada mais.
 *
 *  O papel é escolhido **antes** de a pessoa existir — é o desenho do convite (`backend/06`), e é
 *  o que separa este caminho do auto-cadastro de Parceiro. Não há campo de nome: quem tem conta
 *  já tem o seu, e quem não tem o informa ao aceitar.
 *
 *  Não há convite em lote nem importação de CSV: o `POST` é um e-mail por vez, e um lote traria
 *  resultado parcial (quais foram, quais falharam), que é contrato de backend novo. */
export function InviteForm({
  orgId,
  organizationType,
}: {
  orgId: string
  organizationType: OrganizationType
}) {
  // O papel default é o primeiro do tipo desta organização — nunca um papel fixo em código, que
  // seria inválido do outro lado (`hr` num Parceiro não existe).
  const defaultRole = rolesFor(organizationType)[0]!

  const [values, setValues] = useState<CreateInvitationInput>({ email: '', role: defaultRole })
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const invite = useCreateInvitation(orgId)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const parsed = createInvitationSchema.safeParse(values)
    if (!parsed.success) {
      const { fieldErrors: errors } = parsed.error.flatten()
      setFieldErrors({ email: errors.email?.[0], role: errors.role?.[0] })
      return
    }

    setFieldErrors({})
    invite.mutate(parsed.data, {
      // Some o e-mail e fica o papel: convidar cinco colaboradores seguidos é o caso comum, e
      // repor o papel a cada um seria trabalho que a tela criou sozinha.
      onSuccess: () => setValues((current) => ({ ...current, email: '' })),
    })
  }

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="space-y-4 rounded-lg border border-line bg-surface p-4"
    >
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-64 flex-1 space-y-2">
          <Label htmlFor="invite-email">E-mail</Label>
          <Input
            id="invite-email"
            type="email"
            inputMode="email"
            autoComplete="off"
            placeholder="pessoa@empresa.com"
            value={values.email}
            onChange={(event) => {
              setValues((current) => ({ ...current, email: event.target.value }))
              setFieldErrors((current) => ({ ...current, email: undefined }))
              if (invite.isError) invite.reset()
            }}
            aria-invalid={fieldErrors.email !== undefined}
            aria-describedby={fieldErrors.email ? 'invite-email-error' : undefined}
            disabled={invite.isPending}
          />
        </div>

        <div className="min-w-44 space-y-2">
          <Label htmlFor="invite-role">Papel</Label>
          <RoleSelect
            id="invite-role"
            organizationType={organizationType}
            value={values.role}
            onValueChange={(role) => setValues((current) => ({ ...current, role }))}
            disabled={invite.isPending}
          />
        </div>

        <Button type="submit" disabled={invite.isPending}>
          {invite.isPending ? 'Convidando…' : 'Convidar'}
        </Button>
      </div>

      {fieldErrors.email ? (
        <p id="invite-email-error" className="text-sm text-danger">
          {fieldErrors.email}
        </p>
      ) : null}

      {invite.isError ? (
        <p role="alert" className="text-sm text-danger">
          {createInvitationErrorMessage(invite.error)}
        </p>
      ) : null}

      {invite.isSuccess ? (
        // O convite foi criado e o e-mail saiu; o link **não** aparece aqui, e o motivo está no
        // `invitations-table.tsx`.
        <p role="status" className="text-sm text-success">
          Convite enviado. Ele aparece na lista abaixo enquanto estiver pendente.
        </p>
      ) : null}
    </form>
  )
}
