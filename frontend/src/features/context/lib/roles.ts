/** Quais papéis existem em cada tipo de organização — o espelho de
 *  `ROLES_BY_ORGANIZATION_TYPE` (`access/domain/permissions.py`).
 *
 *  **Vem daqui e não do backend porque não há rota que o exponha.** É a mesma disciplina que o
 *  `MODULE_CATALOG` já carrega: mexeu no mapa do domínio, mexe aqui. O custo de errar é baixo e
 *  visível — o `PATCH /membros/{id}` responde 422 com a lista de papéis válidos na mensagem, e a
 *  tela mostra essa mensagem —, então a divergência aparece na primeira tentativa em vez de
 *  virar dado torto no banco. Quem **garante** segue sendo o `CHECK` gerado de `memberships`.
 *
 *  Nota que `platform` tem exatamente um papel: a Widelab como operadora. Nenhuma tela desta
 *  spec edita papel na organização `platform` — provisionar e operar tenant é a `frontend/09` —,
 *  mas o mapa é espelho e espelho não escolhe o que reflete. */

import type { OrganizationType, Role } from '#/features/context/types'

export const ROLES_BY_ORGANIZATION_TYPE: Record<OrganizationType, readonly Role[]> = {
  platform: ['platform_admin'],
  company: ['company_admin', 'hr', 'finance', 'manager', 'collaborator'],
  partner: ['partner_admin', 'partner_operator'],
}

/** Os papéis que o select de papel pode oferecer nesta organização.
 *
 *  Oferecer um papel de outro tipo não seria só feio: o backend o recusa com 422 e o banco o
 *  recusa com um `CHECK`, então o item existiria só pra produzir erro. */
export function rolesFor(organizationType: OrganizationType): readonly Role[] {
  return ROLES_BY_ORGANIZATION_TYPE[organizationType]
}
