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
    expect(homePathFor([membership(ACME, 'company', 'collaborator')])).toBe(
      `/organizacoes/${ACME}`,
    )
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

  it('com vários vínculos, cai no primeiro — o seletor é a spec 05', () => {
    const memberships = [
      membership(GOMES, 'partner', 'partner_admin'),
      membership(ACME, 'company', 'collaborator'),
    ]

    expect(homePathFor(memberships)).toBe(`/organizacoes/${GOMES}`)
  })
})
