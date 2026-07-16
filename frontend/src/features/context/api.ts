import {
  myContextSchema,
  orgContextSchema,
  organizationSchema,
} from '#/features/context/schema'
import type { MyContext, OrgContext, Organization } from '#/features/context/types'
import { apiFetch } from '#/lib/api'

/** Meus vínculos — a pergunta que **precede** a escolha do `orgId`. */
export async function getContext(): Promise<MyContext> {
  return myContextSchema.parse(await apiFetch<unknown>('/api/me/contexto'))
}

/** Eu nesta organização: persona, permissões e módulos habilitados dela.
 *
 *  403 aqui é a resposta normal de quem não alcança este tenant — a casca o trata como
 *  "sem vínculo" e redireciona (`org-context-boundary`), não como falha. */
export async function getOrgContext(orgId: string): Promise<OrgContext> {
  return orgContextSchema.parse(
    await apiFetch<unknown>(`/api/organizacoes/${encodeURIComponent(orgId)}/eu`),
  )
}

/** A organização ativa. Existe só pelo nome que o masthead pinta: o `/eu` não o devolve, e o
 *  `/me/contexto` não lista a organização para um `platform_admin` que não tem vínculo nela —
 *  seria a única persona a ver um cabeçalho sem nome. */
export async function getOrganization(orgId: string): Promise<Organization> {
  return organizationSchema.parse(
    await apiFetch<unknown>(`/api/organizacoes/${encodeURIComponent(orgId)}`),
  )
}
