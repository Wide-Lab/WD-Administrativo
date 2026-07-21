/**
 * As chamadas da frota — as 14 rotas sob `/api/organizacoes/{orgId}/frota/*`.
 *
 * O `orgId` é o primeiro argumento de tudo, e vem do path da tela: a organização ativa **é** a
 * URL, nunca um header nem a sessão. Toda rota daqui já está atrás do `require_module('frota')` do
 * backend, então uma Empresa sem o módulo recebe 403 — o `ModuleGuard` da tela evita a ida, não a
 * substitui.
 *
 * É aqui, e só aqui, que o `camelCase` do formulário vira o `snake_case` do payload.
 */

import { usageFiltersToApiQuery, type UsageFilters } from '#/features/frota/lib/filters'
import {
  driverSchema,
  memberSchema,
  mileageReportSchema,
  pageSchema,
  usageSchema,
  vehicleSchema,
} from '#/features/frota/schema'
import type {
  Driver,
  DriverFormValues,
  Member,
  MileageGroupBy,
  MileageReport,
  Page,
  Usage,
  UsageFormValues,
  Vehicle,
  VehicleFormValues,
  VehicleStatus,
  CloseUsageFormValues,
  DriverStatus,
} from '#/features/frota/types'
import { apiFetch } from '#/lib/api'

function base(orgId: string): string {
  return `/api/organizacoes/${encodeURIComponent(orgId)}/frota`
}

/** A query string com `?`, ou vazia. Mesma regra do `usageFiltersToQueryString`: `?` solto é
 *  sujeira. */
function query(params: URLSearchParams): string {
  const value = params.toString()
  return value === '' ? '' : `?${value}`
}

// ---------------------------------------------------------------------------------------------
// Veículos
// ---------------------------------------------------------------------------------------------

export async function listVehicles(
  orgId: string,
  options: { status?: VehicleStatus; pageSize?: number } = {},
): Promise<Page<Vehicle>> {
  const params = new URLSearchParams()
  if (options.status) params.set('status', options.status)
  if (options.pageSize) params.set('page_size', String(options.pageSize))

  return pageSchema(vehicleSchema).parse(
    await apiFetch<unknown>(`${base(orgId)}/veiculos${query(params)}`),
  )
}

export async function createVehicle(orgId: string, values: VehicleFormValues): Promise<Vehicle> {
  return vehicleSchema.parse(
    await apiFetch<unknown>(`${base(orgId)}/veiculos`, {
      method: 'POST',
      body: JSON.stringify({
        plate: values.plate,
        brand: values.brand,
        model: values.model,
        model_year: values.modelYear,
        initial_odometer: values.initialOdometer,
        status: values.status,
      }),
    }),
  )
}

/** Edita um veículo.
 *
 *  `initial_odometer` **não vai** no corpo, e a ausência é a decisão: mudá-lo depois reescreve o
 *  passado de um carro que já rodou. O backend aceitaria (é `PATCH`) — quem não oferece é a tela,
 *  e está escrito aqui em vez de ser um `if` escondido no formulário. */
export async function updateVehicle(
  orgId: string,
  vehicleId: string,
  values: Omit<VehicleFormValues, 'initialOdometer'>,
): Promise<Vehicle> {
  return vehicleSchema.parse(
    await apiFetch<unknown>(`${base(orgId)}/veiculos/${encodeURIComponent(vehicleId)}`, {
      method: 'PATCH',
      body: JSON.stringify({
        plate: values.plate,
        brand: values.brand,
        model: values.model,
        model_year: values.modelYear ?? null,
        status: values.status,
      }),
    }),
  )
}

