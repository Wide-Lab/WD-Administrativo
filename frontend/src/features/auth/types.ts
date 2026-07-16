import type { z } from 'zod'

import type { loginSchema, userSchema } from '#/features/auth/schema'

// Tipos sempre `z.infer`, nunca escritos à mão.
export type LoginInput = z.infer<typeof loginSchema>
export type User = z.infer<typeof userSchema>
