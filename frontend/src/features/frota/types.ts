import type { z } from 'zod'

import type {
  closeUsageFormSchema,
  driverFormSchema,
  driverSchema,
  driverStatusSchema,
  memberSchema,
  mileageGroupBySchema,
  mileageGroupSchema,
  mileageReportSchema,
  usageFormSchema,
  usageSchema,
  vehicleFormSchema,
  vehicleSchema,
  vehicleStatusSchema,
} from '#/features/frota/schema'

// Tipos sempre `z.infer`, nunca escritos à mão.

export type VehicleStatus = z.infer<typeof vehicleStatusSchema>
export type DriverStatus = z.infer<typeof driverStatusSchema>
export type MileageGroupBy = z.infer<typeof mileageGroupBySchema>

export type Vehicle = z.infer<typeof vehicleSchema>
export type Driver = z.infer<typeof driverSchema>
export type Usage = z.infer<typeof usageSchema>
export type MileageGroup = z.infer<typeof mileageGroupSchema>
export type MileageReport = z.infer<typeof mileageReportSchema>
export type Member = z.infer<typeof memberSchema>

/** Uma página de qualquer coisa da frota. O envelope é o mesmo pras três listas. */
export type Page<ItemT> = {
  items: ItemT[]
  total: number
  page: number
  page_size: number
}

// Formulários: a **saída** do parse (`z.output`), que é o que a `api.ts` recebe — os campos
// numéricos já viraram número e os vazios já viraram `undefined`. A **entrada** é o estado do
// React, e é toda de string; ela tem tipo próprio abaixo porque `z.input` de um schema com
// `.transform` encadeado não sobrevive ao `.pipe`.

export type UsageFormValues = z.output<typeof usageFormSchema>
export type CloseUsageFormValues = z.output<typeof closeUsageFormSchema>
export type VehicleFormValues = z.output<typeof vehicleFormSchema>
export type DriverFormValues = z.output<typeof driverFormSchema>

/** O que o `useState` de cada formulário guarda: string em tudo, porque é o que o `<input>` dá. */
export type UsageFormState = {
  vehicleId: string
  driverId: string
  startedAt: string
  startOdometer: string
  endedAt: string
  endOdometer: string
  purpose: string
  notes: string
}

export type CloseUsageFormState = {
  endedAt: string
  endOdometer: string
}

export type VehicleFormState = {
  plate: string
  brand: string
  model: string
  modelYear: string
  initialOdometer: string
  status: VehicleStatus
}

export type DriverFormState = {
  name: string
  userId: string
  licenseNumber: string
  licenseCategory: string
  licenseExpiresAt: string
  status: DriverStatus
}
