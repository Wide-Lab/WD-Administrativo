import { describe, expect, it } from 'vitest'

import { MODULE_CATALOG, type ModuleNavDescriptor } from '#/features/context/modules'
import { buildNav, isNavItemActive, type NavIcon } from '#/features/context/nav'
import type { Persona } from '#/features/context/types'

const ORG = '01890000-0000-7000-8000-000000000009'
const HOME = `/organizacoes/${ORG}`

// Ícone de mentira: a `buildNav` só o repassa, e prendê-lo a um ícone real acoplaria o teste
// da regra a uma escolha de desenho.
const icon: NavIcon = () => null

const catalog: readonly ModuleNavDescriptor[] = [
  {
    key: 'refeicoes',
    label: 'Refeições',
    path: '/refeicoes',
    personas: ['collaborator', 'company_admin', 'partner'],
    icon,
  },
  {
    key: 'frota',
    label: 'Frota',
    path: '/frota',
    personas: ['collaborator', 'company_admin'],
    icon,
  },
]

function keysOf(
  persona: Persona,
  modules: readonly string[],
  permissions: readonly string[] = [],
): string[] {
  return buildNav({ orgId: ORG, persona, modules, catalog, permissions }).map((item) => item.key)
}

describe('buildNav', () => {
  it('sempre abre com a home da organização', () => {
    const [first] = buildNav({
      orgId: ORG,
      persona: 'collaborator',
      modules: [],
      catalog,
      permissions: [],
    })

    expect(first?.key).toBe('inicio')
    expect(first?.href).toBe(HOME)
  })

  it('prefixa o orgId no href do módulo — a org ativa é a da URL', () => {
    const nav = buildNav({
      orgId: ORG,
      persona: 'collaborator',
      modules: ['refeicoes'],
      catalog,
      permissions: [],
    })

    expect(nav.find((item) => item.key === 'refeicoes')).toMatchObject({
      label: 'Refeições',
      href: `${HOME}/refeicoes`,
    })
  })

  // O critério 1 da spec: é o entitlement do tenant que faz o item existir ou sumir.
  it('mostra o módulo habilitado e esconde o que não foi contratado', () => {
    expect(keysOf('collaborator', ['refeicoes'])).toEqual(['inicio', 'refeicoes'])
    expect(keysOf('collaborator', [])).toEqual(['inicio'])
  })

  it('lista os dois módulos quando a Empresa contratou os dois', () => {
    expect(keysOf('collaborator', ['refeicoes', 'frota'])).toEqual(['inicio', 'refeicoes', 'frota'])
  })

  // Persona × módulos: entitlement sozinho não basta.
  it('esconde da Plataforma um módulo contratado que não atende a persona dela', () => {
    expect(keysOf('platform', ['refeicoes', 'frota'])).toEqual(['inicio'])
  })

  // Os dois casos abaixo trazem 'parceiros' junto porque ele não depende de capability nenhuma
  // (a rota de convênios exige só o vínculo) — quem o filtra é a persona. Ver `KERNEL_NAV`.
  it('dá ao Parceiro só o módulo que o lista nas personas', () => {
    expect(keysOf('partner', ['refeicoes', 'frota'])).toEqual(['inicio', 'refeicoes', 'parceiros'])
  })

  it('dá ao Admin da Empresa os dois', () => {
    expect(keysOf('company_admin', ['refeicoes', 'frota'])).toEqual([
      'inicio',
      'refeicoes',
      'frota',
      'parceiros',
    ])
  })

  it('ignora chave habilitada que o frontend não conhece, sem quebrar', () => {
    // O backend pode ter um módulo que este deploy ainda não tem — ausência de label não é erro.
    expect(keysOf('collaborator', ['refeicoes', 'modulo_do_futuro'])).toEqual([
      'inicio',
      'refeicoes',
    ])
  })

  it('preserva a ordem do catálogo, não a ordem em que o tenant contratou', () => {
    expect(keysOf('collaborator', ['frota', 'refeicoes'])).toEqual(['inicio', 'refeicoes', 'frota'])
  })

  it('vale para o catálogo real, não só para o do teste', () => {
    // `MODULE_CATALOG` espelha `src/api/modules.py`; se divergirem, o item aparece pra uma
    // persona que não tem tela — ou some de quem tem.
    const nav = buildNav({
      orgId: ORG,
      persona: 'collaborator',
      modules: ['refeicoes'],
      catalog: MODULE_CATALOG,
      permissions: [],
    })

    expect(nav.map((item) => item.key)).toEqual(['inicio', 'refeicoes'])
  })
})

/** O grupo do kernel (`frontend/08`). São as telas que existem em todo tenant, e a regra de
 *  visibilidade delas é a única peça desta spec que dá pra provar sem browser — é por isso que o
 *  critério 11 a nomeia. */
