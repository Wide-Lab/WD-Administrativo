import { z } from 'zod'

// Validação de formulário. As mensagens são as que o usuário lê — diretas, sem culpar.
export const loginSchema = z.object({
  email: z.string().min(1, 'Informe seu e-mail.').email('Esse e-mail não parece válido.'),
  // **Não** é a `passwordSchema`: aqui a senha é conferida, não definida. Cobrar a política do
  // dia numa senha antiga barraria o login de quem a criou sob outra regra — e o comprimento
  // mínimo, dito na tela de login, é dica de política a quem está só sondando.
  password: z.string().min(1, 'Informe sua senha.'),
})

/** A política de senha, num número só. O backend exige 8 em toda ponta que **define** senha
 *  (`AcceptInvitationRequest`, `RegisterPartnerAdminRequest`, `PUT /api/me/password`) — aqui é
 *  eco dela, não a regra: quem nega é o 422 do servidor. O valor é exportado porque a tela
 *  também o escreve ("Pelo menos 8 caracteres"), e duas cópias divergiriam na primeira mudança. */
export const PASSWORD_MIN_LENGTH = 8

export const passwordSchema = z
  .string()
  .min(PASSWORD_MIN_LENGTH, `Use pelo menos ${PASSWORD_MIN_LENGTH} caracteres.`)

/** Os dois campos de toda tela que **define** uma senha — o aceite de convite, o auto-cadastro
 *  de Parceiro e a troca de senha logada (spec 06, `Reuso`).
 *
 *  É um *shape*, não um schema pronto, porque cada formulário o compõe com os campos que são
 *  seus. A conferência das duas senhas vem separada (`passwordsMatch`) e é aplicada **por
 *  último**, já que `.refine()` devolve um `ZodEffects` — que não dá mais `.extend()`. */
export const passwordFieldsShape = {
  password: passwordSchema,
  passwordConfirmation: z.string().min(1, 'Repita a senha para confirmar.'),
}

export const passwordFieldsSchema = z.object(passwordFieldsShape)

/** A confirmação existe pra pegar o erro de digitação numa senha que ninguém vê enquanto digita
 *  — e um erro desses, no onboarding, tranca a pessoa pra fora da conta que ela acabou de criar. */
export function passwordsMatch(values: {
  password: string
  passwordConfirmation: string
}): boolean {
  return values.password === values.passwordConfirmation
}

/** O veredito cai na confirmação, não na senha: o campo errado é o segundo. */
export const PASSWORDS_MATCH_ERROR = {
  message: 'As senhas não conferem.',
  path: ['passwordConfirmation'],
}

/** Resposta de `GET /api/me` — só identidade. Vínculos, personas e módulos habilitados vêm
 *  de `GET /api/me/contexto` e `GET /api/organizacoes/{orgId}/me` (specs 04/05). */
export const userSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string(),
})
