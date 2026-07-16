import type { z } from 'zod'

import type {
  contextMembershipSchema,
  myContextSchema,
  orgContextSchema,
  organizationSchema,
  organizationTypeSchema,
  personaSchema,
  roleSchema,
} from '#/features/context/schema'

// Tipos sempre `z.infer`, nunca escritos à mão.
export type OrganizationType = z.infer<typeof organizationTypeSchema>
export type Role = z.infer<typeof roleSchema>
export type Persona = z.infer<typeof personaSchema>
export type ContextMembership = z.infer<typeof contextMembershipSchema>
export type MyContext = z.infer<typeof myContextSchema>
export type OrgContext = z.infer<typeof orgContextSchema>
export type Organization = z.infer<typeof organizationSchema>
