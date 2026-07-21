'use client'

import Link from 'next/link'
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
import { Textarea } from '#/components/ui/textarea'
import { useOrgContext, useOrgId } from '#/features/context/use-org-context'
import { Field, fieldProps } from '#/features/frota/components/field'
import {
  overlapFilters,
  usageFiltersToQueryString,
  type UsageFilters,
} from '#/features/frota/lib/filters'
import { translateUsageError, type UsageErrorField } from '#/features/frota/lib/frota-error'
import { nowForInput, vehicleLabel } from '#/features/frota/lib/labels'
import { frotaPath } from '#/features/frota/module'
import { FrotaPermissions } from '#/features/frota/permissions'
import { usageFormSchema } from '#/features/frota/schema'
import type { UsageFormState } from '#/features/frota/types'
import { useCreateUsage, useDrivers, useVehicles } from '#/features/frota/use-frota'

type FieldErrors = Partial<Record<keyof UsageFormState, string>>

function emptyState(): UsageFormState {
  return {
    vehicleId: '',
    driverId: '',
    // O agora só como valor **inicial** do campo, e editável. Retroativo é o caso normal da
    // frota, e não existe botão "iniciar agora" em lugar nenhum desta tela.
    startedAt: nowForInput(),
    startOdometer: '',
    endedAt: '',
    endOdometer: '',
    purpose: '',
    notes: '',
  }
}

/**
 * O formulário de viagem — **um só** pra viagem aberta e fechada.
 *
 * `ended_at` e `end_odometer` são um par opcional: os dois vazios lançam uma viagem em curso, os
 * dois preenchidos já a lançam encerrada (o lançamento retroativo de ontem). O par é indivisível,
 * e quem o exige primeiro é o `usageFormSchema` — o `ck_vehicle_usages_closed_together` o exigiria
 * também, mas com um erro que a tela sabia evitar.
 *
 * **`driver_id` é o campo que muda por capability, e é o único.** Com `frota.drivers.read`, um
 * select de condutores ativos; sem ela, **campo nenhum** — omitir `driver_id` já significa "sou
 * eu" pro backend, e apontar outro condutor responde 403. Renderizar um select que a pessoa não
 * pode preencher, ou um campo travado com o próprio nome, seria pedir 403 de propósito.
 */