describe('buildNav — Pessoas e Parceiros', () => {
  // O critério 11 em duas linhas: com e sem `members.read`.
  it('mostra Pessoas a quem tem members.read e esconde de quem não tem', () => {
    expect(keysOf('company_admin', [], ['members.read'])).toContain('pessoas')
    expect(keysOf('company_admin', [], [])).not.toContain('pessoas')
  })

  it('decide Pessoas por capability, não por persona', () => {
    // O caso que persona erraria: `hr` e `finance` compartilham a persona `company_admin`, e só
    // um dos dois tem `members.read`. Um filtro por persona daria a tela aos dois.
    const hr = keysOf('company_admin', [], ['members.read', 'invitations.read'])
    const finance = keysOf('company_admin', [], [])

    expect(hr).toContain('pessoas')
    expect(finance).not.toContain('pessoas')
  })

  it('dá Pessoas ao partner_admin, que é outra persona', () => {
    // A outra metade do mesmo argumento: a capability atravessa personas diferentes.
    expect(keysOf('partner', [], ['members.read'])).toContain('pessoas')
  })

  it('mostra Parceiros a quem administra a organização, dos dois lados do convênio', () => {
    expect(keysOf('company_admin', [], [])).toContain('parceiros')
    expect(keysOf('partner', [], [])).toContain('parceiros')
  })

  // O critério 1: o `collaborator` não vê nenhum dos dois.
  it('esconde os dois do Colaborador', () => {
    expect(keysOf('collaborator', ['refeicoes'], [])).toEqual(['inicio', 'refeicoes'])
  })

  /** A Plataforma inspecionando um tenant é o caso que mostra a regra funcionando, e o resultado
   *  é assimétrico de propósito:
   *
   *  - **Pessoas aparece.** `platform_admin` tem `members.read`/`members.write` de verdade
   *    (`PERMISSIONS_BY_ROLE`), porque é assim que a Widelab conserta o vínculo de um cliente, e
   *    o `require_permission` afrouxa pra ele em qualquer `orgId`. A tela funciona pra ele, então
   *    escondê-la seria a tal "persona acertando por acidente" que a spec manda evitar.
   *  - **Parceiros não aparece.** Conveniar é ato da Empresa — `platform_admin` não tem
   *    `agreements.write` (decisão da `backend/03`), e a persona `platform` não é lado nenhum de
   *    um convênio.
   */
  it('dá Pessoas à Plataforma, que tem a capability, e não lhe dá Parceiros', () => {
    expect(keysOf('platform', [], ['members.read', 'members.write'])).toEqual(['inicio', 'pessoas'])
  })

  it('não dá Pessoas à Plataforma sem a capability', () => {
    // Quem decide continua sendo a capability, não o fato de ser plataforma.
    expect(keysOf('platform', [], [])).toEqual(['inicio'])
  })

  it('põe o grupo do kernel depois dos módulos', () => {
    expect(keysOf('company_admin', ['refeicoes', 'frota'], ['members.read'])).toEqual([
      'inicio',
      'refeicoes',
      'frota',
      'pessoas',
      'parceiros',
    ])
  })

  it('embute o orgId nos hrefs dos dois, como faz com os módulos', () => {
    const nav = buildNav({
      orgId: ORG,
      persona: 'company_admin',
      modules: [],
      catalog,
      permissions: ['members.read'],
    })

    expect(nav.find((item) => item.key === 'pessoas')?.href).toBe(`${HOME}/pessoas`)
    expect(nav.find((item) => item.key === 'parceiros')?.href).toBe(`${HOME}/parceiros`)
  })

  it('não deixa uma capability de módulo destravar tela de kernel', () => {
    // `frota.vehicles.read` é capability namespaced de módulo (`backend/09`). Um `includes`
    // frouxo ou um `startsWith` a confundiria com `members.read`.
    expect(keysOf('company_admin', ['frota'], ['frota.vehicles.read'])).not.toContain('pessoas')
  })
})

describe('isNavItemActive', () => {
  const nav = buildNav({
    orgId: ORG,
    persona: 'collaborator',
    modules: ['refeicoes'],
    catalog,
    permissions: [],
  })
  const inicio = nav[0]!
  const refeicoes = nav[1]!

  it('acende a home só na home', () => {
    expect(isNavItemActive(HOME, inicio, ORG)).toBe(true)
    expect(isNavItemActive(`${HOME}/refeicoes`, inicio, ORG)).toBe(false)
  })

  it('mantém o módulo aceso numa tela de dentro dele', () => {
    expect(isNavItemActive(`${HOME}/refeicoes`, refeicoes, ORG)).toBe(true)
    expect(isNavItemActive(`${HOME}/refeicoes/tickets/1`, refeicoes, ORG)).toBe(true)
  })

  it('não acende por prefixo de nome parecido', () => {
    expect(isNavItemActive(`${HOME}/refeicoes-antigo`, refeicoes, ORG)).toBe(false)
  })
})
