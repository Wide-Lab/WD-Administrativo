import { z } from 'zod'

// Validação de formulário. As mensagens são as que o usuário lê — diretas, sem culpar.
export const loginSchema = z.object({
  email: z.string().min(1, 'Informe seu e-mail.').email('Esse e-mail não parece válido.'),
  password: z.string().min(1, 'Informe sua senha.'),
})

/** Resposta de `GET /api/me` — só identidade. Vínculos, personas e módulos habilitados vêm
 *  de `GET /api/me/contexto` e `GET /api/organizacoes/{orgId}/me` (specs 04/05). */
export const userSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string(),
})
