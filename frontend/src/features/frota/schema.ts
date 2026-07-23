import { z } from 'zod'

/**
 * Os contratos da frota e os três formulários.
 *
 * Os enums e os nomes de campo são **cópia fiel** do backend (`frota/adapters/http/schemas.py`),
 * em `snake_case`: é payload, não modelo da tela. Reescrevê-los aqui é o preço de não ter geração
 * de tipos do OpenAPI, e o ganho é o de sempre — campo novo (ou renomeado) lá vira erro de parse
 * aqui, alto e cedo.
 *
 * Os **formulários**, ao contrário, falam `camelCase` e guardam tudo como string: é o que os
 * `<input>` devolvem. Quem faz a ponte entre os dois mundos é a `api.ts`.
 */

// ---------------------------------------------------------------------------------------------
// Contratos de resposta
// ---------------------------------------------------------------------------------------------

export const vehicleStatusSchema = z.enum(['active', 'maintenance', 'inactive'])
export const driverStatusSchema = z.enum(['active', 'inactive'])

/** O eixo do relatório. Os valores são **português** (`veiculo`/`condutor`) porque o
 *  `MileageGroupBy` do backend os escreveu assim — é query param, e query param deste projeto é
 *  português, como `de`/`ate`/`abertos`. */
export const mileageGroupBySchema = z.enum(['veiculo', 'condutor'])

export const vehicleSchema = z.object({
  id: z.string().uuid(),
  organization_id: z.string().uuid(),
  plate: z.string(),
  brand: z.string(),
  model: z.string(),
  model_year: z.number().int().nullable(),
  initial_odometer: z.number().int(),
  status: vehicleStatusSchema,
  created_at: z.string(),
})

export const driverSchema = z.object({
  id: z.string().uuid(),
  organization_id: z.string().uuid(),
  name: z.string(),
  /** O vínculo opcional com quem tem login — é ele que faz o `write_own` funcionar. Sem FK no
   *  banco, de propósito (é o seam de extração da frota), e por isso `z.string()` sem mais. */
  user_id: z.string().uuid().nullable(),
  license_number: z.string().nullable(),
  license_category: z.string().nullable(),
  license_expires_at: z.string().nullable(),
  status: driverStatusSchema,
  created_at: z.string(),
})

export const usageSchema = z.object({
  id: z.string().uuid(),
  organization_id: z.string().uuid(),
  vehicle_id: z.string().uuid(),
  driver_id: z.string().uuid(),
  started_at: z.string(),
  ended_at: z.string().nullable(),
  start_odometer: z.number().int(),
  end_odometer: z.number().int().nullable(),
  /** Os quilômetros rodados, **derivados pelo backend**, ou `null` na viagem aberta. A tela nunca
   *  calcula `end_odometer - start_odometer`: a segunda conta é a que diverge no dia em que a
   *  regra ganhar um caso. `null` vira "Em curso", nunca "0 km". */
  distance: z.number().int().nullable(),
  purpose: z.string().nullable(),
  notes: z.string().nullable(),
  created_by: z.string().uuid(),
  created_at: z.string(),
})

export const mileageGroupSchema = z.object({
  id: z.string().uuid(),
  label: z.string(),
  total_km: z.number().int(),
  closed_usages: z.number().int(),
  /** Nunca somada como zero km — é a contagem que explica por que o total não bate com o que a
   *  pessoa esperava. Por isso a tela a mostra **sempre**, mesmo zero. */
  open_usages: z.number().int(),
})

export const mileageReportSchema = z.object({
  group_by: mileageGroupBySchema,
  groups: z.array(mileageGroupSchema),
})

/** O envelope de paginação da frota — a cópia que o backend também teve de fazer (a `PageResponse`
 *  mora no `access`, e um app de negócio não a importa). Genérico por função porque `z.object`
 *  com item variável não se declara de outro jeito. */
export function pageSchema<ItemT extends z.ZodTypeAny>(item: ItemT) {
  return z.object({
    items: z.array(item),
    total: z.number().int(),
    page: z.number().int(),
    page_size: z.number().int(),
  })
}

