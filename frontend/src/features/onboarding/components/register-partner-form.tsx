'use client'

import Link from 'next/link'
import { useState, type FormEvent } from 'react'

import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import { PasswordFields } from '#/features/auth/components/password-fields'
import {
  isEmailConflict,
  registerPartnerErrorMessage,
} from '#/features/onboarding/lib/onboarding-error'
import { registerPartnerSchema } from '#/features/onboarding/schema'
import type { RegisterPartnerInput } from '#/features/onboarding/types'
import { useRegisterPartner } from '#/features/onboarding/use-register-partner'

type FieldErrors = Partial<Record<keyof RegisterPartnerInput, string>>

/** O auto-cadastro de Parceiro — o outro caminho de entrada, e o oposto do convite: aqui a
 *  pessoa chega sozinha, e a organização nasce com ela.
 *
 *  Cadastrar-se **não** dá acesso a Empresa nenhuma: quem liga um Parceiro a cada Empresa é o
 *  convênio, que segue sendo ato da Empresa (spec 03). É o que a descrição da tela diz, pra
 *  ninguém sair daqui esperando ver clientes. */
export function RegisterPartnerForm() {
  const [values, setValues] = useState<RegisterPartnerInput>({
    companyName: '',
    document: '',
    adminName: '',
    adminEmail: '',
    password: '',
    passwordConfirmation: '',
  })
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const register = useRegisterPartner()

  function update<K extends keyof RegisterPartnerInput>(field: K, value: RegisterPartnerInput[K]) {
    setValues((current) => ({ ...current, [field]: value }))
    setFieldErrors((current) => ({ ...current, [field]: undefined }))
    if (register.isError) register.reset()
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const parsed = registerPartnerSchema.safeParse(values)
    if (!parsed.success) {
      const { fieldErrors: errors } = parsed.error.flatten()
      setFieldErrors({
        companyName: errors.companyName?.[0],
        document: errors.document?.[0],
        adminName: errors.adminName?.[0],
        adminEmail: errors.adminEmail?.[0],
        password: errors.password?.[0],
        passwordConfirmation: errors.passwordConfirmation?.[0],
      })
      return
    }

    setFieldErrors({})
    register.mutate(parsed.data)
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {/* O 409 não limpa nada: o que a pessoa digitou continua na tela, e ela troca só o e-mail
          — ou entra com a conta que já tem. "Sem estado órfão" (critério 2) é isto do lado de
          cá; do lado de lá, é a transação do backend, que não deixa organização sem dono. */}
      {register.isError ? (
        <div
          role="alert"
          className="space-y-2 rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-text"
        >
          <p>{registerPartnerErrorMessage(register.error)}</p>
          {isEmailConflict(register.error) ? (
            <Link
              href="/entrar"
              className="inline-block font-medium text-primary-fg underline-offset-4 hover:underline"
            >
              Entrar com esta conta
            </Link>
          ) : null}
        </div>
      ) : null}

      <div className="space-y-2">
        <Label htmlFor="companyName">Nome do parceiro</Label>
        <Input
          id="companyName"
          type="text"
          autoComplete="organization"
          autoFocus
          placeholder="Restaurante Gomes"
          value={values.companyName}
          onChange={(event) => update('companyName', event.target.value)}
          aria-invalid={fieldErrors.companyName !== undefined}
          aria-describedby={fieldErrors.companyName ? 'companyName-error' : undefined}
          disabled={register.isPending}
        />
        {fieldErrors.companyName ? (
          <p id="companyName-error" className="text-sm text-danger">
            {fieldErrors.companyName}
          </p>
        ) : null}
      </div>

      <div className="space-y-2">
        <Label htmlFor="document">CNPJ</Label>
        <Input
          id="document"
          type="text"
          inputMode="numeric"
          placeholder="00.000.000/0000-00"
          value={values.document ?? ''}
          onChange={(event) => update('document', event.target.value)}
          aria-invalid={fieldErrors.document !== undefined}
          aria-describedby={fieldErrors.document ? 'document-error' : 'document-hint'}
          disabled={register.isPending}
        />
        {fieldErrors.document ? (
          <p id="document-error" className="text-sm text-danger">
            {fieldErrors.document}
          </p>
        ) : (
          // Opcional no backend, e sem máscara nem validação de dígito aqui: o campo é `document`
          // (texto livre) do lado de lá, e inventar a regra do CNPJ nesta tela criaria uma
          // verdade que o servidor não cobra.
          <p id="document-hint" className="text-sm text-muted">
            Opcional.
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="adminName">Seu nome</Label>
        <Input
          id="adminName"
          type="text"
          autoComplete="name"
          value={values.adminName}
          onChange={(event) => update('adminName', event.target.value)}
          aria-invalid={fieldErrors.adminName !== undefined}
          aria-describedby={fieldErrors.adminName ? 'adminName-error' : undefined}
          disabled={register.isPending}
        />
        {fieldErrors.adminName ? (
          <p id="adminName-error" className="text-sm text-danger">
            {fieldErrors.adminName}
          </p>
        ) : null}
      </div>

      <div className="space-y-2">
        <Label htmlFor="adminEmail">Seu e-mail</Label>
        <Input
          id="adminEmail"
          type="email"
          inputMode="email"
          autoComplete="username"
          placeholder="voce@parceiro.com"
          value={values.adminEmail}
          onChange={(event) => update('adminEmail', event.target.value)}
          aria-invalid={fieldErrors.adminEmail !== undefined}
          aria-describedby={fieldErrors.adminEmail ? 'adminEmail-error' : undefined}
          disabled={register.isPending}
        />
        {fieldErrors.adminEmail ? (
          <p id="adminEmail-error" className="text-sm text-danger">
            {fieldErrors.adminEmail}
          </p>
        ) : null}
      </div>

      <PasswordFields
        values={values}
        errors={fieldErrors}
        onChange={update}
        disabled={register.isPending}
      />

      <Button type="submit" size="lg" className="w-full" disabled={register.isPending}>
        {register.isPending ? 'Criando…' : 'Criar conta de parceiro'}
      </Button>
    </form>
  )
}
