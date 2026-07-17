'use client'

import { useState, type FormEvent } from 'react'

import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import { PasswordFields } from '#/features/auth/components/password-fields'
import { acceptInvitationErrorMessage } from '#/features/onboarding/lib/onboarding-error'
import { acceptInvitationSchema } from '#/features/onboarding/schema'
import type { AcceptInvitationInput, PublicInvitation } from '#/features/onboarding/types'
import { useAcceptInvitation } from '#/features/onboarding/use-accept-invitation'

type FieldErrors = Partial<Record<keyof AcceptInvitationInput, string>>

/** O formulário que transforma um convite numa sessão.
 *
 *  Ele pergunta nome e senha **sempre**, inclusive a quem já tem conta — e é assim que o
 *  critério 4 se cumpre nesta tela: a alternativa (pedir só a senha de quem é novo) exigiria
 *  saber quem é novo, e essa pergunta não tem resposta aqui, de propósito. O backend ignora a
 *  senha quando a conta existe, e é ele quem carrega essa decisão (backend 06). */
export function AcceptInvitationForm({
  token,
  invitation,
}: {
  token: string
  invitation: PublicInvitation
}) {
  const [values, setValues] = useState<AcceptInvitationInput>({
    name: '',
    password: '',
    passwordConfirmation: '',
  })
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const accept = useAcceptInvitation(token)

  function update<K extends keyof AcceptInvitationInput>(
    field: K,
    value: AcceptInvitationInput[K],
  ) {
    setValues((current) => ({ ...current, [field]: value }))
    setFieldErrors((current) => ({ ...current, [field]: undefined }))
    if (accept.isError) accept.reset()
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const parsed = acceptInvitationSchema.safeParse(values)
    if (!parsed.success) {
      const { fieldErrors: errors } = parsed.error.flatten()
      setFieldErrors({
        name: errors.name?.[0],
        password: errors.password?.[0],
        passwordConfirmation: errors.passwordConfirmation?.[0],
      })
      return
    }

    setFieldErrors({})
    accept.mutate(parsed.data)
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {accept.isError ? (
        <p
          role="alert"
          className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-text"
        >
          {acceptInvitationErrorMessage(accept.error)}
        </p>
      ) : null}

      {/* Read-only, não `disabled`: o convite é **deste** e-mail e não há o que escolher, mas o
          campo segue focalizável e legível por leitor de tela — e o `autoComplete="username"`
          faz o gerenciador de senhas guardar a senha nova sob a conta certa. */}
      <div className="space-y-2">
        <Label htmlFor="email">E-mail</Label>
        <Input
          id="email"
          type="email"
          name="email"
          autoComplete="username"
          value={invitation.email}
          readOnly
          aria-readonly
          className="text-muted"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="name">Nome</Label>
        <Input
          id="name"
          type="text"
          autoComplete="name"
          autoFocus
          placeholder="Como você quer ser chamado"
          value={values.name ?? ''}
          onChange={(event) => update('name', event.target.value)}
          aria-invalid={fieldErrors.name !== undefined}
          aria-describedby={fieldErrors.name ? 'name-error' : 'name-hint'}
          disabled={accept.isPending}
        />
        {fieldErrors.name ? (
          <p id="name-error" className="text-sm text-danger">
            {fieldErrors.name}
          </p>
        ) : (
          <p id="name-hint" className="text-sm text-muted">
            Opcional. Dá pra mudar depois.
          </p>
        )}
      </div>

      <PasswordFields
        values={values}
        errors={fieldErrors}
        onChange={update}
        disabled={accept.isPending}
      />

      {/* `isPending` segue verdadeiro depois do sucesso, enquanto o redirecionamento acontece. */}
      <Button type="submit" size="lg" className="w-full" disabled={accept.isPending}>
        {accept.isPending ? 'Entrando…' : 'Aceitar convite e entrar'}
      </Button>
    </form>
  )
}
