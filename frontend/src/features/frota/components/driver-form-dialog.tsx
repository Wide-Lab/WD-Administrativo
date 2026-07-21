'use client'

import { useState, type FormEvent, type ReactNode } from 'react'

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
import { Select } from '#/components/ui/select'
import { useOrgContext, useOrgId } from '#/features/context/use-org-context'
import { Field, fieldProps } from '#/features/frota/components/field'
import { translateDriverError } from '#/features/frota/lib/frota-error'
import { DRIVER_STATUS_LABEL } from '#/features/frota/lib/labels'
import { MEMBERS_READ } from '#/features/frota/permissions'
import { driverFormSchema } from '#/features/frota/schema'
import type { Driver, DriverFormState, DriverStatus } from '#/features/frota/types'
import { useMembers, useSaveDriver } from '#/features/frota/use-frota'

type FieldErrors = Partial<Record<keyof DriverFormState, string>>

function stateFrom(driver?: Driver): DriverFormState {
  return {
    name: driver?.name ?? '',
    userId: driver?.user_id ?? '',
    licenseNumber: driver?.license_number ?? '',
    licenseCategory: driver?.license_category ?? '',
    licenseExpiresAt: driver?.license_expires_at ?? '',
    status: driver?.status ?? 'active',
  }
}

/**
 * Cadastro e edição de condutor.
 *
 * O campo que merece nota é `user_id`: é o vínculo opcional com quem tem login, e é ele que faz o
 * `frota.usages.write_own` funcionar. **"— sem vínculo —" é caso de primeira classe**, e não o
 * estado degenerado do campo: o motorista terceirizado dirige e nunca loga, e exigir login de todo
 * condutor forçaria cadastrar usuário-fantasma pra gente que não usa o sistema.
 *
 * Se quem abre a tela não tem `members.read`, o select degrada pra "sem vínculo" e um aviso — não
 * quebra. `manager` tem `drivers.write` e pode não ter `members.read`; são mapas diferentes
 * (`PERMISSIONS_BY_ROLE` × o `grants` do módulo) e nada os obriga a concordar.
 */
export function DriverFormDialog({ driver, trigger }: { driver?: Driver; trigger: ReactNode }) {
  const orgId = useOrgId()
  const { permissions } = useOrgContext()
  const canReadMembers = permissions.includes(MEMBERS_READ)
  const isEditing = driver !== undefined

  const [open, setOpen] = useState(false)
  const [values, setValues] = useState<DriverFormState>(() => stateFrom(driver))
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string | null>(null)

  const members = useMembers(orgId, { enabled: canReadMembers })
  const save = useSaveDriver(orgId)

  function update<K extends keyof DriverFormState>(field: K, value: DriverFormState[K]) {
    setValues((current) => ({ ...current, [field]: value }))
    setFieldErrors((current) => ({ ...current, [field]: undefined }))
    setFormError(null)
  }

  function handleOpenChange(next: boolean) {
    setOpen(next)
    if (!next) {
      setValues(stateFrom(driver))
      setFieldErrors({})
      setFormError(null)
      save.reset()
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const parsed = driverFormSchema.safeParse(values)
    if (!parsed.success) {
      const { fieldErrors: errors } = parsed.error.flatten()
      setFieldErrors({
        name: errors.name?.[0],
        userId: errors.userId?.[0],
        licenseNumber: errors.licenseNumber?.[0],
        licenseCategory: errors.licenseCategory?.[0],
        licenseExpiresAt: errors.licenseExpiresAt?.[0],
        status: errors.status?.[0],
      })
      return
    }

    setFieldErrors({})
    save.mutate(
      { driverId: driver?.id, values: parsed.data },
      {
        onSuccess: () => handleOpenChange(false),
        onError: (error) => {
          const translated = translateDriverError(error)
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
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Editar condutor' : 'Cadastrar condutor'}</DialogTitle>
          <DialogDescription>
            Condutor não precisa ter login: o motorista terceirizado dirige e nunca acessa o
            sistema.
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

          <Field id="driverName" label="Nome" error={fieldErrors.name}>
            <Input
              {...fieldProps('driverName', fieldErrors.name)}
              type="text"
              autoComplete="name"
              value={values.name}
              onChange={(event) => update('name', event.target.value)}
              disabled={save.isPending}
            />
          </Field>

          <Field
            id="userId"
            label="Acesso vinculado"
            error={fieldErrors.userId}
            hint={
              canReadMembers
                ? 'Quem tem vínculo pode lançar as próprias viagens pelo sistema.'
                : 'Você não tem permissão para listar os membros desta organização, então este condutor será cadastrado sem vínculo. Um administrador pode vinculá-lo depois.'
            }
          >
            <Select
              {...fieldProps('userId', fieldErrors.userId, true)}
              value={values.userId}
              onChange={(event) => update('userId', event.target.value)}
              disabled={save.isPending || !canReadMembers || members.isPending}
            >
              <option value="">— sem vínculo —</option>
              {members.data?.items.map((member) => (
                <option key={member.id} value={member.user_id}>
                  {/* O contrato do `access` não devolve nome nem e-mail do membro — só o
                      `user_id`. É furo de backend, registrado no `Como ficou`: até ele fechar, a
                      opção se identifica pelo papel e pelo começo do id, que é o que existe. */}
                  {member.role} · {member.user_id.slice(0, 8)}
                </option>
              ))}
              {/* Um condutor já vinculado a alguém que a lista não trouxe (sem `members.read`, ou
                  membro fora da primeira página) manteria o campo em "sem vínculo" e o salvaria
                  desvinculado sem ninguém pedir. Esta opção preserva o valor atual. */}
              {values.userId &&
              !members.data?.items.some((member) => member.user_id === values.userId) ? (
                <option value={values.userId}>Vínculo atual ({values.userId.slice(0, 8)})</option>
              ) : null}
            </Select>
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              id="licenseNumber"
              label="CNH"
              error={fieldErrors.licenseNumber}
              hint="Opcional."
            >
              <Input
                {...fieldProps('licenseNumber', fieldErrors.licenseNumber, true)}
                type="text"
                inputMode="numeric"
                value={values.licenseNumber}
                onChange={(event) => update('licenseNumber', event.target.value)}
                disabled={save.isPending}
              />
            </Field>

            <Field id="licenseCategory" label="Categoria" error={fieldErrors.licenseCategory}>
              <Input
                {...fieldProps('licenseCategory', fieldErrors.licenseCategory)}
                type="text"
                placeholder="B"
                autoCapitalize="characters"
                value={values.licenseCategory}
                onChange={(event) => update('licenseCategory', event.target.value)}
                disabled={save.isPending}
              />
            </Field>
          </div>

          <Field id="licenseExpiresAt" label="Validade da CNH" error={fieldErrors.licenseExpiresAt}>
            <Input
              {...fieldProps('licenseExpiresAt', fieldErrors.licenseExpiresAt)}
              type="date"
              value={values.licenseExpiresAt}
              onChange={(event) => update('licenseExpiresAt', event.target.value)}
              disabled={save.isPending}
            />
          </Field>

          <Field id="driverStatus" label="Situação" error={fieldErrors.status}>
            <Select
              {...fieldProps('driverStatus', fieldErrors.status)}
              value={values.status}
              onChange={(event) => update('status', event.target.value as DriverStatus)}
              disabled={save.isPending}
            >
              {Object.entries(DRIVER_STATUS_LABEL).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={save.isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? 'Salvando…' : 'Salvar'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
