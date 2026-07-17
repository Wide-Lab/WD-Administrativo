'use client'

import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import { PASSWORD_MIN_LENGTH } from '#/features/auth/schema'
import type { PasswordFieldValues } from '#/features/auth/types'

type PasswordFieldsProps = {
  values: PasswordFieldValues
  errors: Partial<Record<keyof PasswordFieldValues, string>>
  onChange: (field: keyof PasswordFieldValues, value: string) => void
  disabled?: boolean
  /** "Senha" no onboarding; "Nova senha" na troca de senha logada, que tem também a atual. */
  label?: string
  /** Prefixa os `id`s. Existe pro dia em que uma tela pintar dois grupos (a troca de senha, com
   *  a atual e a nova): dois `id="password"` na mesma página quebram o `<Label htmlFor>`. */
  idPrefix?: string
}

/** Os campos de definir senha, num lugar só — o `Reuso` que a spec 06 pede entre
 *  `/convites/[token]`, `/parceiros/cadastro` e a troca de senha logada.
 *
 *  Controlado pelo formulário de fora (mesmo desenho do `LoginForm`): quem valida é a
 *  `passwordFieldsShape` do schema, e o componente só pinta o veredito. Deixar o estado aqui
 *  dentro obrigaria cada tela a pescá-lo de volta pra montar o payload.
 *
 *  Não há medidor de força — a spec o marca "opcional", e um medidor mede o que a política não
 *  cobra: hoje o backend exige comprimento, e uma barra dizendo "fraca" numa senha que ele
 *  aceita ensina uma regra que não existe. */
export function PasswordFields({
  values,
  errors,
  onChange,
  disabled = false,
  label = 'Senha',
  idPrefix = '',
}: PasswordFieldsProps) {
  const passwordId = `${idPrefix}password`
  const confirmationId = `${idPrefix}password-confirmation`
  const hintId = `${idPrefix}password-hint`

  return (
    <>
      <div className="space-y-2">
        <Label htmlFor={passwordId}>{label}</Label>
        <Input
          id={passwordId}
          type="password"
          // `new-password` (e não `current-password`) é o que faz o gerenciador de senhas
          // oferecer uma nova em vez de tentar completar com uma antiga.
          autoComplete="new-password"
          value={values.password}
          onChange={(event) => onChange('password', event.target.value)}
          aria-invalid={errors.password !== undefined}
          aria-describedby={errors.password ? `${passwordId}-error` : hintId}
          disabled={disabled}
        />
        {errors.password ? (
          <p id={`${passwordId}-error`} className="text-sm text-danger">
            {errors.password}
          </p>
        ) : (
          <p id={hintId} className="text-sm text-muted">
            Pelo menos {PASSWORD_MIN_LENGTH} caracteres.
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor={confirmationId}>Confirmar {label.toLowerCase()}</Label>
        <Input
          id={confirmationId}
          type="password"
          autoComplete="new-password"
          value={values.passwordConfirmation}
          onChange={(event) => onChange('passwordConfirmation', event.target.value)}
          aria-invalid={errors.passwordConfirmation !== undefined}
          aria-describedby={errors.passwordConfirmation ? `${confirmationId}-error` : undefined}
          disabled={disabled}
        />
        {errors.passwordConfirmation ? (
          <p id={`${confirmationId}-error`} className="text-sm text-danger">
            {errors.passwordConfirmation}
          </p>
        ) : null}
      </div>
    </>
  )
}
