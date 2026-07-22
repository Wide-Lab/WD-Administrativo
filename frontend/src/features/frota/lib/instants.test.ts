import { describe, expect, it } from 'vitest'

import { toInstant, toInstantOrUndefined } from '#/features/frota/lib/instants'

describe('toInstant — a hora digitada vira instante absoluto', () => {
  it('lê o `datetime-local` como hora **local**, que é o fuso de quem digitou', () => {
    // Nada de string literal esperada: o teste roda em qualquer fuso, e o que se afirma é a
    // equivalência, não o offset.
    expect(toInstant('2026-07-20T08:30')).toBe(new Date(2026, 6, 20, 8, 30).toISOString())
  })

  it('sempre sai com fuso — é o que o backend exige desde o 500 do lançamento', () => {
    expect(toInstant('2026-07-20T08:30')).toMatch(/Z$/)
  })

  it('preserva o instante de uma string que já tem offset', () => {
    expect(toInstant('2026-07-20T08:30:00-03:00')).toBe('2026-07-20T11:30:00.000Z')
  })

  it('devolve o valor cru no que não é data — quem recusa campo inválido é o zod', () => {
    expect(toInstant('')).toBe('')
    expect(toInstant('ontem')).toBe('ontem')
  })
})

describe('toInstantOrUndefined — o campo opcional da viagem aberta', () => {
  it('vazio continua vazio: sem `ended_at` é o que faz a viagem nascer em curso', () => {
    expect(toInstantOrUndefined(undefined)).toBeUndefined()
    expect(toInstantOrUndefined('')).toBeUndefined()
    expect(toInstantOrUndefined(null)).toBeUndefined()
  })

  it('preenchido passa pelo mesmo carimbo', () => {
    expect(toInstantOrUndefined('2026-07-20T18:00')).toBe(
      new Date(2026, 6, 20, 18, 0).toISOString(),
    )
  })
})
