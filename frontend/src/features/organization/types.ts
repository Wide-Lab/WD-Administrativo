import type { z } from 'zod'

import type {
  agreementSchema,
  agreementStatusSchema,
  createAgreementSchema,
  createInvitationSchema,
  invitationSchema,
  invitationStatusSchema,
  memberSchema,
  membershipStatusSchema,
  updateMemberSchema,
} from '#/features/organization/schema'

// Tipos sempre `z.infer`, nunca escritos à mão.
export type MembershipStatus = z.infer<typeof membershipStatusSchema>
export type InvitationStatus = z.infer<typeof invitationStatusSchema>
export type AgreementStatus = z.infer<typeof agreementStatusSchema>

export type Member = z.infer<typeof memberSchema>
export type Invitation = z.infer<typeof invitationSchema>
export type Agreement = z.infer<typeof agreementSchema>

export type CreateInvitationInput = z.infer<typeof createInvitationSchema>
export type UpdateMemberInput = z.infer<typeof updateMemberSchema>
export type CreateAgreementInput = z.infer<typeof createAgreementSchema>

/** Uma página do backend, já tipada pelo item. As três listagens desta feature a devolvem. */
export type Page<ItemT> = {
  items: ItemT[]
  total: number
  page: number
  page_size: number
}
