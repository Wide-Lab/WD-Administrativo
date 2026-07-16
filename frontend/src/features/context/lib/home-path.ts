/** Pra onde mandar alguém que só disse "quero entrar" — a `/`, o pós-login, e o destino de
 *  quem bateu numa área de persona que não é a sua.
 *
 *  Pura: é regra de roteamento, e regra de roteamento errada manda a pessoa pra um beco. O
 *  último `orgId` entra por **parâmetro**, não lido do `localStorage` aqui — é o que mantém a
 *  regra provável sem DOM (o Vitest deste projeto roda em `node`), e o efeito colateral fica
 *  numa peça só (`lib/last-org.ts`). */

import { organizationHomePath } from '#/features/context/nav'
import type { ContextMembership } from '#/features/context/types'

/** A área da Plataforma é **cross-tenant** e vive fora do `orgId`: administrar tenants é o que
 *  se faz *antes* de haver um tenant ativo. */
export const PLATFORM_HOME = '/plataforma'

export function isPlatformMembership(membership: ContextMembership): boolean {
  return membership.organization.type === 'platform'
}

/** A home deste vínculo. A da Plataforma não é um `orgId`: quem é da Widelab entra pela mesa
 *  de operação, e é o único vínculo cuja casca vive fora de `/organizacoes/`. */
export function membershipHomePath(membership: ContextMembership): string {
  return isPlatformMembership(membership)
    ? PLATFORM_HOME
    : organizationHomePath(membership.organization.id)
}

/** A home real de quem tem estes vínculos, ou `null` se a pessoa não tem nenhum.
 *
 *  A ordem é: **onde a pessoa estava** > a mesa da Plataforma > o primeiro vínculo.
 *
 *  `lastOrgId` só vale se ainda for um vínculo **válido** — e é a validação que faz o palpite
 *  ser seguro: o vínculo pode ter sido desativado desde a última visita (o backend o omite do
 *  `/me/contexto`), e um `platform_admin` alcança qualquer `orgId` sem ter vínculo nele. Nos
 *  dois casos o palpite é descartado em silêncio, sem quebrar.
 *
 *  Uma visita explícita ganha do atalho da Plataforma **de propósito**, e isto é uma mudança
 *  em relação à `04`: quem tem vínculo de plataforma *e* de tenant e estava no tenant volta pro
 *  tenant. É o que o critério 4 desta spec pede ("o último orgId … orienta o redirect"), é
 *  reversível pelo seletor, e quem trabalha só na mesa nunca guarda `orgId` nenhum — a
 *  `/plataforma` esquece o último (`forgetLastOrgId`), então ela segue caindo aqui.
 *
 *  `null` não é erro: é o convidado que ainda não aceitou nada (spec 06), e a `/` o trata como
 *  estado, com tela própria. */
export function homePathFor(
  memberships: readonly ContextMembership[],
  lastOrgId: string | null = null,
): string | null {
  const last = memberships.find((membership) => membership.organization.id === lastOrgId)
  if (last !== undefined) return membershipHomePath(last)

  const platform = memberships.find(isPlatformMembership)
  if (platform !== undefined) return PLATFORM_HOME

  const [first] = memberships
  if (first === undefined) return null

  return membershipHomePath(first)
}
