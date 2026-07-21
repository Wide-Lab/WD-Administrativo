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
import { useOrgId } from '#/features/context/use-org-context'
import { Field, fieldProps } from '#/features/frota/components/field'
import { translateVehicleError } from '#/features/frota/lib/frota-error'
import { VEHICLE_STATUS_LABEL } from '#/features/frota/lib/labels'
import { vehicleFormSchema } from '#/features/frota/schema'
import type { Vehicle, VehicleFormState, VehicleStatus } from '#/features/frota/types'
import { useSaveVehicle } from '#/features/frota/use-frota'

type FieldErrors = Partial<Record<keyof VehicleFormState, string>>

function stateFrom(vehicle?: Vehicle): VehicleFormState {
  return {
    plate: vehicle?.plate ?? '',
    brand: vehicle?.brand ?? '',
    model: vehicle?.model ?? '',
    modelYear:
      vehicle?.model_year === null || vehicle === undefined ? '' : String(vehicle.model_year),
    initialOdometer: vehicle === undefined ? '' : String(vehicle.initial_odometer),
    status: vehicle?.status ?? 'active',
  }
}

/**
 * Cadastro e edição de veículo.
 *
 * **`initial_odometer` só é editável no cadastro.** Mudá-lo depois reescreve o passado de um carro
 * que já rodou, e a tela não oferece o que o domínio não quer. O backend aceita — é `PATCH` — e
 * essa diferença fica registrada aqui e na `api.ts`, em vez de virar um `if` escondido.
 *
 * Não há botão de apagar em lugar nenhum: **não existe `DELETE`** no backend, e é decisão da
 * `backend/10` (o histórico é o produto). O que a tela oferece é `status` — "Desativar" —, nunca
 * uma lixeira.
 */
export function VehicleFormDialog({ vehicle, trigger }: { vehicle?: Vehicle; trigger: ReactNode }) {
  const orgId = useOrgId()
  const isEditing = vehicle !== undefined

  const [open, setOpen] = useState(false)
  const [values, setValues] = useState<VehicleFormState>(() => stateFrom(vehicle))
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const save = useSaveVehicle(orgId)

  function update<K extends keyof VehicleFormState>(field: K, value: VehicleFormState[K]) {
    setValues((current) => ({ ...current, [field]: value }))
    setFieldErrors((current) => ({ ...current, [field]: undefined }))
    setFormError(null)
  }

  function handleOpenChange(next: boolean) {
    setOpen(next)
    if (!next) {
      setValues(stateFrom(vehicle))
      setFieldErrors({})
      setFormError(null)
      save.reset()
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const parsed = vehicleFormSchema.safeParse(values)
    if (!parsed.success) {
      const { fieldErrors: errors } = parsed.error.flatten()
      setFieldErrors({
        plate: errors.plate?.[0],
        brand: errors.brand?.[0],
        model: errors.model?.[0],
        modelYear: errors.modelYear?.[0],
        initialOdometer: errors.initialOdometer?.[0],
        status: errors.status?.[0],
      })
      return
    }

    setFieldErrors({})
    save.mutate(
      { vehicleId: vehicle?.id, values: parsed.data },
      {
        onSuccess: () => handleOpenChange(false),
        onError: (error) => {
          const translated = translateVehicleError(error)
          if (translated.field === null) {
            setFormError(translated.message)
            return
          }
          // A placa duplicada vai **pro campo placa** — é lá que a pessoa corrige.
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
          <DialogTitle>{isEditing ? 'Editar veículo' : 'Cadastrar veículo'}</DialogTitle>
          <DialogDescription>
            {isEditing
              ? 'O hodômetro inicial não muda: ele é o ponto de partida do histórico deste carro.'
              : 'O hodômetro inicial é a leitura no dia em que o carro entrou na frota.'}
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

          <Field id="plate" label="Placa" error={fieldErrors.plate}>
            <Input
              {...fieldProps('plate', fieldErrors.plate)}
              type="text"
              autoCapitalize="characters"
              placeholder="ABC1D23"
              value={values.plate}
              onChange={(event) => update('plate', event.target.value)}
              disabled={save.isPending}
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="brand" label="Marca" error={fieldErrors.brand}>
              <Input
                {...fieldProps('brand', fieldErrors.brand)}
                type="text"
                placeholder="Fiat"
                value={values.brand}
                onChange={(event) => update('brand', event.target.value)}
                disabled={save.isPending}
              />
            </Field>

            <Field id="model" label="Modelo" error={fieldErrors.model}>
              <Input
                {...fieldProps('model', fieldErrors.model)}
                type="text"
                placeholder="Strada"
                value={values.model}
                onChange={(event) => update('model', event.target.value)}
                disabled={save.isPending}
              />
            </Field>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="modelYear" label="Ano" error={fieldErrors.modelYear} hint="Opcional.">
              <Input
                {...fieldProps('modelYear', fieldErrors.modelYear, true)}
                type="number"
                inputMode="numeric"
                placeholder="2024"
                value={values.modelYear}
                onChange={(event) => update('modelYear', event.target.value)}
                disabled={save.isPending}
              />
            </Field>

            {/* Só no cadastro — ver o docstring do componente. */}
            {isEditing ? null : (
              <Field
                id="initialOdometer"
                label="Hodômetro inicial"
                error={fieldErrors.initialOdometer}
              >
                <Input
                  {...fieldProps('initialOdometer', fieldErrors.initialOdometer)}
                  type="number"
                  inputMode="numeric"
                  min={0}
                  placeholder="0"
                  value={values.initialOdometer}
                  onChange={(event) => update('initialOdometer', event.target.value)}
                  disabled={save.isPending}
                />
              </Field>
            )}
          </div>

          <Field id="status" label="Situação" error={fieldErrors.status}>
            <Select
              {...fieldProps('status', fieldErrors.status)}
              value={values.status}
              onChange={(event) => update('status', event.target.value as VehicleStatus)}
              disabled={save.isPending}
            >
              {Object.entries(VEHICLE_STATUS_LABEL).map(([value, label]) => (
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
