import { describe, expect, it } from 'vitest'

import {
  createAgreementErrorMessage,
  createInvitationErrorMessage,
  revokeInvitationErrorMessage,
  updateAgreementErrorMessage,
  updateMemberErrorMessage,
} from '#/features/organization/lib/organization-error'
import { ApiError } from '#/lib/api'

const VALIDACAO_DE_PAPEL =
  "O papel 'hr' não existe numa organização do tipo 'partner'. Papéis válidos: partner_admin, partner_operator."

describe('updateMemberErrorMessage', () => {
  // O critério 7: quando o 422 chega, é a lista de papéis válidos do backend que a tela mostra.
  // Reescrever a frase aqui seria trocar a única fonte que sabe o mapa de verdade por um palpite.
  it('repassa o 422 do backend, com a lista de papéis válidos', () => {
    const message = updateMemberErrorMessage(
      new ApiError(422, 'validation_error', VALIDACAO_DE_PAPEL),
    )

    expect(message).toBe(VALIDACAO_DE_PAPEL)
    expect(message).toContain('partner_admin')
  })

  it('explica o 404 como lista velha, não como erro da pessoa', () => {
    expect(
      updateMemberErrorMessage(new ApiError(404, 'not_found', 'Vínculo não encontrado.')),
    ).toContain('Recarregue a lista')
  })

  it('não manda tentar de novo num 403', () => {
    const message = updateMemberErrorMessage(new ApiError(403, 'forbidden', 'Forbidden.'))

    expect(message).toContain('permissão')
    expect(message).not.toContain('Tente de novo')
  })

  it('distingue falha de rede de resposta do servidor', () => {
    expect(updateMemberErrorMessage(new TypeError('Failed to fetch'))).toContain('conexão')
    expect(updateMemberErrorMessage(new ApiError(500, 'internal', 'boom'))).toContain(
      'não respondeu',
    )
  })
})

describe('revokeInvitationErrorMessage', () => {
  /** O caso que esta camada existe pra acertar: revogar um convite que virou membro não tira
   *  acesso nenhum. Mandar "tente de novo" faria alguém revogar em loop o que já não é o
   *  problema — a saída é a outra aba. */
  it('manda o 409 pra aba Membros, e não pra uma nova tentativa', () => {
    const message = revokeInvitationErrorMessage(
      new ApiError(409, 'conflict', 'Resource conflict.'),
    )

    expect(message).toContain('já aceitou')
    expect(message).toContain('Membros')
    expect(message).not.toMatch(/tente de novo/i)
  })

  it('explica o 404 como lista velha', () => {
    expect(revokeInvitationErrorMessage(new ApiError(404, 'not_found', 'x'))).toContain(
      'Recarregue a lista',
    )
  })
})

describe('createInvitationErrorMessage', () => {
  it('repassa o 422 de papel inválido pro tipo da organização', () => {
    expect(
      createInvitationErrorMessage(new ApiError(422, 'validation_error', VALIDACAO_DE_PAPEL)),
    ).toBe(VALIDACAO_DE_PAPEL)
  })
})

describe('createAgreementErrorMessage', () => {
  it('aponta o 409 pra lista, onde o convênio já está', () => {
    const message = createAgreementErrorMessage(new ApiError(409, 'conflict', 'Resource conflict.'))

    expect(message).toContain('Já existe um convênio')
    expect(message).toContain('suspenso')
  })

  it('repassa o 422 — só o backend sabe se o id não existe ou não é Parceiro', () => {
    const doBackend = 'O convênio precisa apontar para um Parceiro.'

    expect(createAgreementErrorMessage(new ApiError(422, 'validation_error', doBackend))).toBe(
      doBackend,
    )
  })
})

describe('updateAgreementErrorMessage', () => {
  it('explica o 404 como lista velha', () => {
    expect(updateAgreementErrorMessage(new ApiError(404, 'not_found', 'x'))).toContain(
      'Recarregue a lista',
    )
  })
})
