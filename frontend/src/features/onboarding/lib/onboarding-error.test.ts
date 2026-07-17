import { describe, expect, it } from 'vitest'

import {
  acceptInvitationErrorMessage,
  invitationErrorMessage,
  isEmailConflict,
  registerPartnerErrorMessage,
} from '#/features/onboarding/lib/onboarding-error'
import { ApiError } from '#/lib/api'

const apiError = (status: number, message = 'mensagem do backend') =>
  new ApiError(status, 'some_code', message)

describe('invitationErrorMessage', () => {
  it('separa link torto (404) de convite gasto (410) — a saída de cada um é outra', () => {
    expect(invitationErrorMessage(apiError(404))).toContain('copiado inteiro')
    expect(invitationErrorMessage(apiError(410))).toContain('Peça um novo')
  })

  it('não fala de conta em nenhum caso — um convite é de um e-mail, não de quem já o usa', () => {
    for (const status of [404, 410, 422, 500]) {
      expect(invitationErrorMessage(apiError(status))).not.toMatch(/conta|cadastrad|existe/i)
    }
  })

  it('falha de rede (não-`ApiError`) fala de conexão, não de convite', () => {
    expect(invitationErrorMessage(new TypeError('Failed to fetch'))).toContain('conexão')
  })

  it('5xx não culpa o convite, que pode estar perfeito', () => {
    expect(invitationErrorMessage(apiError(500))).toContain('servidor')
  })
})

describe('acceptInvitationErrorMessage', () => {
  it('410 no aceite é o convite que venceu com a aba aberta, ou o token de uso único já gasto', () => {
    expect(acceptInvitationErrorMessage(apiError(410))).toContain('não vale mais')
  })

  it('422 é a senha que o backend recusou — pede pra conferir, sem dizer o quê', () => {
    expect(acceptInvitationErrorMessage(apiError(422))).toContain('Confira os dados')
  })

  it('nunca revela se o e-mail já tinha conta (critério 4)', () => {
    for (const status of [410, 422, 500]) {
      expect(acceptInvitationErrorMessage(apiError(status))).not.toMatch(/conta|cadastrad/i)
    }
  })
})

describe('isEmailConflict', () => {
  it('só o 409 é conflito de e-mail — é o que decide se a tela oferece o login', () => {
    expect(isEmailConflict(apiError(409))).toBe(true)
    expect(isEmailConflict(apiError(422))).toBe(false)
    expect(isEmailConflict(apiError(500))).toBe(false)
    expect(isEmailConflict(new TypeError('Failed to fetch'))).toBe(false)
  })
})

describe('registerPartnerErrorMessage', () => {
  it('409 conta que o e-mail já tem conta — o critério 2 cobra o conflito, e quem se cadastra é o dono do e-mail', () => {
    expect(registerPartnerErrorMessage(apiError(409))).toContain('já tem uma conta')
  })

  it('cai no genérico quando não é conflito', () => {
    expect(registerPartnerErrorMessage(apiError(422))).toContain('Confira os dados')
    expect(registerPartnerErrorMessage(apiError(500))).toContain('servidor')
    expect(registerPartnerErrorMessage(new TypeError('Failed to fetch'))).toContain('conexão')
  })

  it('erro sem tratamento próprio repete o que o backend disse, que é melhor que um chute', () => {
    expect(registerPartnerErrorMessage(apiError(400, 'organização inválida'))).toBe(
      'organização inválida',
    )
  })
})
