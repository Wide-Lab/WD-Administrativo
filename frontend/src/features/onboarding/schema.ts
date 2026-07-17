import { z } from 'zod'

import { PASSWORDS_MATCH_ERROR, passwordFieldsShape, passwordsMatch } from '#/features/auth/schema'
import { roleSchema } from '#/features/context/schema'

/** `GET /api/convites/{token}` — público, e o backend escolheu cada campo (backend 06): o nome
 *  da organização e o papel explicam à pessoa o que ela está aceitando, e o e-mail deixa a tela
 *  dizer pra quem o convite é sem pedir que ela o digite. Não há id nenhum aqui: quem ainda não
 *  aceitou não é membro de nada. */
export const publicInvitationSchema = z.object({
  organization_name: z.string(),
  email: z.string().email(),
  role: roleSchema,
  /** O backend manda, e a tela **não** pinta: quem diz que o convite venceu é o 410 dele, no
   *  momento do aceite. Uma data na tela seria uma segunda verdade, que envelhece sozinha com a
   *  aba aberta. Fica no schema porque é o contrato, e `z.string()` — não `.datetime()` —
   *  porque o formato exato é escolha do Pydantic: um convite bom não pode falhar o parse por
   *  causa de como o fuso foi escrito. */
  expires_at: z.string(),
})

/** O aceite (`POST /api/convites/{token}/aceitar`).
 *
 *  `name` é opcional porque quem já tem conta já tem nome — e a tela **não sabe** qual é o caso:
 *  o backend responde igual pros dois (backend 06), e é isso que o critério 4 protege. Por isso
 *  ela pergunta sempre, e o backend ignora o que não se aplica. */
export const acceptInvitationSchema = z
  .object({
    name: z.string().trim().max(120, 'Use no máximo 120 caracteres.').optional(),
    ...passwordFieldsShape,
  })
  .refine(passwordsMatch, PASSWORDS_MATCH_ERROR)

/** O auto-cadastro de Parceiro (`POST /api/parceiros/cadastro`).
 *
 *  Os campos são planos e o payload é aninhado (`admin: {...}`) — quem os junta é a `api.ts`. É
 *  também onde `companyName` vira `company_name`: o payload do backend chama o nome do
 *  **Parceiro** de `company_name`, num domínio onde `company` é outro tipo de organização (a
 *  `backend/06` registrou a confusão e apontou pra cá). O nome de lá é contrato e fica; o de cá
 *  é o que a tela e o TypeScript leem, e não precisa herdar o engano. */
export const registerPartnerSchema = z
  .object({
    companyName: z.string().trim().min(1, 'Informe o nome do parceiro.'),
    document: z.string().trim().max(32, 'Use no máximo 32 caracteres.').optional(),
    adminName: z.string().trim().min(1, 'Informe seu nome.'),
    adminEmail: z.string().min(1, 'Informe seu e-mail.').email('Esse e-mail não parece válido.'),
    ...passwordFieldsShape,
  })
  .refine(passwordsMatch, PASSWORDS_MATCH_ERROR)
