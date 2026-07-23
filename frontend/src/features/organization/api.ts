import {
  agreementPageSchema,
  agreementSchema,
  invitationPageSchema,
  invitationSchema,
  memberPageSchema,
  memberSchema,
} from '#/features/organization/schema'
import type {
  Agreement,
  AgreementStatus,
  CreateAgreementInput,
  CreateInvitationInput,
  Invitation,
  InvitationStatus,
  Member,
  Page,
  UpdateMemberInput,
} from '#/features/organization/types'
import { apiFetch } from '#/lib/api'

/** As oito rotas com que uma organização administra a si mesma. Todas escopadas pelo `orgId` do
 *  **path** — a organização ativa é a URL, nunca um header nem a sessão. */

function orgPath(orgId: string): string {
  return `/api/organizacoes/${encodeURIComponent(orgId)}`
}

/** O `?page=`/`?page_size=` que o `get_page_params` do backend lê (1-based, `page_size` ≤ 100). */
function pageQuery(page: number, pageSize: number): string {
  return `page=${page}&page_size=${pageSize}`
}

export async function listMembers(
  orgId: string,
  { page, pageSize }: { page: number; pageSize: number },
): Promise<Page<Member>> {
  return memberPageSchema.parse(
    await apiFetch<unknown>(`${orgPath(orgId)}/membros?${pageQuery(page, pageSize)}`),
  )
}

/** Muda papel e/ou status de um vínculo (`members.write`).
 *
 *  422 se o papel não existe no tipo desta organização — e a mensagem do backend traz a lista de
 *  papéis válidos, que é o que a tela mostra —, **e 422 também no próprio vínculo**: ninguém se
 *  rebaixa nem se desativa. 404, e não 403, num vínculo de outra organização: quem não pode
 *  vê-lo também não deveria descobrir que ele existe.
 *
 *  Devolve o membro no mesmo formato da listagem, com `name` e `email` — a tela não tem duas
 *  formas do mesmo objeto pra parsear. */
export async function updateMember(
  orgId: string,
  membershipId: string,
  input: UpdateMemberInput,
): Promise<Member> {
  return memberSchema.parse(
    await apiFetch<unknown>(`${orgPath(orgId)}/membros/${encodeURIComponent(membershipId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ role: input.role, status: input.status }),
    }),
  )
}

/** Lista convites (`invitations.read`).
 *
 *  **Sem `status`, o backend devolve só os pendentes** — o default é dele, não desta função, e
 *  não passar o parâmetro é como se pede "o que ainda está de pé pra alguém aceitar". Mandar
 *  `?status=pending` explicitamente daria o mesmo resultado hoje e esconderia de quem lê o
 *  código que o default existe. */
export async function listInvitations(
  orgId: string,
  { page, pageSize, status }: { page: number; pageSize: number; status: InvitationStatus | null },
): Promise<Page<Invitation>> {
  const query =
    status === null ? pageQuery(page, pageSize) : `${pageQuery(page, pageSize)}&status=${status}`

  return invitationPageSchema.parse(await apiFetch<unknown>(`${orgPath(orgId)}/convites?${query}`))
}

/** Convida alguém, com o papel já definido (`invitations.write`). 201 com o convite — **sem o
 *  token**, que sai por e-mail pro convidado. */
export async function createInvitation(
  orgId: string,
  input: CreateInvitationInput,
): Promise<Invitation> {
  return invitationSchema.parse(
    await apiFetch<unknown>(`${orgPath(orgId)}/convites`, {
      method: 'POST',
      body: JSON.stringify({ email: input.email, role: input.role }),
    }),
  )
}

/** Revoga um convite (`invitations.write`), **por id e nunca por token**.
 *
 *  É soft e terminal: grava `revoked`, mantém a linha — que é o que faz o aceite recusar com 410
 *  em vez de 404 — e um convite revogado não reativa. 204 no pendente e no já revogado
 *  (idempotente), 409 no já aceito, 404 no de outra organização. */
export async function revokeInvitation(orgId: string, invitationId: string): Promise<void> {
  await apiFetch<void>(`${orgPath(orgId)}/convites/${encodeURIComponent(invitationId)}`, {
    method: 'DELETE',
  })
}

/** Lista convênios. **Não exige capability** — só o vínculo com a organização do path —, e serve
 *  aos dois lados: numa Empresa são os Parceiros dela, num Parceiro são as Empresas que ele
 *  atende. Mesma rota, mesmo dado; só o rótulo sabe de que lado se está. */
export async function listAgreements(
  orgId: string,
  { page, pageSize }: { page: number; pageSize: number },
): Promise<Page<Agreement>> {
  return agreementPageSchema.parse(
    await apiFetch<unknown>(`${orgPath(orgId)}/convenios?${pageQuery(page, pageSize)}`),
  )
}

/** Convenia um Parceiro (`agreements.write`, que só o `company_admin` tem — nem `platform_admin`).
 *
 *  A Empresa não vai no corpo: é a organização do path. 422 se o `partner_id` não for um
 *  Parceiro, 409 se o convênio já existir. */
export async function createAgreement(
  orgId: string,
  input: CreateAgreementInput,
): Promise<Agreement> {
  return agreementSchema.parse(
    await apiFetch<unknown>(`${orgPath(orgId)}/convenios`, {
      method: 'POST',
      body: JSON.stringify({ partner_id: input.partner_id }),
    }),
  )
}

/** Suspende ou reativa um convênio (`agreements.write`). Diferente do convite, aqui `PATCH` é o
 *  certo: suspender **não** é terminal — reativar é o mesmo convênio de volta, não um novo. */
export async function updateAgreementStatus(
  orgId: string,
  agreementId: string,
  status: AgreementStatus,
): Promise<Agreement> {
  return agreementSchema.parse(
    await apiFetch<unknown>(`${orgPath(orgId)}/convenios/${encodeURIComponent(agreementId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
  )
}
