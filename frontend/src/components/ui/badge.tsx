import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps } from 'react'

import { cn } from '#/lib/utils'

// Estados semânticos como fundo tingido + texto na cor do estado. Cores de
// estado (success/warning/danger) passam AA como texto pequeno; a primária usa
// o `primary-fg` clareado, nunca o `primary` de preenchimento.
const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium',
  {
    variants: {
      variant: {
        default: 'border-line bg-surface-2 text-text',
        muted: 'border-line bg-transparent text-muted',
        primary: 'border-transparent bg-primary/15 text-primary-fg',
        success: 'border-transparent bg-success/15 text-success',
        warning: 'border-transparent bg-warning/15 text-warning',
        danger: 'border-transparent bg-danger/15 text-danger',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

export type BadgeProps = ComponentProps<'span'> & VariantProps<typeof badgeVariants>

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { badgeVariants }
