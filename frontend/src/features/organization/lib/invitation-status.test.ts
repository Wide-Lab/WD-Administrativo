import { describe, expect, it } from 'vitest'

import { invitationStatusSchema } from '#/features/organization/schema'
import {
  actionFor,
  INVITATION_ACTION,
  parseStatusFilter,
  statusFilterHref,
} from '#/features/organization/lib/invitation-status'

describe('parseStatusFilter', () => {
  it('lê os quatro status que o backend conhece', () => {
    expect(parseStatusFilter('pending')).toBe('pending')
    expect(parseStatusFilter('accepted')).toBe('accepted')
    expect(parseStatusFilter('revoked')).toBe('revoked')
    expect(parseStatusFilter('expired')).toBe('expired')
  })

  // O critério 5: a aba abre só com os pendentes, **sem nenhum filtro aplicado**. A ausência do
  // parâmetro é o que produz isso, e ela não pode virar `'pending'` no caminho.
  it('trata a ausência do parâmetro como ausência de filtro, não como pending', () => {
    expect(parseStatusFilter(null)).toBeNull()
    expect(parseStatusFilter(undefined)).toBeNull()
    expect(parseStatusFilter('')).toBeNull()
  })

  it('cai no default em vez de quebrar com valor que o enum não conhece', () => {
    // Link velho, URL editada à mão, `?status=todos`: mandar isso ao backend renderia 422 por um
    // parâmetro que a pessoa nem sabe que existe.
    expect(parseStatusFilter('todos')).toBeNull()
    expect(parseStatusFilter('PENDING')).toBeNull()
    expect(parseStatusFilter('pending ')).toBeNull()
  })
})

describe('INVITATION_ACTION', () => {
  it('oferece revogar só no pendente', () => {
    expect(actionFor('pending')).toBe('revoke')
  })

  it('oferece convidar de novo no vencido e no revogado', () => {
    // Revogar é terminal: reconvidar é **criar outro**, com token novo. Não há "reativar".
    expect(actionFor('expired')).toBe('reinvite')
    expect(actionFor('revoked')).toBe('reinvite')
  })

  it('não oferece ação nenhuma no aceito — aquele virou membro', () => {
    // É isto que faz o 409 do backend não acontecer pela tela: a linha não tem o botão.
    expect(actionFor('accepted')).toBe('none')
  })

  it('cobre todo status do enum, sem deixar linha sem regra', () => {
    expect(Object.keys(INVITATION_ACTION).sort()).toEqual(
      [...invitationStatusSchema.options].sort(),
    )
  })
})

describe('statusFilterHref', () => {
  const PATH = '/organizacoes/01890000-0000-7000-8000-000000000009/pessoas'

  it('mantém a aba ao trocar de filtro', () => {
    // Trocar o filtro não pode jogar a pessoa de volta pra aba Membros.
    expect(statusFilterHref(PATH, 'revoked')).toBe(`${PATH}?aba=convites&status=revoked`)
  })

  it('não escreve parâmetro nenhum no estado sem filtro', () => {
    expect(statusFilterHref(PATH, null)).toBe(`${PATH}?aba=convites`)
  })

  it('produz uma URL que o próprio parser lê de volta', () => {
    // Ida e volta: o href que a tela escreve tem de ser o que ela sabe ler.
    for (const status of invitationStatusSchema.options) {
      const href = statusFilterHref(PATH, status)
      const raw = new URL(href, 'https://exemplo.test').searchParams.get('status')

      expect(parseStatusFilter(raw)).toBe(status)
    }
  })
})
