import { describe, expect, it } from 'vitest'

import { homePathFor, PLATFORM_HOME } from '#/features/context/lib/home-path'
import type { ContextMembership, OrganizationType, Role } from '#/features/context/types'

const ACME = '01890000-0000-7000-8000-00000000000a'
const GOMES = '01890000-0000-7000-8000-00000000000b'
const WIDELAB = '01890000-0000-7000-8000-000000000001'

function membership(id: string, type: OrganizationType, role: Role): ContextMembership {
  return { organization: { id, type, name: 'Org' }, role }
}

describe('homePathFor', () => {
  it('manda quem não tem vínculo pra lugar nenhum — é estado, não destino', () => {
    expect(homePathFor([])).toBeNull()
  })

  it('manda pra organização de quem tem um vínculo só', () => {
    expect(homePathFor([membership(ACME, 'company', 'collaborator')])).toBe(`/organizacoes/${ACME}`)
  })

  it('manda o vínculo de plataforma pra área cross-tenant, não pra um orgId', () => {
    expect(homePathFor([membership(WIDELAB, 'platform', 'platform_admin')])).toBe(PLATFORM_HOME)
  })

  it('a plataforma ganha da lista, esteja ela em que posição estiver', () => {
    const memberships = [
      membership(ACME, 'company', 'collaborator'),
      membership(WIDELAB, 'platform', 'platform_admin'),
    ]

    expect(homePathFor(memberships)).toBe(PLATFORM_HOME)
  })

  it('sem último orgId lembrado, cai no primeiro vínculo', () => {
    const memberships = [
      membership(GOMES, 'partner', 'partner_admin'),
      membership(ACME, 'company', 'collaborator'),
    ]

    expect(homePathFor(memberships)).toBe(`/organizacoes/${GOMES}`)
  })

  describe('com o último orgId visitado', () => {
    const doisVinculos = [
      membership(GOMES, 'partner', 'partner_admin'),
      membership(ACME, 'company', 'collaborator'),
    ]

    it('volta pra onde a pessoa estava, e não pro primeiro da lista', () => {
      expect(homePathFor(doisVinculos, ACME)).toBe(`/organizacoes/${ACME}`)
    })

    it('cai no primeiro vínculo quando o vínculo lembrado deixou de existir', () => {
      const semGomes = [membership(ACME, 'company', 'collaborator')]

      // O vínculo foi desativado desde a última visita: o backend o omite do `/me/contexto`.
      expect(homePathFor(semGomes, GOMES)).toBe(`/organizacoes/${ACME}`)
    })

    it('ignora um orgId que a pessoa alcança mas não tem vínculo (platform_admin em tenant alheio)', () => {
      const soPlataforma = [membership(WIDELAB, 'platform', 'platform_admin')]

      expect(homePathFor(soPlataforma, ACME)).toBe(PLATFORM_HOME)
    })

    it('uma visita explícita ganha do atalho da Plataforma', () => {
      const plataformaEEmpresa = [
        membership(WIDELAB, 'platform', 'platform_admin'),
        membership(ACME, 'company', 'company_admin'),
      ]

      expect(homePathFor(plataformaEEmpresa, ACME)).toBe(`/organizacoes/${ACME}`)
    })

    it('segue sem destino pra quem não tem vínculo nenhum', () => {
      expect(homePathFor([], ACME)).toBeNull()
    })
  })
})
