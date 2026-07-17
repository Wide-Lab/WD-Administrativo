import { publicInvitationSchema } from '#/features/onboarding/schema'
import type {
  AcceptInvitationInput,
  PublicInvitation,
  RegisterPartnerInput,
} from '#/features/onboarding/types'
import { apiFetch } from '#/lib/api'

/** As três rotas **públicas** do kernel: são as únicas que respondem sem cookie de sessão, e as
 *  únicas que *emitem* um sem haver login. O que autoriza o aceite é o token do path — ele prova
 *  controle da caixa de e-mail, e é por isso que ele nunca aparece numa listagem (backend 06). */

/** Os dados da tela de aceite. 404 se o token nunca existiu, 410 se existiu e não vale mais. */
export async function getInvitation(token: string): Promise<PublicInvitation> {
  return publicInvitationSchema.parse(
    await apiFetch<unknown>(`/api/convites/${encodeURIComponent(token)}`),
  )
}

/** Aceita e já entra: o backend cria o login se não houver, cria o vínculo e devolve a sessão no
 *  cookie. Responde 200 **sem corpo**, como o login — a identidade vem do `GET /api/me`.
 *
 *  `passwordConfirmation` fica na tela: ela existe pra pegar erro de digitação, e mandá-la ao
 *  servidor pediria que ele confiasse na mesma comparação duas vezes. `name` vazio vira ausente,
 *  não `""` — o campo é opcional no backend, e `""` seria um nome, só que em branco. */
export async function acceptInvitation(token: string, input: AcceptInvitationInput): Promise<void> {
  await apiFetch<void>(`/api/convites/${encodeURIComponent(token)}/aceitar`, {
    method: 'POST',
    body: JSON.stringify({
      password: input.password,
      name: input.name || undefined,
    }),
  })
}

/** Auto-cadastro de Parceiro: organização, primeiro `partner_admin` e vínculo numa transação só,
 *  mais a sessão. E-mail já cadastrado responde 409 — sem organização órfã do outro lado.
 *
 *  É aqui que o formulário plano vira o payload aninhado da spec, e `companyName` vira
 *  `company_name` (ver `schema.ts`). */
export async function registerPartner(input: RegisterPartnerInput): Promise<void> {
  await apiFetch<void>('/api/parceiros/cadastro', {
    method: 'POST',
    body: JSON.stringify({
      company_name: input.companyName,
      document: input.document || undefined,
      admin: {
        name: input.adminName,
        email: input.adminEmail,
        password: input.password,
      },
    }),
  })
}
