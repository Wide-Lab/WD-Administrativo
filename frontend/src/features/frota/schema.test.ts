import { describe, expect, it } from 'vitest'

import {
  closeUsageFormSchema,
  driverFormSchema,
  isFutureMoment,
  usageFormSchema,
  vehicleFormSchema,
} from '#/features/frota/schema'

/** O mínimo que passa, pra cada teste mexer só no campo que lhe interessa. */
const viagem = (overrides: Record<string, string> = {}) => ({
  vehicleId: '018f0000-0000-7000-8000-000000000001',
  driverId: '',
  startedAt: '2026-07-20T08:00',
  startOdometer: '45210',
  endedAt: '',
  endOdometer: '',
  purpose: '',
  notes: '',
  ...overrides,
})

const errorsOf = (result: { success: boolean; error?: { flatten: () => unknown } }) =>
  (result.error?.flatten() as { fieldErrors: Record<string, string[] | undefined> }).fieldErrors

describe('usageFormSchema — o par indivisível `ended_at` + `end_odometer`', () => {
  it('os dois vazios lançam uma viagem em curso', () => {
    const result = usageFormSchema.safeParse(viagem())

    expect(result.success).toBe(true)
    if (!result.success) return
    expect(result.data.endedAt).toBeUndefined()
    expect(result.data.endOdometer).toBeUndefined()
  })

  it('os dois preenchidos lançam a viagem já encerrada — o retroativo de ontem', () => {
    const result = usageFormSchema.safeParse(
      viagem({ endedAt: '2026-07-20T11:00', endOdometer: '45355' }),
    )

    expect(result.success).toBe(true)
    if (!result.success) return
    expect(result.data.endedAt).toBe('2026-07-20T11:00')
    expect(result.data.endOdometer).toBe(45355)
  })

  it('só a chegada é meio par, e o erro cai no hodômetro que falta', () => {
    const result = usageFormSchema.safeParse(viagem({ endedAt: '2026-07-20T11:00' }))

    expect(result.success).toBe(false)
    if (result.success) return
    expect(errorsOf(result).endOdometer?.[0]).toContain('hodômetro de chegada')
    // E não no campo que a pessoa preencheu certo.
    expect(errorsOf(result).endedAt).toBeUndefined()
  })

  it('só o hodômetro é meio par, e o erro cai na chegada que falta', () => {
    const result = usageFormSchema.safeParse(viagem({ endOdometer: '45355' }))

    expect(result.success).toBe(false)
    if (result.success) return
    expect(errorsOf(result).endedAt?.[0]).toContain('data e a hora de chegada')
    expect(errorsOf(result).endOdometer).toBeUndefined()
  })

  it('espaço em branco não conta como preenchido — senão um campo "vazio" viraria meio par', () => {
    const result = usageFormSchema.safeParse(viagem({ endedAt: '   ', endOdometer: '  ' }))

    expect(result.success).toBe(true)
  })
})

describe('usageFormSchema — os demais campos', () => {
  it('exige o veículo, que é o único select sempre presente', () => {
    const result = usageFormSchema.safeParse(viagem({ vehicleId: '' }))

    expect(result.success).toBe(false)
    if (result.success) return
    expect(errorsOf(result).vehicleId?.[0]).toContain('Escolha o veículo')
  })

  it('o condutor é opcional — omiti-lo significa "sou eu" pro backend', () => {
    expect(usageFormSchema.safeParse(viagem({ driverId: '' })).success).toBe(true)
  })

  it('hodômetro vazio não vira zero — "não informado" e "zero km" não podem ser o mesmo', () => {
    const result = usageFormSchema.safeParse(viagem({ startOdometer: '' }))

    expect(result.success).toBe(false)
    if (result.success) return
    expect(errorsOf(result).startOdometer?.[0]).toContain('hodômetro de saída')
  })

  it('hodômetro com ponto ou vírgula é recusado — o backend quer inteiro', () => {
    expect(usageFormSchema.safeParse(viagem({ startOdometer: '45.210' })).success).toBe(false)
    expect(usageFormSchema.safeParse(viagem({ startOdometer: '45,210' })).success).toBe(false)
    expect(usageFormSchema.safeParse(viagem({ startOdometer: '-5' })).success).toBe(false)
  })

  it('hodômetro válido chega como number, não string — é o que o payload espera', () => {
    const result = usageFormSchema.safeParse(viagem({ startOdometer: '0' }))

    expect(result.success).toBe(true)
    if (!result.success) return
    expect(result.data.startOdometer).toBe(0)
  })
})

describe('isFutureMoment — a única regra que o banco não consegue impor', () => {
  const agora = new Date('2026-07-20T12:00:00')

  it('recusa o futuro', () => {
    expect(isFutureMoment('2026-07-20T12:01', agora)).toBe(true)
  })

  it('aceita o passado, que é o caso normal da frota', () => {
    expect(isFutureMoment('2026-07-19T08:00', agora)).toBe(false)
    expect(isFutureMoment('2020-01-01T00:00', agora)).toBe(false)
  })

  it('data ilegível não é "futuro" — quem reclama dela é o campo obrigatório, não esta regra', () => {
    expect(isFutureMoment('', agora)).toBe(false)
    expect(isFutureMoment('ontem', agora)).toBe(false)
  })
})

