import { z } from 'zod'

// Os enums do backend (`access/domain/entities.py`). Reescrevê-los aqui é o preço de não ter
// geração de tipos do OpenAPI: um valor novo lá vira erro de parse aqui, alto e cedo, em vez
// de `undefined` silencioso atravessando a casca.

export const organizationTypeSchema = z.enum(['platform', 'company', 'partner'])

export const roleSchema = z.enum([
  'platform_admin',
  'company_admin',
  'hr',
  'finance',
  'manager',
  'collaborator',
  'partner_admin',
  'partner_operator',
])

/** A superfície que o vínculo abre. Derivada no backend de tipo da organização + papel
 *  (`persona_for`) — o frontend recebe pronta e nunca a recalcula: papel→persona é decisão do
 *  `access`, e duplicá-la aqui criaria uma segunda verdade que diverge no primeiro papel novo. */
export const personaSchema = z.enum(['platform', 'company_admin', 'collaborator', 'partner'])

export const contextOrganizationSchema = z.object({
  id: z.string().uuid(),
  type: organizationTypeSchema,
  name: z.string(),
})

export const contextMembershipSchema = z.object({
  organization: contextOrganizationSchema,
  role: roleSchema,
})

/** `GET /api/me/contexto` — global, o bootstrap de roteamento. Lista o que a pessoa **pode
 *  abrir agora**: o backend já omite vínculo ou organização desativados. */
export const myContextSchema = z.object({
  user: z.object({
    id: z.string().uuid(),
    email: z.string().email(),
    name: z.string(),
  }),
  memberships: z.array(contextMembershipSchema),
})

/** `GET /api/organizacoes/{orgId}/me` — eu **nesta** organização. Fonte única de autorização
 *  no cliente: `permissions` libera ações, `modules` monta navegação. */
export const orgContextSchema = z.object({
  role: roleSchema,
  persona: personaSchema,
  permissions: z.array(z.string()),
  /** As chaves dos módulos habilitados **da organização** — não da pessoa. Quem separa duas
   *  pessoas da mesma Empresa é `persona`/`permissions`. */
  modules: z.array(z.string()),
})

/** `GET /api/organizacoes/{orgId}` — só o que a casca pinta. O `/me` não devolve o nome da
 *  organização, e o `/me/contexto` não a lista para um `platform_admin` sem vínculo nela. */
export const organizationSchema = z.object({
  id: z.string().uuid(),
  type: organizationTypeSchema,
  name: z.string(),
  status: z.enum(['active', 'disabled']),
})
