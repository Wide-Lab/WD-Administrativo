'use client'

import type { ComponentProps } from 'react'

import { ROLE_LABEL } from '#/features/context/lib/labels'
import { rolesFor } from '#/features/context/lib/roles'
import type { OrganizationType, Role } from '#/features/context/types'
import { cn } from '#/lib/utils'

/** O select de papel, estreitado pelo **tipo desta organização**.
 *
 *  Cinco opções numa Empresa, duas num Parceiro (`ROLES_BY_ORGANIZATION_TYPE`). Oferecer um papel
 *  do outro tipo produziria só um 422 — e o `CHECK` do banco o recusaria depois disso —, então o
 *  item não existe em vez de existir pra falhar.
 *
 *  `<select>` nativo e não o `Select` do shadcn: `@radix-ui/react-select` não está instalado, e
 *  um select de 2 a 5 opções não ganha nada com listbox custom — perde teclado e o comportamento
 *  de campo do sistema no mobile. As classes são as do `Input`, pra ele não destoar da linha. */
export function RoleSelect({
  organizationType,
  value,
  onValueChange,
  className,
  ...props
}: Omit<ComponentProps<'select'>, 'value' | 'onChange'> & {
  organizationType: OrganizationType
  value: Role
  onValueChange: (role: Role) => void
}) {
  return (
    <select
      value={value}
      onChange={(event) => onValueChange(event.target.value as Role)}
      className={cn(
        'flex h-10 w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-text',
        'transition-[color,border-color,box-shadow] duration-150',
        'focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'aria-invalid:border-danger aria-invalid:focus-visible:ring-danger/40',
        className,
      )}
      {...props}
    >
      {rolesFor(organizationType).map((role) => (
        <option key={role} value={role}>
          {ROLE_LABEL[role]}
        </option>
      ))}
    </select>
  )
}
