import { describe, expect, it } from 'vitest'

import { ROLES_BY_ORGANIZATION_TYPE, rolesFor } from '#/features/context/lib/roles'
import { roleSchema } from '#/features/context/schema'

/** Este mapa é um espelho de `ROLES_BY_ORGANIZATION_TYPE` do backend, e espelho quebra calado:
 *  um papel a mais aqui vira uma opção que só produz 422, um a menos vira um papel que a tela
 *  não deixa mais atribuir. Nenhum teste daqui alcança o Python — o que dá pra provar é a
 *  coerência interna, e é o que estes casos fazem. */
describe('ROLES_BY_ORGANIZATION_TYPE', () => {
  it('dá cinco papéis numa Empresa e dois num Parceiro', () => {
    // Os números estão na spec (`frontend/08`) em vez de só na lista: se alguém acrescentar um
    // papel sem passar pela spec, é aqui que a conta não fecha.
    expect(rolesFor('company')).toEqual([
      'company_admin',
      'hr',
      'finance',
      'manager',
      'collaborator',
    ])
    expect(rolesFor('partner')).toEqual(['partner_admin', 'partner_operator'])
  })

  it('dá à Plataforma só o papel dela', () => {
    expect(rolesFor('platform')).toEqual(['platform_admin'])
  })

  it('nunca oferece um papel que o `roleSchema` não conhece', () => {
    // O `roleSchema` é o outro espelho do mesmo enum (`Role`, no backend). Se os dois
    // divergirem, o select ofereceria um valor que o parse da resposta rejeitaria depois.
    for (const roles of Object.values(ROLES_BY_ORGANIZATION_TYPE)) {
      for (const role of roles) {
        expect(roleSchema.safeParse(role).success).toBe(true)
      }
    }
  })

  it('não repete um papel entre tipos — papel pertence a um tipo só', () => {
    const todos = Object.values(ROLES_BY_ORGANIZATION_TYPE).flat()

    expect(new Set(todos).size).toBe(todos.length)
  })

  it('cobre todos os papéis do enum, sem sobrar nenhum sem tipo', () => {
    // Um papel que não aparece em tipo nenhum é um papel que nenhuma tela consegue atribuir —
    // o modo de falha silencioso que este teste existe pra pegar.
    const cobertos = new Set(Object.values(ROLES_BY_ORGANIZATION_TYPE).flat())

    expect([...cobertos].sort()).toEqual([...roleSchema.options].sort())
  })
})