/** Um membro da organização (`GET /api/organizacoes/{orgId}/membros`, do `access`).
 *
 *  A frota o consome por um motivo só: o `user_id` do condutor — e por muito tempo era só isso
 *  que dava pra consumir, porque a `MemberResponse` não trazia nome nem e-mail e o select
 *  oferecia `papel · <8 caracteres de UUID>`. **O furo era de backend, e foi fechado lá**: a
 *  resposta ganhou `name`/`email` (ver `backend/04`, seção "Depois"). Esta é a cópia local do
 *  contrato, e ela declara só os campos que a frota usa. */
export const memberSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  organization_id: z.string().uuid(),
  name: z.string(),
  email: z.string(),
  role: z.string(),
  status: z.string(),
  created_at: z.string(),
})

// ---------------------------------------------------------------------------------------------
// Peças comuns dos formulários
// ---------------------------------------------------------------------------------------------

/** Um hodômetro obrigatório: string do `<input>` → inteiro do payload.
 *
 *  Não é `z.coerce.number()` porque `Number('')` é `0`, e um campo vazio viraria "zero
 *  quilômetros" em silêncio — o pior erro possível num campo cuja diferença é o produto. */
const requiredOdometer = (label: string) =>
  z
    .string()
    .trim()
    .min(1, `Informe ${label}.`)
    .regex(/^\d+$/, 'Use só números inteiros, sem pontos.')
    .transform(Number)

/** O mesmo, mas opcional: vazio vira `undefined`, nunca `0`. */
const optionalOdometer = z
  .string()
  .trim()
  .transform((value) => (value === '' ? undefined : value))
  .pipe(
    z.string().regex(/^\d+$/, 'Use só números inteiros, sem pontos.').transform(Number).optional(),
  )

/** Um `datetime-local` opcional: vazio vira `undefined`. */
const optionalMoment = z
  .string()
  .trim()
  .transform((value) => (value === '' ? undefined : value))

// ---------------------------------------------------------------------------------------------
// Viagem — o formulário que carrega o módulo
// ---------------------------------------------------------------------------------------------

/** Se o instante digitado está no futuro.
 *
 *  Espelha o `is_future` do backend, que é a **única** regra do módulo que o banco não consegue
 *  impor (`now()` não entra em `CHECK`). Repeti-la aqui não cria segunda verdade: o 422 do
 *  servidor continua sendo a palavra final, e a tela só evita a ida até lá. Retroativo é o caso
 *  normal — o que se recusa é o futuro.
 *
 *  `now` é injetável pelo mesmo motivo do use case: teste não depende de relógio. */
export function isFutureMoment(value: string, now: Date = new Date()): boolean {
  const moment = new Date(value)
  if (Number.isNaN(moment.getTime())) return false
  return moment.getTime() > now.getTime()
}

/** O formulário de viagem, um só pra viagem aberta e fechada.
 *
 *  **A regra que importa é o par indivisível** `endedAt` + `endOdometer`: os dois vazios lançam
 *  uma viagem em curso, os dois preenchidos já a lançam encerrada (o lançamento retroativo de
 *  ontem, que é o caso normal). Meio par é recusado **aqui**, e não no banco: o
 *  `ck_vehicle_usages_closed_together` o recusaria também, mas com um 409 que a tela sabia evitar.
 *
 *  `driverId` é opcional porque omiti-lo significa "eu" pro backend — e é assim que o
 *  `collaborator`, cujo formulário não tem o campo, lança em nome de si mesmo. */
export const usageFormSchema = z
  .object({
    vehicleId: z.string().min(1, 'Escolha o veículo.'),
    driverId: z.string().optional(),
    startedAt: z
      .string()
      .trim()
      .min(1, 'Informe a data e a hora de saída.')
      .refine((value) => !isFutureMoment(value), {
        message: 'A saída não pode estar no futuro — registre a viagem que aconteceu.',
      }),
    startOdometer: requiredOdometer('o hodômetro de saída'),
    endedAt: optionalMoment,
    endOdometer: optionalOdometer,
    purpose: z.string().trim().max(200, 'Use no máximo 200 caracteres.').optional(),
    notes: z.string().trim().max(2000, 'Use no máximo 2000 caracteres.').optional(),
  })
  .superRefine((values, ctx) => {
    const hasEnd = values.endedAt !== undefined
    const hasOdometer = values.endOdometer !== undefined

    if (hasEnd === hasOdometer) return

    // A mensagem cai no campo que **falta**, e não no que foi preenchido: é lá que o cursor
    // precisa ir.
    if (hasEnd) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['endOdometer'],
        message: 'Para encerrar a viagem, informe também o hodômetro de chegada.',
      })
      return
    }

    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ['endedAt'],
      message: 'Para encerrar a viagem, informe também a data e a hora de chegada.',
    })
  })

