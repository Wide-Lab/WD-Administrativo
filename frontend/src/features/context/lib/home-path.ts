/** Pra onde mandar alguém que só disse "quero entrar" — a `/`, o pós-login, e o destino de
 *  quem bateu numa área de persona que não é a sua.
 *
 *  Pura: é regra de roteamento, e regra de roteamento errada manda a pessoa pra um beco. */

import { organizationHomePath } from '#/features/context/nav'
import type { ContextMembership } from '#/features/context/types'

/** A área da Plataforma é **cross-tenant** e vive fora do `orgId`: administrar tenants é o que
 *  se faz *antes* de haver um tenant ativo. */
export const PLATFORM_HOME = '/plataforma'

export function isPlatformMembership(membership: ContextMembership): boolean {
  return membership.organization.type === 'platform'
}

/** A home real de quem tem estes vínculos, ou `null` se a pessoa não tem nenhum.
 *
 *  Vínculo de plataforma ganha da lista: quem é da Widelab entra pela mesa de operação, não
 *  por um tenant. Com mais de um vínculo, cai no primeiro — **o seletor de organização é a
 *  spec 05**, e esta spec assume uma org ativa já resolvida. `null` não é erro: é o convidado
 *  que ainda não aceitou nada (spec 06), e a `/` o trata como estado, com tela própria. */
export function homePathFor(memberships: readonly ContextMembership[]): string | null {
  if (memberships.some(isPlatformMembership)) return PLATFORM_HOME

  const [first] = memberships
  if (first === undefined) return null

  return organizationHomePath(first.organization.id)
}
