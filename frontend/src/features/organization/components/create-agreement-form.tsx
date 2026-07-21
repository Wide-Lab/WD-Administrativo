'use client'

import { useState, type FormEvent } from 'react'

import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import { createAgreementErrorMessage } from '#/features/organization/lib/organization-error'
import { createAgreementSchema } from '#/features/organization/schema'
import { useCreateAgreement } from '#/features/organization/use-agreements'

/** Conveniar um Parceiro.
 *
 *  **O campo é um UUID colado, e isso é um limite do backend, não preguiça da tela.** Não existe
 *  rota que liste os Parceiros disponíveis pra uma Empresa: `GET /organizacoes` é
 *  `organizations.read`, capability de `platform_admin`. A ergonomia certa — buscar Parceiro por
 *  nome ou documento — é **rota nova**, e é o segundo achado da spec `frontend/08`. Enquanto ela
 *  não existe, o honesto é dizer de onde o id vem em vez de fingir um autocomplete que
 *  consultaria uma rota que ninguém pode chamar. */
export function CreateAgreementForm({ orgId }: { orgId: string }) {
  const [partnerId, setPartnerId] = useState('')
  const [fieldError, setFieldError] = useState<string | undefined>(undefined)
  const create = useCreateAgreement(orgId)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const parsed = createAgreementSchema.safeParse({ partner_id: partnerId })
    if (!parsed.success) {
      setFieldError(parsed.error.flatten().fieldErrors.partner_id?.[0])
      return
    }

    setFieldError(undefined)
    create.mutate(parsed.data, { onSuccess: () => setPartnerId('') })
  }

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="space-y-4 rounded-lg border border-line bg-surface p-4"
    >
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-80 flex-1 space-y-2">
          <Label htmlFor="partner-id">Identificador do parceiro</Label>
          <Input
            id="partner-id"
            type="text"
            autoComplete="off"
            placeholder="01890000-0000-7000-8000-000000000000"
            className="font-mono text-xs"
            value={partnerId}
            onChange={(event) => {
              setPartnerId(event.target.value)
              setFieldError(undefined)
              if (create.isError) create.reset()
            }}
            aria-invalid={fieldError !== undefined}
            aria-describedby={fieldError ? 'partner-id-error' : 'partner-id-hint'}
            disabled={create.isPending}
          />
        </div>

        <Button type="submit" disabled={create.isPending}>
          {create.isPending ? 'Conveniando…' : 'Conveniar parceiro'}
        </Button>
      </div>

      {fieldError ? (
        <p id="partner-id-error" className="text-sm text-danger">
          {fieldError}
        </p>
      ) : (
        <p id="partner-id-hint" className="text-sm text-muted">
          Peça este identificador ao parceiro, ou à Widelab. Ainda não há busca por nome — ela
          depende de uma rota que o backend não tem.
        </p>
      )}

      {create.isError ? (
        <p role="alert" className="text-sm text-danger">
          {createAgreementErrorMessage(create.error)}
        </p>
      ) : null}
    </form>
  )
}