export function UsageFormDialog({ trigger }: { trigger: ReactNode }) {
  const orgId = useOrgId()
  const { permissions } = useOrgContext()
  const canChooseDriver = permissions.includes(FrotaPermissions.DRIVERS_READ)

  const [open, setOpen] = useState(false)
  const [values, setValues] = useState<UsageFormState>(emptyState)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  /** Os filtros do atalho do 409 de sobreposição — `null` quando o erro não é esse. */
  const [overlapShortcut, setOverlapShortcut] = useState<UsageFilters | null>(null)

  // Só os **ativos**: veículo inativo "some da escolha na tela, não do sistema", e é esta a tela
  // de que o docstring da rota falava.
  const vehicles = useVehicles(orgId, 'active')
  const drivers = useDrivers(orgId, 'active', { enabled: canChooseDriver })
  const create = useCreateUsage(orgId)

  function update<K extends keyof UsageFormState>(field: K, value: UsageFormState[K]) {
    setValues((current) => ({ ...current, [field]: value }))
    setFieldErrors((current) => ({ ...current, [field]: undefined }))
    setFormError(null)
    setOverlapShortcut(null)
  }

  function reset() {
    setValues(emptyState())
    setFieldErrors({})
    setFormError(null)
    setOverlapShortcut(null)
    create.reset()
  }

  function handleOpenChange(next: boolean) {
    setOpen(next)
    if (!next) reset()
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const parsed = usageFormSchema.safeParse(values)
    if (!parsed.success) {
      const { fieldErrors: errors } = parsed.error.flatten()
      setFieldErrors({
        vehicleId: errors.vehicleId?.[0],
        driverId: errors.driverId?.[0],
        startedAt: errors.startedAt?.[0],
        startOdometer: errors.startOdometer?.[0],
        endedAt: errors.endedAt?.[0],
        endOdometer: errors.endOdometer?.[0],
        purpose: errors.purpose?.[0],
        notes: errors.notes?.[0],
      })
      return
    }

    setFieldErrors({})
    setFormError(null)

    create.mutate(
      // Sem o campo de condutor, o valor nunca sai do estado inicial (`''`) e a `api.ts` o omite
      // — que é o que faz "sou eu" acontecer.
      { ...parsed.data, driverId: canChooseDriver ? parsed.data.driverId : undefined },
      {
        onSuccess: () => handleOpenChange(false),
        onError: (error) => {
          const chosen = vehicles.data?.items.find((item) => item.id === values.vehicleId)
          const translated = translateUsageError(error, {
            vehicleLabel: chosen?.plate,
            startedAt: values.startedAt,
            endedAt: values.endedAt || undefined,
          })

          if (translated.field === null) {
            setFormError(translated.message)
            // O atalho existe porque o 409 fala de um dado que **não está na tela**: a viagem que
            // colide é de outra pessoa, possivelmente de outro dia. Sem um caminho até ela, a
            // pessoa fica com um "não pode" sem saber por quê.
            if (values.vehicleId && /sobrep|já tem uma viagem/i.test(translated.message)) {
              setOverlapShortcut(
                overlapFilters(values.vehicleId, values.startedAt, values.endedAt || undefined),
              )
            }
            return
          }

          setFieldErrors({ [translated.field as UsageErrorField]: translated.message })
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Lançar viagem</DialogTitle>
          <DialogDescription>
            Registre a viagem que aconteceu. Deixe a chegada em branco se o carro ainda está na rua.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {formError ? (
            <div
              role="alert"
              className="space-y-2 rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-text"
            >
              <p>{formError}</p>
              {overlapShortcut ? (
                <Link
                  href={`${frotaPath(orgId)}${usageFiltersToQueryString(overlapShortcut)}`}
                  onClick={() => handleOpenChange(false)}
                  className="inline-block font-medium text-primary-fg underline-offset-4 hover:underline"
                >
                  Ver as viagens desse veículo no período
                </Link>
              ) : null}
            </div>
          ) : null}

          <Field id="vehicleId" label="Veículo" error={fieldErrors.vehicleId}>
            <Select
              {...fieldProps('vehicleId', fieldErrors.vehicleId)}
              value={values.vehicleId}
              onChange={(event) => update('vehicleId', event.target.value)}
              disabled={create.isPending || vehicles.isPending}
            >
              <option value="">{vehicles.isPending ? 'Carregando…' : 'Escolha o veículo'}</option>
              {vehicles.data?.items.map((vehicle) => (
                <option key={vehicle.id} value={vehicle.id}>
                  {vehicleLabel(vehicle)}
                </option>
              ))}
            </Select>
          </Field>

          {/* O único campo que muda por capability. Sem `drivers.read`, ele não existe — e o
              backend resolve "sou eu" sozinho. */}
          {canChooseDriver ? (
            <Field
              id="driverId"
              label="Condutor"
              error={fieldErrors.driverId}
              hint="Deixe em branco para lançar em seu próprio nome."
            >
              <Select
                {...fieldProps('driverId', fieldErrors.driverId, true)}
                value={values.driverId}
                onChange={(event) => update('driverId', event.target.value)}
                disabled={create.isPending || drivers.isPending}
              >
                <option value="">Eu mesmo</option>
                {drivers.data?.items.map((driver) => (
                  <option key={driver.id} value={driver.id}>
                    {driver.name}
                  </option>
                ))}
              </Select>
            </Field>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="startedAt" label="Saída" error={fieldErrors.startedAt}>
              <Input
                {...fieldProps('startedAt', fieldErrors.startedAt)}
                type="datetime-local"
                value={values.startedAt}
                onChange={(event) => update('startedAt', event.target.value)}
                disabled={create.isPending}
              />
            </Field>

            <Field id="startOdometer" label="Hodômetro de saída" error={fieldErrors.startOdometer}>
              <Input
                {...fieldProps('startOdometer', fieldErrors.startOdometer)}
                type="number"
                inputMode="numeric"
                min={0}
                placeholder="Ex.: 45210"
                value={values.startOdometer}
                onChange={(event) => update('startOdometer', event.target.value)}
                disabled={create.isPending}
              />
            </Field>
          </div>

          <fieldset className="space-y-4 rounded-md border border-line p-4">
            <legend className="px-1 text-sm text-muted">
              Chegada — preencha os dois campos, ou nenhum
            </legend>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="endedAt" label="Chegada" error={fieldErrors.endedAt}>
                <Input
                  {...fieldProps('endedAt', fieldErrors.endedAt)}
                  type="datetime-local"
                  value={values.endedAt}
                  onChange={(event) => update('endedAt', event.target.value)}
                  disabled={create.isPending}
                />
              </Field>

              <Field id="endOdometer" label="Hodômetro de chegada" error={fieldErrors.endOdometer}>
                <Input
                  {...fieldProps('endOdometer', fieldErrors.endOdometer)}
                  type="number"
                  inputMode="numeric"
                  min={0}
                  placeholder="Ex.: 45355"
                  value={values.endOdometer}
                  onChange={(event) => update('endOdometer', event.target.value)}
                  disabled={create.isPending}
                />
              </Field>
            </div>
          </fieldset>

          <Field id="purpose" label="Finalidade" error={fieldErrors.purpose}>
            <Input
              {...fieldProps('purpose', fieldErrors.purpose)}
              type="text"
              placeholder="Ex.: entrega no centro"
              value={values.purpose}
              onChange={(event) => update('purpose', event.target.value)}
              disabled={create.isPending}
            />
          </Field>

          <Field id="notes" label="Observações" error={fieldErrors.notes}>
            <Textarea
              {...fieldProps('notes', fieldErrors.notes)}
              value={values.notes}
              onChange={(event) => update('notes', event.target.value)}
              disabled={create.isPending}
            />
          </Field>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={create.isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? 'Lançando…' : 'Lançar viagem'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
