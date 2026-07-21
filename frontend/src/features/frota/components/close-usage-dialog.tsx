'use client'

import { useState, type FormEvent } from 'react'

import { Button } from '#/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '#/components/ui/dialog'
import { Input } from '#/components/ui/input'
import { useOrgId } from '#/features/context/use-org-context'
import { Field, fieldProps } from '#/features/frota/components/field'
import { translateCloseUsageError } from '#/features/frota/lib/frota-error'
import { formatDateTime, nowForInput } from '#/features/frota/lib/labels'
import { closeUsageFormSchema } from '#/features/frota/schema'
import type { CloseUsageFormState, Usage } from '#/features/frota/types'
import { useCloseUsage } from '#/features/frota/use-frota'

type FieldErrors = Partial<Record<keyof CloseUsageFormState, string>>

/**
 * Encerrar viagem — **ação própria, não edição**.
 *
 * `POST /usos/{id}/encerrar` existe porque os dois campos vão juntos, e é por isso que este
 * diálogo tem exatamente dois. Deixar isso cair no `PATCH` genérico devolveria ao usuário a
 * chance de encerrar pela metade — que é o que a rota própria existe pra impedir, e o que o
 * `ck_vehicle_usages_closed_together` recusaria no banco de qualquer forma.
 *
 * Os dois campos são **obrigatórios** aqui, e opcionais-em-par no formulário de lançamento: são
 * schemas diferentes porque são gestos diferentes.
 */
export function CloseUsageDialog({ usage }: { usage: Usage }) {
  const orgId = useOrgId()
  const [open, setOpen] = useState(false)
  const [values, setValues] = useState<CloseUsageFormState>({
    endedAt: nowForInput(),
    endOdometer: '',
  })
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const close = useCloseUsage(orgId)

  function update<K extends keyof CloseUsageFormState>(field: K, value: CloseUsageFormState[K]) {
    setValues((current) => ({ ...current, [field]: value }))
    setFieldErrors((current) => ({ ...current, [field]: undefined }))
    setFormError(null)
  }

  function handleOpenChange(next: boolean) {
    setOpen(next)
    if (!next) {
      setValues({ endedAt: nowForInput(), endOdometer: '' })
      setFieldErrors({})
      setFormError(null)
      close.reset()
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const parsed = closeUsageFormSchema.safeParse(values)
    if (!parsed.success) {
      const { fieldErrors: errors } = parsed.error.flatten()
      setFieldErrors({
        endedAt: errors.endedAt?.[0],
        endOdometer: errors.endOdometer?.[0],
      })
      return
    }

    setFieldErrors({})
    close.mutate(
      { usageId: usage.id, values: parsed.data },
      {
        onSuccess: () => handleOpenChange(false),
        onError: (error) => {
          const translated = translateCloseUsageError(error)
          if (translated.field === null) {
            setFormError(translated.message)
            return
          }
          setFieldErrors({ [translated.field]: translated.message })
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="secondary" size="sm">
          Encerrar
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Encerrar viagem</DialogTitle>
          <DialogDescription>
            Saída em {formatDateTime(usage.started_at)}, com{' '}
            {usage.start_odometer.toLocaleString('pt-BR')} km.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {formError ? (
            <p
              role="alert"
              className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-text"
            >
              {formError}
            </p>
          ) : null}

          <Field id="closeEndedAt" label="Chegada" error={fieldErrors.endedAt}>
            <Input
              {...fieldProps('closeEndedAt', fieldErrors.endedAt)}
              type="datetime-local"
              value={values.endedAt}
              onChange={(event) => update('endedAt', event.target.value)}
              disabled={close.isPending}
            />
          </Field>

          <Field id="closeEndOdometer" label="Hodômetro de chegada" error={fieldErrors.endOdometer}>
            <Input
              {...fieldProps('closeEndOdometer', fieldErrors.endOdometer)}
              type="number"
              inputMode="numeric"
              min={usage.start_odometer}
              placeholder="Ex.: 45355"
              value={values.endOdometer}
              onChange={(event) => update('endOdometer', event.target.value)}
              disabled={close.isPending}
            />
          </Field>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={close.isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={close.isPending}>
              {close.isPending ? 'Encerrando…' : 'Encerrar viagem'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
