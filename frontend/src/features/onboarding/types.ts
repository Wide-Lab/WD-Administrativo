import type { z } from 'zod'

import type {
  acceptInvitationSchema,
  publicInvitationSchema,
  registerPartnerSchema,
} from '#/features/onboarding/schema'

// Tipos sempre `z.infer`, nunca escritos à mão.
export type PublicInvitation = z.infer<typeof publicInvitationSchema>
export type AcceptInvitationInput = z.infer<typeof acceptInvitationSchema>
export type RegisterPartnerInput = z.infer<typeof registerPartnerSchema>
