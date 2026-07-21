/** Como os enums do `access` se chamam pra quem os lê.
 *
 *  São rótulos de **exibição** do valor que o backend mandou — não regra. Em especial,
 *  `ROLE_LABEL` **não** é papel→persona: essa é decisão do `access` (`persona_for`), vem pronta
 *  no `/me`, e o frontend nunca a recalcula (ver `features/context/schema.ts`).
 *
 *  Moram aqui, e não no componente que os usou primeiro, porque o seletor de organização (spec
 *  05) e o aceite de convite (spec 06) escrevem o mesmo papel — e duas tabelas divergiriam no
 *  primeiro papel novo, com a mesma pessoa lendo "RH" numa tela e "hr" na outra. */

import type {
  AgreementStatus,
  InvitationStatus,
  MembershipStatus,
} from '#/features/organization/types'

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

export const MEMBERSHIP_STATUS_LABEL: Record<MembershipStatus, string> = {
  active: 'Ativo',
  disabled: 'Desativado',
}

/** O status **efetivo** de um convite, como o backend o resolveu (`backend/08`).
 *
 *  "Expirado" é rótulo de algo que a tela **recebeu**, nunca de algo que ela calculou: a
 *  expiração é derivada de `expires_at` no servidor, e recalculá-la aqui seria a terceira
 *  escrita de uma regra que já existe duas vezes lá (Python e SQL) — e a única das três rodando
 *  num relógio que o servidor não controla. Ver `features/organization/schema.ts`. */
export const INVITATION_STATUS_LABEL: Record<InvitationStatus, string> = {
  pending: 'Pendente',
  accepted: 'Aceito',
  revoked: 'Revogado',
  expired: 'Expirado',
}

export const AGREEMENT_STATUS_LABEL: Record<AgreementStatus, string> = {
  active: 'Ativo',
  suspended: 'Suspenso',
}