describe('closeUsageFormSchema — encerrar é ação, e os dois campos são obrigatórios', () => {
  it('aceita os dois preenchidos', () => {
    const result = closeUsageFormSchema.safeParse({
      endedAt: '2026-07-20T11:00',
      endOdometer: '45355',
    })

    expect(result.success).toBe(true)
    if (!result.success) return
    expect(result.data.endOdometer).toBe(45355)
  })

  it('recusa cada um sozinho — é o que a rota própria existe pra garantir', () => {
    expect(
      closeUsageFormSchema.safeParse({ endedAt: '2026-07-20T11:00', endOdometer: '' }).success,
    ).toBe(false)
    expect(closeUsageFormSchema.safeParse({ endedAt: '', endOdometer: '45355' }).success).toBe(
      false,
    )
  })
})

describe('vehicleFormSchema', () => {
  const veiculo = (overrides: Record<string, string> = {}) => ({
    plate: 'abc1d23',
    brand: 'Fiat',
    model: 'Strada',
    modelYear: '',
    initialOdometer: '0',
    status: 'active' as const,
    ...overrides,
  })

  it('normaliza a placa em maiúsculas, como o `normalize_plate` do backend', () => {
    const result = vehicleFormSchema.safeParse(veiculo())

    expect(result.success).toBe(true)
    if (!result.success) return
    expect(result.data.plate).toBe('ABC1D23')
  })

  it('não mexe em hífen nem espaço interno — unificá-los seria palpite sobre formato de placa', () => {
    const result = vehicleFormSchema.safeParse(veiculo({ plate: 'abc-1d23' }))

    expect(result.success).toBe(true)
    if (!result.success) return
    expect(result.data.plate).toBe('ABC-1D23')
  })

  it('exige placa, marca e modelo', () => {
    expect(vehicleFormSchema.safeParse(veiculo({ plate: '  ' })).success).toBe(false)
    expect(vehicleFormSchema.safeParse(veiculo({ brand: '' })).success).toBe(false)
    expect(vehicleFormSchema.safeParse(veiculo({ model: '' })).success).toBe(false)
  })

  it('o ano é opcional, mas quando vem tem quatro dígitos', () => {
    expect(vehicleFormSchema.safeParse(veiculo({ modelYear: '' })).success).toBe(true)
    expect(vehicleFormSchema.safeParse(veiculo({ modelYear: '24' })).success).toBe(false)

    const result = vehicleFormSchema.safeParse(veiculo({ modelYear: '2024' }))
    expect(result.success).toBe(true)
    if (!result.success) return
    expect(result.data.modelYear).toBe(2024)
  })

  it('o hodômetro inicial é obrigatório e aceita zero — carro novo existe', () => {
    expect(vehicleFormSchema.safeParse(veiculo({ initialOdometer: '' })).success).toBe(false)

    const result = vehicleFormSchema.safeParse(veiculo({ initialOdometer: '0' }))
    expect(result.success).toBe(true)
    if (!result.success) return
    expect(result.data.initialOdometer).toBe(0)
  })
})

describe('driverFormSchema', () => {
  const condutor = (overrides: Record<string, string> = {}) => ({
    name: 'João da Silva',
    userId: '',
    licenseNumber: '',
    licenseCategory: '',
    licenseExpiresAt: '',
    status: 'active' as const,
    ...overrides,
  })

  it('exige o nome, que é a única coisa que todo condutor tem', () => {
    expect(driverFormSchema.safeParse(condutor({ name: '   ' })).success).toBe(false)
  })

  it('"sem vínculo" é caso de primeira classe — o terceirizado dirige e nunca loga', () => {
    const result = driverFormSchema.safeParse(condutor({ userId: '' }))

    expect(result.success).toBe(true)
    if (!result.success) return
    expect(result.data.userId).toBeUndefined()
  })

  it('CNH e validade são opcionais, e o vazio vira ausente em vez de string vazia', () => {
    const result = driverFormSchema.safeParse(condutor())

    expect(result.success).toBe(true)
    if (!result.success) return
    expect(result.data.licenseNumber).toBeUndefined()
    expect(result.data.licenseCategory).toBeUndefined()
    expect(result.data.licenseExpiresAt).toBeUndefined()
  })

  it('preenchidos, chegam como vieram', () => {
    const result = driverFormSchema.safeParse(
      condutor({
        licenseNumber: '12345678900',
        licenseCategory: 'B',
        licenseExpiresAt: '2030-01-31',
      }),
    )

    expect(result.success).toBe(true)
    if (!result.success) return
    expect(result.data.licenseNumber).toBe('12345678900')
    expect(result.data.licenseExpiresAt).toBe('2030-01-31')
  })
})