/** "Desativar" — e não apagar, porque não existe `DELETE` e o histórico é o produto. */
export async function setVehicleStatus(
  orgId: string,
  vehicleId: string,
  status: VehicleStatus,
): Promise<Vehicle> {
  return vehicleSchema.parse(
    await apiFetch<unknown>(`${base(orgId)}/veiculos/${encodeURIComponent(vehicleId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
  )
}

// ---------------------------------------------------------------------------------------------
// Condutores
// ---------------------------------------------------------------------------------------------

export async function listDrivers(
  orgId: string,
  options: { status?: DriverStatus; pageSize?: number } = {},
): Promise<Page<Driver>> {
  const params = new URLSearchParams()
  if (options.status) params.set('status', options.status)
  if (options.pageSize) params.set('page_size', String(options.pageSize))

  return pageSchema(driverSchema).parse(
    await apiFetch<unknown>(`${base(orgId)}/condutores${query(params)}`),
  )
}

export async function createDriver(orgId: string, values: DriverFormValues): Promise<Driver> {
  return driverSchema.parse(
    await apiFetch<unknown>(`${base(orgId)}/condutores`, {
      method: 'POST',
      body: JSON.stringify(driverPayload(values)),
    }),
  )
}

export async function updateDriver(
  orgId: string,
  driverId: string,
  values: DriverFormValues,
): Promise<Driver> {
  return driverSchema.parse(
    await apiFetch<unknown>(`${base(orgId)}/condutores/${encodeURIComponent(driverId)}`, {
      method: 'PATCH',
      body: JSON.stringify(driverPayload(values)),
    }),
  )
}

export async function setDriverStatus(
  orgId: string,
  driverId: string,
  status: DriverStatus,
): Promise<Driver> {
  return driverSchema.parse(
    await apiFetch<unknown>(`${base(orgId)}/condutores/${encodeURIComponent(driverId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
  )
}

/** Os campos opcionais viram `null` explícito, e não somem do corpo.
 *
 *  A diferença importa no `PATCH`: o backend usa `UNSET` pra "não mexa" e `None` pra "apague". Um
 *  campo omitido manteria a CNH antiga de um condutor cujo campo a pessoa acabou de limpar — o
 *  formulário mostra tudo, então ele manda tudo. */
function driverPayload(values: DriverFormValues) {
  return {
    name: values.name,
    user_id: values.userId ?? null,
    license_number: values.licenseNumber ?? null,
    license_category: values.licenseCategory ?? null,
    license_expires_at: values.licenseExpiresAt ?? null,
    status: values.status,
  }
}

// ---------------------------------------------------------------------------------------------
// Viagens
// ---------------------------------------------------------------------------------------------

/** As viagens — **já escopadas pelo backend**.
 *
 *  Esta é a única rota do módulo sem `require_permission`: quem tem `frota.usages.read` recebe a
 *  Empresa inteira, quem não tem recebe só as do próprio condutor. A tela **confia** e não
 *  filtra de novo: um segundo filtro aqui seria uma regra de autorização escrita no frontend. */
export async function listUsages(
  orgId: string,
  filters: UsageFilters,
  options: { pageSize?: number } = {},
): Promise<Page<Usage>> {
  const params = usageFiltersToApiQuery(filters)
  if (options.pageSize) params.set('page_size', String(options.pageSize))

  return pageSchema(usageSchema).parse(
    await apiFetch<unknown>(`${base(orgId)}/usos${query(params)}`),
  )
}

/** Lança uma viagem — inclusive retroativa, que é o caso normal.
 *
 *  `driver_id` só entra no corpo quando a tela tem o campo (quem tem `frota.drivers.read`).
 *  Omiti-lo significa "eu" pro backend, e é isso que faz o `collaborator` lançar em nome próprio
 *  sem que a tela precise descobrir qual é o condutor dele. */
export async function createUsage(orgId: string, values: UsageFormValues): Promise<Usage> {
  return usageSchema.parse(
    await apiFetch<unknown>(`${base(orgId)}/usos`, {
      method: 'POST',
      body: JSON.stringify({
        vehicle_id: values.vehicleId,
        driver_id: values.driverId || undefined,
        started_at: values.startedAt,
        start_odometer: values.startOdometer,
        ended_at: values.endedAt,
        end_odometer: values.endOdometer,
        purpose: values.purpose || undefined,
        notes: values.notes || undefined,
      }),
    }),
  )
}

/** Encerra a viagem: os dois campos **juntos**, na rota que existe pra garantir isso. */
export async function closeUsage(
  orgId: string,
  usageId: string,
  values: CloseUsageFormValues,
): Promise<Usage> {
  return usageSchema.parse(
    await apiFetch<unknown>(`${base(orgId)}/usos/${encodeURIComponent(usageId)}/encerrar`, {
      method: 'POST',
      body: JSON.stringify({
        ended_at: values.endedAt,
        end_odometer: values.endOdometer,
      }),
    }),
  )
}

/** Apaga um lançamento. Exige `frota.usages.write` — o `write_own` **não** alcança esta rota, e é
 *  a única do módulo em que as duas capabilities de escrita não se equivalem. */
export async function deleteUsage(orgId: string, usageId: string): Promise<void> {
  await apiFetch<void>(`${base(orgId)}/usos/${encodeURIComponent(usageId)}`, { method: 'DELETE' })
}

// ---------------------------------------------------------------------------------------------
// Relatório
// ---------------------------------------------------------------------------------------------

/** A quilometragem do período. `de` e `ate` são **obrigatórios** na rota — não há relatório "de
 *  tudo", e a tela abre no mês corrente por isso. */
export async function getMileageReport(
  orgId: string,
  params: { from: string; until: string; groupBy: MileageGroupBy },
): Promise<MileageReport> {
  const search = new URLSearchParams({
    de: `${params.from}T00:00:00`,
    ate: `${params.until}T23:59:59.999`,
    agrupar_por: params.groupBy,
  })

  return mileageReportSchema.parse(
    await apiFetch<unknown>(`${base(orgId)}/relatorios/quilometragem?${search.toString()}`),
  )
}

// ---------------------------------------------------------------------------------------------
// Membros — do `access`, não da frota
// ---------------------------------------------------------------------------------------------

/** Os membros da organização, pro select de `user_id` do condutor.
 *
 *  É a **única** chamada desta feature fora do módulo (`members.read`, do kernel), e ela é
 *  opcional por desenho: `manager` tem `drivers.write` e pode não ter `members.read` — são mapas
 *  diferentes (`PERMISSIONS_BY_ROLE` × o `grants` do módulo) e nada os obriga a concordar. Quem
 *  levar 403 aqui perde o select, não a tela.
 *
 *  **O que este contrato não dá, e devia:** `MemberResponse` é `id`/`user_id`/`role`/`status` —
 *  **sem nome e sem e-mail**. Não há como nomear a pessoa no select, e ele acaba oferecendo papel
 *  + um pedaço de UUID. É furo de backend, não da tela; está registrado no `Como ficou` da spec. */
export async function listMembers(orgId: string): Promise<Page<Member>> {
  return pageSchema(memberSchema).parse(
    await apiFetch<unknown>(`/api/organizacoes/${encodeURIComponent(orgId)}/membros?page_size=100`),
  )
}