/** O encerramento (`POST /usos/{id}/encerrar`) — os dois campos, e **obrigatórios**.
 *
 *  Formulário próprio, e não o de cima com os opcionais preenchidos: encerrar é ação, não edição.
 *  Deixar isso cair no `PATCH` genérico devolveria ao usuário a chance de encerrar pela metade,
 *  que é exatamente o que a rota própria existe pra impedir. */
export const closeUsageFormSchema = z.object({
  endedAt: z.string().trim().min(1, 'Informe a data e a hora de chegada.'),
  endOdometer: requiredOdometer('o hodômetro de chegada'),
})

// ---------------------------------------------------------------------------------------------
// Veículo
// ---------------------------------------------------------------------------------------------

/** Cadastro e edição de veículo.
 *
 *  `initialOdometer` está aqui, mas a tela só o **oferece no cadastro**: mudá-lo depois reescreve
 *  o passado de um carro que já rodou. O backend aceita (é `PATCH`), e a diferença fica registrada
 *  na spec em vez de virar um `if` escondido. */
export const vehicleFormSchema = z.object({
  plate: z
    .string()
    .trim()
    .min(1, 'Informe a placa.')
    .max(16, 'Use no máximo 16 caracteres.')
    // Maiúsculas aqui pelo mesmo motivo do `normalize_plate` do backend: o `UNIQUE
    // (organization_id, plate)` só significa o que promete com a placa normalizada. Hífen e
    // espaço interno ficam como vieram — mexer neles é palpite sobre formato de placa, e o
    // backend também não mexe.
    .transform((value) => value.toUpperCase()),
  brand: z.string().trim().min(1, 'Informe a marca.'),
  model: z.string().trim().min(1, 'Informe o modelo.'),
  modelYear: z
    .string()
    .trim()
    .transform((value) => (value === '' ? undefined : value))
    .pipe(
      z
        .string()
        .regex(/^\d{4}$/, 'Use um ano com quatro dígitos.')
        .transform(Number)
        .optional(),
    ),
  initialOdometer: requiredOdometer('o hodômetro inicial'),
  status: vehicleStatusSchema,
})

// ---------------------------------------------------------------------------------------------
// Condutor
// ---------------------------------------------------------------------------------------------

/** Cadastro e edição de condutor.
 *
 *  `userId` vazio é **"— sem vínculo —"**, e é caso de primeira classe: o motorista terceirizado
 *  dirige e nunca loga. Por isso o campo é opcional de verdade, e não um required com placeholder.
 *
 *  `licenseExpiresAt` é dado e só dado — a tela mostra a data e **não** pinta vencimento. Alerta
 *  de CNH está fora de escopo na `backend/10`, e uma tarja vermelha aqui seria meia implementação
 *  de compliance. */
export const driverFormSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, 'Informe o nome do condutor.')
    .max(120, 'Use no máximo 120 caracteres.'),
  userId: z
    .string()
    .trim()
    .transform((value) => (value === '' ? undefined : value)),
  licenseNumber: z
    .string()
    .trim()
    .max(32, 'Use no máximo 32 caracteres.')
    .transform((value) => (value === '' ? undefined : value)),
  licenseCategory: z
    .string()
    .trim()
    .max(8, 'Use no máximo 8 caracteres.')
    .transform((value) => (value === '' ? undefined : value)),
  licenseExpiresAt: z
    .string()
    .trim()
    .transform((value) => (value === '' ? undefined : value)),
  status: driverStatusSchema,
})
