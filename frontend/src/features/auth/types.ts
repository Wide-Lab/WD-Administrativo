import type { z } from 'zod'

import type { loginSchema, passwordFieldsSchema, userSchema } from '#/features/auth/schema'

// Tipos sempre `z.infer`, nunca escritos à mão.
export type LoginInput = z.infer<typeof loginSchema>
export type User = z.infer<typeof userSchema>

/** O par de campos que o `PasswordFields` pinta. Todo formulário que define senha o carrega
 *  dentro do seu (`AcceptInvitationInput`, `RegisterPartnerInput`). */
export type PasswordFieldValues = z.infer<typeof passwordFieldsSchema>
