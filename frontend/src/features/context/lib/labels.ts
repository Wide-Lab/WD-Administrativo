/** Como os enums do `access` se chamam pra quem os lê.
 *
 *  São rótulos de **exibição** do valor que o backend mandou — não regra. Em especial,
 *  `ROLE_LABEL` **não** é papel→persona: essa é decisão do `access` (`persona_for`), vem pronta
 *  no `/me`, e o frontend nunca a recalcula (ver `features/context/schema.ts`).
 *
 *  Moram aqui, e não no componente que os usou primeiro, porque o seletor de organização (spec
 *  05) e o aceite de convite (spec 06) escrevem o mesmo papel — e duas tabelas divergiriam no
 *  primeiro papel novo, com a mesma pessoa lendo "RH" numa tela e "hr" na outra. */

import type { OrganizationType, Role } from '#/features/context/types'

export const ORGANIZATION_TYPE_LABEL: Record<OrganizationType, string> = {
  platform: 'Plataforma',
  company: 'Empresa',
  partner: 'Parceiro',
}

export const ROLE_LABEL: Record<Role, string> = {
  platform_admin: 'Administrador',
  company_admin: 'Administrador',
  hr: 'RH',
  finance: 'Financeiro',
  manager: 'Gestor',
  collaborator: 'Colaborador',
  partner_admin: 'Administrador',
  partner_operator: 'Operador',
}
