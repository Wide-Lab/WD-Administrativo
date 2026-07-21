import { z } from 'zod'

import { roleSchema } from '#/features/context/schema'

/** Os contratos das telas com que uma organização administra a si mesma: membros, convites e
 *  convênios (`frontend/08`). Os enums espelham `access/domain/entities.py` — reescrevê-los é o
 *  preço de não gerar tipos do OpenAPI, e o ganho é um valor novo lá virar erro de parse aqui,
 *  alto e cedo, em vez de `undefined` atravessando a tela. */

export const membershipStatusSchema = z.enum(['active', 'disabled'])
export const invitationStatusSchema = z.enum(['pending', 'accepted', 'revoked', 'expired'])
export const agreementStatusSchema = z.enum(['active', 'suspended'])

/** A `PageResponse[T]` do backend. Genérica porque as três listagens desta tela a devolvem
 *  igual — e porque `total` é o que separa "acabou" de "tem mais página". */
export function pageSchema<ItemT extends z.ZodTypeAny>(item: ItemT) {
  return z.object({
    items: z.array(item),
    total: z.number().int(),
    page: z.number().int(),
    page_size: z.number().int(),
  })
}

/** Um membro, como o `GET .../membros` o devolve.
 *
 *  **Note o que não há aqui: nome e e-mail.** A `MemberResponse` do backend devolve só o
 *  `user_id` — não existe rota que traduza um id de usuário em pessoa (`/api/me` é sobre quem
 *  pergunta, e o `/me/contexto` também). Não é omissão desta tela: é o terceiro achado da spec,
 *  registrado no `Como ficou`. Enquanto a rota não existe, a coluna mostra o id e marca a
 *  própria linha — inventar o nome no cliente seria inventar dado. */
export const memberSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  organization_id: z.string().uuid(),
  role: roleSchema,
  status: membershipStatusSchema,
  created_at: z.string(),
})

/** Um convite, como o `GET .../convites` o devolve.
 *
 *  **Sem `token`, e a ausência é o contrato** (`backend/06`): o token é credencial do convidado,
 *  sai por e-mail pra ele, e devolvê-lo aqui deixaria quem convidou aceitar no lugar da pessoa.
 *  É por isso que não há "copiar link" em tela nenhuma desta spec — não é ergonomia esquecida,
 *  é que a resposta não traz o que o link precisaria. Ver `components/invitations-table.tsx`.
 *
 *  O `status` é o **efetivo**: um convite vencido chega como `expired` mesmo com a coluna em
 *  `pending`. A tela exibe o que recebeu e **não** recalcula vencimento comparando `expires_at`
 *  com o relógio do navegador — seria a terceira escrita de uma regra que já existe duas vezes
 *  no backend, e a única rodando num relógio que o servidor não controla. */
export const invitationSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  organization_id: z.string().uuid(),
  role: roleSchema,
  status: invitationStatusSchema,
  /** `z.string()` e não `.datetime()`, como no onboarding: o formato exato é escolha do
   *  Pydantic, e um convite bom não pode falhar o parse por causa de como o fuso foi escrito. */
  expires_at: z.string(),
  invited_by: z.string().uuid(),
  created_at: z.string(),
})

export const agreementSchema = z.object({
  id: z.string().uuid(),
  company_id: z.string().uuid(),
  partner_id: z.string().uuid(),
  status: agreementStatusSchema,
  created_at: z.string(),
})

export const memberPageSchema = pageSchema(memberSchema)
export const invitationPageSchema = pageSchema(invitationSchema)
export const agreementPageSchema = pageSchema(agreementSchema)

/** O formulário de convite: dois campos, e o papel é escolhido antes de a pessoa existir.
 *
 *  Quais papéis o select oferece **não** é decisão do schema — é `rolesFor(tipo da organização)`
 *  (`features/context/lib/roles.ts`). Aqui o `roleSchema` aceita qualquer papel do enum porque
 *  ele é o espelho do enum; quem estreita pro tipo certo é a tela, e quem **garante** é o
 *  `CHECK` do banco. */
export const createInvitationSchema = z.object({
  email: z
    .string()
    .trim()
    .min(1, 'Informe o e-mail de quem você quer convidar.')
    .email('Esse e-mail não parece válido.'),
  role: roleSchema,
})

/** A edição de um membro. Ao menos um dos dois campos muda — o backend recusa corpo vazio com
 *  422, e a tela não tem por que mandar um. */
export const updateMemberSchema = z.object({
  role: roleSchema,
  status: membershipStatusSchema,
})

/** O convênio novo. O campo é o `partner_id` colado, e isso é um limite reconhecido: **não
 *  existe rota que liste Parceiros disponíveis pra uma Empresa** — `GET /organizacoes` é
 *  `organizations.read`, de `platform_admin`. Buscar Parceiro por nome ou documento é rota nova
 *  de backend, o segundo achado da spec; não é algo que a tela resolva. */
export const createAgreementSchema = z.object({
  partner_id: z
    .string()
    .trim()
    .min(1, 'Informe o identificador do parceiro.')
    .uuid('O identificador do parceiro é um UUID — confira se ele foi copiado inteiro.'),
})
