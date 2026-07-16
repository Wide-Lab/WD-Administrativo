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

function keysOf(persona: Persona, modules: readonly string[]): string[] {
  return buildNav({ orgId: ORG, persona, modules, catalog }).map((item) => item.key)
}

describe('buildNav', () => {
  it('sempre abre com a home da organização', () => {
    const [first] = buildNav({ orgId: ORG, persona: 'collaborator', modules: [], catalog })

    expect(first?.key).toBe('inicio')
    expect(first?.href).toBe(HOME)
  })

  it('prefixa o orgId no href do módulo — a org ativa é a da URL', () => {
    const nav = buildNav({ orgId: ORG, persona: 'collaborator', modules: ['refeicoes'], catalog })

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

  it('dá ao Parceiro só o módulo que o lista nas personas', () => {
    expect(keysOf('partner', ['refeicoes', 'frota'])).toEqual(['inicio', 'refeicoes'])
  })

  it('dá ao Admin da Empresa os dois', () => {
    expect(keysOf('company_admin', ['refeicoes', 'frota'])).toEqual(['inicio', 'refeicoes', 'frota'])
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
    })

    expect(nav.map((item) => item.key)).toEqual(['inicio', 'refeicoes'])
  })
})

describe('isNavItemActive', () => {
  const nav = buildNav({ orgId: ORG, persona: 'collaborator', modules: ['refeicoes'], catalog })
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
